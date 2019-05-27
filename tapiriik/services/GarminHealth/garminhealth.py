from tapiriik.settings import WEB_ROOT, GARMIN_KEY, GARMIN_SECRET
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.database import cachedb, db
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatistics, ActivityStatisticUnit, Waypoint, WaypointType, Location, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity, ServiceException
from tapiriik.services.tcx import TCXIO
from tapiriik.services.ratelimiting import RateLimit, RateLimitExceededException
from requests_oauthlib import OAuth1Session
from requests.exceptions import ReadTimeout, RequestException
from lxml import etree
import copy
from django.core.urlresolvers import reverse
from datetime import date, datetime, time, timezone, timedelta
from urllib.parse import urlencode
import calendar
import requests
import os
import logging
import pytz
import re
import time
import json
import pprint
from hashlib import sha1
import hmac
import base64
import string
import urllib.parse
from six.moves.urllib.parse import parse_qs
import random
from random import randint

logger = logging.getLogger(__name__)

class GarminHealthService(ServiceBase):

    API_URL = "https://healthapi.garmin.com/wellness-api/rest"
    # POST # URI to get a request token
    REQUEST_TOKEN = "https://connectapi.garmin.com/oauth-service/oauth/request_token"
    # POST # URI to get user token/token_secret
    ACCESS_TOKEN = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
    # GET # URI to get user auth and verifier token
    OAUTH_TOKEN ="http://connect.garmin.com/oauthConfirm"
    # GET # URI to get user ID
    URI_USER_ID = "https://healthapi.garmin.com/wellness-api/rest/user/id"
    # GET # URI to get user activities summary
    URI_ACTIVITIES_SUMMARY = "https://healthapi.garmin.com/wellness-api/rest/activities"
    URI_ACTIVITIES_DETAIL = "https://healthapi.garmin.com/wellness-api/rest/activityDetails"

    token = None
    token_secret = None

    FITBIT_AUTH_URI = "https://www.fitbit.com/oauth2/authorize"
    FITBIT_REFRESH_URI = "https://api.fitbit.com/oauth2/token"
    FITBIT_REVOKE_URI = "https://api.fitbit.com/oauth2/revoke"


    header_line = GARMIN_KEY + ":" + GARMIN_SECRET
    header_byte = header_line.encode("utf-8")
    header_encode = base64.b64encode(header_byte)
    header_encode = header_encode.decode("utf-8")


    ID = "garminhealth"
    DisplayName = "Garmin Health"
    DisplayAbbreviation = "GRHL"

    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True  # They don't prevent the iframe, it just looks really ugly.
    PartialSyncRequiresTrigger = False
    LastUpload = None

    SupportsHR = SupportsCadence = SupportsTemp = SupportsPower = False

    SupportsActivityDeletion = False

    GlobalRateLimits = None


    _activityTypeMappings = {
        ActivityType.Running: "RUNNING",
        ActivityType.Cycling: "CYCLING",
        ActivityType.MountainBiking: "MOUNTAIN_BIKING",
        ActivityType.Walking: "WALKING",
        ActivityType.Hiking: "HIKING",
        ActivityType.DownhillSkiing: "DownhillSkiing",#######
        ActivityType.CrossCountrySkiing: "CROSS_COUNTRY_SKIING",
        ActivityType.Snowboarding: "RESORT_SKIING_SNOWBOARDING",
        ActivityType.Skating: "SKATE_SKIING",
        ActivityType.Swimming: "SWIMMING",
        #ActivityType.Wheelchair: "Wheelchair",
        ActivityType.Rowing: "ROWING",
        ActivityType.Elliptical: "ELLIPTICAL",
        ActivityType.Gym: "FITNESS_EQUIPMENT",
        ActivityType.Climbing: "MOUNTAINEERING",
        #ActivityType.RollerSkiing: "RollerSkiing",
        ActivityType.StrengthTraining: "STRENGTH_TRAINING",
        ActivityType.StandUpPaddling: "STAND_UP_PADDLEBOARDING",
        ActivityType.Other: "UNCATEGORIZED"
    }

    _reverseActivityTypeMappings = {  # Removes ambiguities when mapping back to their activity types
        "ALL": ActivityType.Other,
        "UNCATEGORIZED": ActivityType.Other,
        #"SEDENTARY"
        "RUNNING": ActivityType.Running,
        "STREET_RUNNING": ActivityType.Running,
        "TRACK_RUNNING": ActivityType.Running,
        "TRAIL_RUNNING": ActivityType.Running,
        "TREADMILL_RUNNING": ActivityType.Running,
        "CYCLING": ActivityType.Cycling,
        "CYCLOCROSS": ActivityType.Cycling,
        "DOWNHILL_BIKING": ActivityType.MountainBiking,
        "INDOOR_CYCLING": ActivityType.Cycling,
        "MOUNTAIN_BIKING": ActivityType.MountainBiking,
        "RECUMBENT_CYCLING": ActivityType.Cycling,
        "ROAD_BIKING": ActivityType.Cycling,
        "TRACK_CYCLING": ActivityType.Cycling,
        "FITNESS_EQUIPMENT": ActivityType.Gym,
        "ELLIPTICAL": ActivityType.Elliptical,
        #"INDOOR_CARDIO"
        #"INDOOR_ROWING"
        "STAIR_CLIMBING": ActivityType.Climbing,
        "STRENGTH_TRAINING": ActivityType.StrengthTraining,
        "HIKING": ActivityType.Hiking,
        "SWIMMING": ActivityType.Swimming,
        "LAP_SWIMMING": ActivityType.Swimming,
        "OPEN_WATER_SWIMMING": ActivityType.Swimming,
        "WALKING": ActivityType.Walking,
        "CASUAL_WALKING": ActivityType.Walking,
        "SPEED_WALKING": ActivityType.Walking,
        "TRANSITION": ActivityType.Other,
        "SWIMTOBIKETRANSITION": ActivityType.Other,
        "BIKETORUNTRANSITION": ActivityType.Other,
        "RUNTOBIKETRANSITION": ActivityType.Other,
        "OTHER": ActivityType.Other,
        #"BACKCOUNTRY_SKIING_SNOWBOARDING"
        "CROSS_COUNTRY_SKIING": ActivityType.CrossCountrySkiing,
        #"FLYING"
        #"GOLF"
        #"HORSEBACK_RIDING"
        #"INLINE_SKATING"
        "MOUNTAINEERING": ActivityType.Climbing,
        "PADDLING": ActivityType.StandUpPaddling,
        "RESORT_SKIING_SNOWBOARDING": ActivityType.Snowboarding,
        "ROWING": ActivityType.Rowing,
        #"SAILING"
        "SKATE_SKIING": ActivityType.Skating,
        "SKATING": ActivityType.Skating,
        "SNOW_SHOE": ActivityType.Walking,
        "STAND_UP_PADDLEBOARDING": ActivityType.StandUpPaddling,
        #"WHITEWATER_RAFTING_KAYAKING"
        #"WIND_KITE_SURFING"
    }

    SupportedActivities = list(_activityTypeMappings.keys())

    def _randomString(self, stringLength=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

    def _unauthorized_request(self):

        # Prepare some parameters (timestamp, strings, nonce)
        date_now = datetime.now()
        timestamp_now = str(int(date_now.timestamp()))
        timestamp_now_encoded = urllib.parse.quote_plus(timestamp_now, safe='%')
        oauth_nonce = self._randomString(32) #+ timestamp_now
        oauth_nonce_encoded = urllib.parse.quote_plus(oauth_nonce, safe='%')
        garmin_key_encoded = urllib.parse.quote_plus(GARMIN_KEY, safe='%')
        method = "HMAC-SHA1"
        method_encoded = urllib.parse.quote_plus("HMAC-SHA1", safe='%')
        version = "1.0"
        version_encoded = urllib.parse.quote_plus("1.0", safe='%')

        # Build signature
        # 1) HTTP METHOD
        http_method = "POST"
        http_method_encoded = urllib.parse.quote(http_method, safe="%")
        # 2) Path
        path = self.REQUEST_TOKEN#"https://connectapi.garmin.com/oauthservice/oauth/request_token"
        path_encoded = urllib.parse.quote(path, safe="%")
        # 3) Parameter string
        parameter_string = "oauth_consumer_key=" + GARMIN_KEY \
                           + "&oauth_nonce=" + oauth_nonce \
                           + "&oauth_signature_method=" + method\
                           + "&oauth_timestamp=" + timestamp_now \
                           + "&oauth_version=" + version
        parameter_string_encoded = urllib.parse.quote(parameter_string, safe="%")
        # 4) Signature string
        signature_string = http_method_encoded + "&" + path_encoded + "&" + parameter_string_encoded
        # 5) Base string encode
        base_string = signature_string.encode()
        # 6) Key encode
        key = GARMIN_SECRET + "&"
        key = key.encode()
        # 7) hashed
        hashed = hmac.new(key, base_string, sha1)
        hashed_encode = base64.b64encode(hashed.digest())
        # 8) generate Signature
        signature = urllib.parse.quote(hashed_encode, safe="%")

        # Build header line
        # 1) generate Header string
        header_oauth_string = 'oauth_consumer_key="' + garmin_key_encoded \
                              + '",oauth_nonce="' + oauth_nonce_encoded \
                              + '",oauth_signature="' + signature \
                              + '",oauth_signature_method="' + method_encoded \
                              + '",oauth_timestamp="' + timestamp_now_encoded \
                              + '",oauth_version="' + version_encoded + '"'
        payload = ""
        headers = {
            'Authorization': 'OAuth ' + header_oauth_string
        }

        # Call request_token
        resp = requests.request("POST", self.REQUEST_TOKEN, data=payload, headers=headers)

        if resp.status_code != 200:
            data = resp.text
            raise APIException("No authorization", block=True,
                               user_exception=UserException(UserExceptionType.Authorization,
                                                            intervention_required=True))

        content = resp.content
        credentials = parse_qs(content)

        self.token = credentials.get(b'oauth_token')[0].decode()

        self.token_secret = credentials.get(b'oauth_token_secret')[0].decode()

        db.garmin_health.update_one(
            {'_id': self.token},
            {"$set": {'_id': self.token, 'token': self.token, 'secret': self.token_secret, 'used': False, 'date': datetime.now()}},
            upsert=True
        )

        return credentials

    def UserUploadedActivityURL(self, uploadId):
        return "https://www.fitbit.com/activities"

    # Use this function to get Autorization URL
    def WebInit(self):
        # il faut recuperer le dernier token généré
        date_now = datetime.now()
        token_ttl = date_now - timedelta(hours=1)
        #deletedToken = db.garmin_health.delete_many({"date": {'$lt': token_ttl}, 'used': False})
        last_connection = db.garmin_health.find_one({}, sort=[("date", -1)])

        if last_connection:
            if last_connection['used'] is True:
                # Get new oauth token
                response = self._unauthorized_request()
                self.token = response.get(b'oauth_token')[0].decode()
                self.token_secret = response.get(b'oauth_token_secret')[0].decode()
            else:
                self.token = last_connection['token']
                self.token_secret = last_connection['token']
        else:
            # first generation or TTL is done
            response = self._unauthorized_request()
            self.token = response.get(b'oauth_token')[0].decode()
            self.token_secret = response.get(b'oauth_token_secret')[0].decode()

        uri_parameters = {
            'oauth_token': self.token, #credentials.get(b'oauth_token')[0],
            'oauth_callback': WEB_ROOT + reverse("oauth_return", kwargs={"service": "garminhealth"}),
        }

        self.UserAuthorizationURL = self.OAUTH_TOKEN + "?" + urlencode(uri_parameters)

    # This function refresh access token if current is expire
    def _requestWithAuth(self, reqLambda, serviceRecord):
        session = requests.Session()

        now = datetime.utcnow()

        if now > serviceRecord.Authorization.get("AccessTokenExpiresAt", 0):
            logging.info("Refresh Fitbit Authorization Token")

            # Expired access token, or still running (now-deprecated) indefinite access token.
            refreshToken = serviceRecord.Authorization.get("RefreshToken",
                                                           serviceRecord.Authorization.get("OAuthToken"))
            params = {
                "grant_type": "refresh_token",
                "refresh_token": refreshToken,
                #"expires_in": FITBIT_DURATION
            }

            response = requests.post(self.FITBIT_REFRESH_URI,
                                     data=params,
                                     headers={
                                         'Authorization': 'Basic '+ self.header_encode,
                                         'Content-Type': 'application/x-www-form-urlencoded'
                                     })

            if response.status_code != 200:
                raise APIException("No authorization to refresh token", block=True,
                                   user_exception=UserException(UserExceptionType.Authorization,
                                                                intervention_required=True))

            data = response.json()

            now = datetime.now(timezone.utc)
            endDate = now + timedelta(seconds=data['expires_in'])

            authorizationData = {
                "AccessToken": data["access_token"],
                "AccessTokenRequestedAt": now,
                "AccessTokenExpiresAt": endDate,
                "RefreshToken": data["refresh_token"],
                'TokenType': data['token_type']
            }

            serviceRecord.Authorization.update(authorizationData)
            db.connections.update({"_id": serviceRecord._id}, {"$set": {"Authorization": authorizationData}})

        #session.headers.update({"Authorization": "access_token %s" % serviceRecord.Authorization["AccessToken"]})
        return reqLambda(session)

    def _request_signin(self, http_method, path, user_tokens, parameters=None):

        request_info = {
            'path': path,
            'header': None,
            'signature': None
        }
        # Token parameters ----------
        # OAuth token
        oauth_token = user_tokens['oauth_token']
        oauth_token_encoded = urllib.parse.quote_plus(oauth_token, safe='%')
        # User access token
        access_token = user_tokens['access_token']
        access_token_encoded = urllib.parse.quote_plus(access_token, safe='%')
        # User access token secret
        access_token_secret = user_tokens['access_token_secret']
        access_token_secret_encoded = urllib.parse.quote_plus(access_token_secret, safe='%')

        # General parameters ------------
        # Garmin key
        garmin_key_encoded = urllib.parse.quote_plus(GARMIN_KEY, safe='%')
        # Timestamp
        date_now = datetime.now()
        timestamp_now = str(int(date_now.timestamp()))
        timestamp_now_encoded = urllib.parse.quote_plus(timestamp_now, safe='%')
        # UploadEndTime & UploadStartTime
        start_date = datetime.combine(date.today(), datetime.min.time())
        end_date = datetime.combine(date.today(), datetime.max.time())

        upload_end_time = str(int(start_date.timestamp()))
        upload_start_time = str(int(end_date.timestamp()))
        if parameters:
            if parameters['upload_end_time']:
                upload_end_time = parameters['upload_end_time']
            if parameters['upload_start_time']:
                upload_start_time = parameters['upload_start_time']

        #upload_end_time="1558344993"
        #upload_start_time="1558344993"
        upload_end_time_encoded = urllib.parse.quote_plus(upload_end_time, safe='%')
        upload_start_time_encoded = urllib.parse.quote_plus(upload_start_time, safe='%')

        # Nonce
        oauth_nonce = self._randomString(16)
        oauth_nonce_encoded = urllib.parse.quote_plus(oauth_nonce, safe='%')
        # Method
        method = "HMAC-SHA1"
        method_encoded = urllib.parse.quote_plus("HMAC-SHA1", safe='%')
        # Version
        version = "1.0"
        version_encoded = urllib.parse.quote_plus("1.0", safe='%')

        # Building header signature
        # 1) HTTP METHOD
        http_method_encoded = urllib.parse.quote(http_method, safe="%")

        # 2) Path
        path_encoded = urllib.parse.quote(path, safe="%")

        # 3) Parameter string
        parameter_string = "oauth_consumer_key=" + GARMIN_KEY \
                           + "&oauth_nonce=" + oauth_nonce \
                           + "&oauth_signature_method=" + method \
                           + "&oauth_timestamp=" + timestamp_now \
                           + "&oauth_token=" + access_token \
                           + "&oauth_version=" + version \
                           + "&uploadEndTimeInSeconds=" + upload_end_time \
                           + "&uploadStartTimeInSeconds=" + upload_start_time
        parameter_string_encoded = urllib.parse.quote(parameter_string, safe="%")

        # 4) Signature string
        signature_string = http_method_encoded + "&" + path_encoded + "&" + parameter_string_encoded

        # 5) Base string encode
        base_string = signature_string.encode()

        # 6) Key encode
        key = GARMIN_SECRET + "&" + access_token_secret
        key = key.encode()

        # 7) hashed
        hashed = hmac.new(key, base_string, sha1)
        hashed_encode = base64.b64encode(hashed.digest())

        # 8) generate Signature
        signature = urllib.parse.quote(hashed_encode, safe="%")
        request_info['signature'] = signature

        # Building header
        # 1) generate Header string
        header_oauth_string = 'oauth_consumer_key="' + garmin_key_encoded \
                              + '",oauth_nonce="' + oauth_nonce_encoded \
                              + '",oauth_signature="' + signature \
                              + '",oauth_signature_method="' + method_encoded \
                              + '",oauth_timestamp="' + timestamp_now_encoded \
                              + '",oauth_token="' + access_token_encoded \
                              + '",oauth_version="' + version_encoded + '"'

        headers = {
            'Authorization': 'OAuth ' + header_oauth_string
        }

        request_info['header'] = headers
        # TODO : this path construction could be change later
        request_info['path'] = path + "?uploadStartTimeInSeconds=" + upload_start_time\
                               + "&uploadEndTimeInSeconds=" + upload_end_time

        return request_info

    # This function is used to set token info for a user, get expiration date, refresh and access token
    def RetrieveAuthorizationToken(self, req, level):

        oauth_token = req.GET.get("oauth_token")
        oauth_token_encoded = urllib.parse.quote_plus(oauth_token, safe='%')

        # find secret of this token
        current_conn = db.garmin_health.find_one({'_id': self.token})

        oauth_token_secret = current_conn['secret']
        oauth_token_secret_encoded = urllib.parse.quote_plus(oauth_token_secret, safe='%')

        oauth_verifier = req.GET.get("oauth_verifier")
        oauth_verifier_encoded = urllib.parse.quote_plus(oauth_verifier, safe='%')

        # Common parameters
        date_now = datetime.now()
        timestamp_now = str(int(date_now.timestamp()))
        timestamp_now_encoded = urllib.parse.quote_plus(timestamp_now, safe='%')

        oauth_nonce = self._randomString(16)
        oauth_nonce_encoded = urllib.parse.quote_plus(oauth_nonce, safe='%')

        garmin_key_encoded = urllib.parse.quote_plus(GARMIN_KEY, safe='%')

        method = "HMAC-SHA1"
        method_encoded = urllib.parse.quote_plus("HMAC-SHA1", safe='%')

        version = "1.0"
        version_encoded = urllib.parse.quote_plus("1.0", safe='%')

        # 1) HTTP METHOD
        http_method = "POST"
        http_method_encoded = urllib.parse.quote(http_method, safe="%")

        # 2) Path
        path = self.ACCESS_TOKEN # "https://connectapi.garmin.com/oauth-service/oauth/access_token"
        path_encoded = urllib.parse.quote(path, safe="%")

        # 3) Parameter string
        parameter_string = "oauth_consumer_key=" + GARMIN_KEY \
                           + "&oauth_nonce=" + oauth_nonce \
                           + "&oauth_signature_method=" + method \
                           + "&oauth_timestamp=" + timestamp_now \
                           + "&oauth_token=" + oauth_token \
                           + "&oauth_verifier=" + oauth_verifier \
                           + "&oauth_version=" + version
        parameter_string_encoded = urllib.parse.quote(parameter_string, safe="%")

        # 4) Signature string
        signature_string = http_method_encoded + "&" + path_encoded + "&" + parameter_string_encoded

        # 5) Base string encode
        base_string = signature_string.encode()

        # 6) Key encode (garmin secret & verifier)
        key = GARMIN_SECRET + "&" + oauth_token_secret

        # 7) hashed
        key = key.encode()

        # 7) hashed
        hashed = hmac.new(key, base_string, sha1)
        hashed_encode = base64.b64encode(hashed.digest())

        # 8) generate Signature
        signature = urllib.parse.quote(hashed_encode, safe="%")

        # 9) generate Header string
        header_oauth_string = 'oauth_nonce="' + oauth_nonce_encoded \
                              + '", oauth_signature="' + signature \
                              + '", oauth_consumer_key="' + garmin_key_encoded \
                              + '", oauth_token="' + oauth_token_encoded \
                              + '", oauth_timestamp="' + timestamp_now_encoded \
                              + '", oauth_verifier="' + oauth_verifier_encoded \
                              + '", oauth_signature_method="' + method_encoded \
                              + '", oauth_version="' + version_encoded + '"'

        payload = ""
        headers = {
            'Authorization': 'OAuth ' + header_oauth_string
        }

        db.garmin_health.update_one(
            {'_id': self.token},
            {"$set": {'used': True}},
            upsert=True
        )

        # Call access_token
        resp = requests.request("POST", self.ACCESS_TOKEN, data=payload, headers=headers)

        if resp.status_code != 200:
            data = resp.text
            raise APIException(
                "No authorization",
                block=True,
                user_exception=UserException(
                    UserExceptionType.Authorization,
                    intervention_required=True
                 )
            )

        logging.info("Retrieve Garmin Health Authorization Token")

        # Retrieve user access token
        content = resp.content
        credentials = parse_qs(content)

        access_token = credentials.get(b'oauth_token')[0].decode()
        access_token_secret = credentials.get(b'oauth_token_secret')[0].decode()

        # Get user ID
        now = datetime.now(timezone.utc)

        # Build signin header
        user_tokens = {
            'access_token': access_token,
            'access_token_secret': access_token_secret,
            'oauth_token': oauth_token
        }
        signin_info = self._request_signin('GET', self.URI_USER_ID, user_tokens)

        # Request garmin api to get user id
        payload = ""
        resp = requests.request("GET", signin_info['path'], data=payload, headers=signin_info['header'])
        if resp.status_code != 200:
            raise APIException(
                "User not found",
                block=True,
                user_exception=UserException(
                    UserExceptionType.Authorization,
                    intervention_required=True
                 )
            )

        # We get user access, we can now remove token from db
        db.garmin_health.delete_one({'_id': self.token})

        json_data = json.loads(resp.text)
        user_id = json_data['userId']

        authorizationData = {
            "OAuthToken": oauth_token,
            "AccessToken": access_token,
            "AccessTokenSecret": access_token_secret,
            "AccessTokenRequestedAt": now,
        }

        return (user_id, authorizationData)

    # This function is used to revoke access token
    def RevokeAuthorization(self, serviceRecord):

        date_now = datetime.now()
        now_tstmp = str(int(date_now.timestamp()))

        signin_info = self._request_signin(
            'GET',
            self.URI_ACTIVITIES_SUMMARY,
            {
                'access_token': serviceRecord.Authorization.get('AccessToken'),
                'access_token_secret': serviceRecord.Authorization.get('AccessTokenSecret'),
                'oauth_token': serviceRecord.Authorization.get('OAuthToken')
            },
            parameters={
                'upload_start_time': now_tstmp,
                'upload_end_time': now_tstmp,
            }
        )

        resp = requests.request("GET", signin_info['path'], headers=signin_info['header'])

        if resp.status_code != 204 and resp.status_code != 200:
            raise APIException("Unable to deauthorize Fitbit auth token, status " + str(resp.status_code) + " resp " + resp.text)

        logging.info("Revoke Garmin Authorization")

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []
        before = earliestDate = None

        # define low parameter
        # get Garmin info

        # WARNING : BE CAREFULL ABOUT DATE FILTER
        # date filter of this request will follow this process :
        # - fetching activity with uploaded date between  upload_start_time & upload_end_time
        # - return matched activities
        # For example :
        # if you upload at 20-05-2019 an activity into Garmin with start date 01-01-2019
        # and you use upload_start_time=20-05-2019 & upload_end_time=21-05-2019
        # the 01-01-2019 will be return
        # So we've to check if the "startTimeInSeconds" of returned items is > sync_skip_before

        service_id = svcRecord._id
        user = db.users.find_one({'ConnectedServices': {'$elemMatch': {'ID': service_id, 'Service': 'garminhealth'}}})

        afterDateObj = datetime.now() - timedelta(days=1)
        # If we want an exhaustive list
        """
        if user['Config']['sync_skip_before'] is not None and exhaustive:
            afterDateObj = user['Config']['sync_skip_before']
        else:
            if exhaustive:
                afterDateObj = datetime.now() - timedelta(days=30)# throw back to 10 years
        # TODO : TMP VAR FOR TEST
        afterDateObj = datetime.now() - timedelta(days=30)
        """
        afterDate = afterDateObj.strftime("%Y-%m-%d")
        afterDate_tstmp = str(int(afterDateObj.timestamp()))
        date_now = datetime.now()
        now_tstmp = str(int(date_now.timestamp()))

        userID = svcRecord.ExternalID
        oauth_token = svcRecord.Authorization.get('OAuthToken')
        user_access_token = svcRecord.Authorization.get('AccessToken')
        user_access_token_secret = svcRecord.Authorization.get('AccessTokenSecret')

        logging.info("\t Download Garmin Health activities since : " + afterDate)
        logging.info("\t Building signin for activities summary")

        user_tokens = {
            'access_token': user_access_token,
            'access_token_secret': user_access_token_secret,
            'oauth_token': oauth_token
        }
        payload = ""
        start_date = afterDateObj
        index_total = 0
        while start_date < date_now:
            end_date = start_date + timedelta(seconds=86400)
            if end_date > date_now:
                end_date = date_now

            start_date_tmstmp = str(int(start_date.timestamp()))
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_tmstmp = str(int(end_date.timestamp()))
            end_date_str = end_date.strftime("%Y-%m-%d")

            logging.info("\t Download Garmin Health activities from %s to %s " % (start_date_str, end_date_str))

            signin_parameters = {
                'upload_start_time': start_date_tmstmp,
                'upload_end_time': end_date_tmstmp,
            }
            signin_info = self._request_signin('GET', self.URI_ACTIVITIES_SUMMARY, user_tokens, parameters=signin_parameters)

            resp = requests.request("GET", signin_info['path'], data=payload, headers=signin_info['header'])

            if resp.status_code != 204 and resp.status_code != 200:
                logging.info("\t An error occured while downloading Garmin Health activities from %s to %s " % (start_date_str, end_date_str))

            json_data = resp.json()

            if json_data:
                for item in json_data:
                    index_total = index_total + 1
                    activity = UploadedActivity()

                    activity_name = item['activityType']
                    if item['deviceName'] is not 'unknown':
                        activity_name = activity_name + " - " +  item['deviceName']

                    # parse date start to get timezone and date
                    activity.StartTime = datetime.fromtimestamp(item['startTimeInSeconds'])
                    activity.TZ = pytz.utc

                    logger.debug("\tActivity s/t %s: %s" % (activity.StartTime, activity_name))

                    activity.EndTime = activity.StartTime + timedelta(0, (item["durationInSeconds"]))
                    activity.ServiceData = {"ActivityID": item["summaryId"]}
                    if "manual" in item:
                        activity.ServiceData['Manual'] = item["manual"]
                    else:
                        activity.ServiceData['Manual'] = False
                    # check if activity type ID exists
                    if item["activityType"] not in self._reverseActivityTypeMappings:
                        # TODO : Uncomment it when test are done
                        #exclusions.append(
                        #    APIExcludeActivity("Unsupported activity type %s" % item["activityType"],
                        #                       activity_id=item["summaryId"],
                        #                       user_exception=UserException(UserExceptionType.Other)))
                        logger.info("\t\tUnknown activity")
                        continue

                    activity.Type = self._reverseActivityTypeMappings[item["activityType"]]

                    activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters,
                                                                value=item["distanceInMeters"])

                    if "avgSpeedInMetersPerSecond" in item and "maxSpeedInMetersPerSecond" in item:
                        activity.Stats.Speed = ActivityStatistic(
                            ActivityStatisticUnit.MetersPerSecond,
                            avg=item["avgSpeedInMetersPerSecond"],
                            max=item["maxSpeedInMetersPerSecond"]
                        )
                    else:
                        if "avgSpeedInMetersPerSecond" in item:
                            activity.Stats.Speed = ActivityStatistic(
                                ActivityStatisticUnit.MetersPerSecond,
                                avg=item["avgSpeedInMetersPerSecond"]
                            )
                        if "maxSpeedInMetersPerSecond" in item:
                            activity.Stats.Speed = ActivityStatistic(
                                ActivityStatisticUnit.MetersPerSecond,
                                max=item["maxSpeedInMetersPerSecond"]
                            )

                    # Todo: find Garmin data name
                    # activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories,
                    #                                          value=ftbt_activity["calories"])
                    # Todo: find fitbit data name
                    # activity.Stats.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=ride[
                    #    "moving_time"] if "moving_time" in ride and ride[
                    #    "moving_time"] > 0 else None)  # They don't let you manually enter this, and I think it returns 0 for those activities.
                    # Todo: find fitbit data name
                    # if "average_watts" in ride:
                    #    activity.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts,
                    #                                             avg=ride["average_watts"])

                    # Todo: find fitbit data
                    # activity.GPS = ("start_latlng" in ride) and (ride["start_latlng"] is not None)

                    if "averageHeartRateInBeatsPerMinute" in item and "maxHeartRateInBeatsPerMinute" in item:
                        activity.Stats.HR.update(
                            ActivityStatistic(
                                ActivityStatisticUnit.BeatsPerMinute,
                                avg=item["averageHeartRateInBeatsPerMinute"],
                                max=item["maxHeartRateInBeatsPerMinute"]
                            )
                        )
                    else:
                        if "averageHeartRateInBeatsPerMinute" in item:
                            activity.Stats.HR.update(
                                ActivityStatistic(
                                    ActivityStatisticUnit.BeatsPerMinute,
                                    avg=item["averageHeartRateInBeatsPerMinute"]
                                )
                            )
                        if "maxHeartRateInBeatsPerMinute" in item:
                            activity.Stats.HR.update(
                                ActivityStatistic(
                                    ActivityStatisticUnit.BeatsPerMinute,
                                    max=item["maxHeartRateInBeatsPerMinute"]
                                )
                            )

                    # Todo: find Garmin data name
                    # if "average_cadence" in ride:
                    #    activity.Stats.Cadence.update(ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute,
                    #                                                    avg=ride["average_cadence"]))
                    # Todo: find Garmin data name
                    # if "average_temp" in ride:
                    #    activity.Stats.Temperature.update(
                    #        ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, avg=ride["average_temp"]))

                    # Todo: find Garmin data name
                    if "calories" in item:
                        activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories,
                                                                  value=item["calories"])
                    activity.Name = activity_name

                    activity.Private = False
                    activity.Stationary = False

                    activity.AdjustTZ()
                    activity.CalculateUID()
                    activities.append(activity)
                    logging.info("\t\t Garmin Activity ID : " + str(item["summaryId"]))

            start_date = end_date

        logging.info("\t\t total Fitbit activities downloaded : " + str(index_total))
        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):

        service_id = svcRecord._id
        user = db.users.find_one({'ConnectedServices': {'$elemMatch': {'ID': service_id, 'Service': 'garminhealth'}}})

        userID = svcRecord.ExternalID
        oauth_token = svcRecord.Authorization.get('OAuthToken')
        user_access_token = svcRecord.Authorization.get('AccessToken')
        user_access_token_secret = svcRecord.Authorization.get('AccessTokenSecret')

        logging.info("\t Building signin for activity detail")

        user_tokens = {
            'access_token': user_access_token,
            'access_token_secret': user_access_token_secret,
            'oauth_token': oauth_token
        }
        payload = ""

        start_date = datetime.now() - timedelta(days=1)
        end_date = start_date + timedelta(seconds=86400)
        start_date_tmstmp = str(int(start_date.timestamp()))
        end_date_tmstmp = str(int(end_date.timestamp()))
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        signin_parameters = {
            'upload_start_time': start_date_tmstmp,
            'upload_end_time': end_date_tmstmp,
        }
        signin_info = self._request_signin('GET', self.URI_ACTIVITIES_DETAIL, user_tokens,
                                           parameters=signin_parameters)

        print('signin parameter ------------')
        print(signin_parameters)
        print('------------')

        print(' signin info ------------')
        print(signin_info)
        print('------------')
        resp = requests.request("GET", signin_info['path'], data=payload, headers=signin_info['header'])

        if resp.status_code != 204 and resp.status_code != 200:
            logging.info("\t An error occured while downloading Garmin Health activities from %s to %s " % (
            start_date_str, end_date_str))

        json_data = resp.json()
        activity_id = activity.ServiceData["ActivityID"]
        activity_detail_id = activity_id + '-detail'
        if json_data:
            for item in json_data:
                if activity_detail_id == item['summaryId']:
                    lapsdata = []

                    if "laps" in item:
                        for lap in item['laps']:
                            lapsdata.append(lap['startTimeInSeconds'])

                    ridedata = {}
                    lapWaypoints = []
                    startTimeLap = activity.StartTime

                    if "samples" in item:
                        formatedDate = startTimeLap
                        activity.GPS = True
                        activity.Stationary = False
                        for pt in item['samples']:
                            wp = Waypoint()

                            delta = int(pt.get('startTimeInSeconds'))
                            formatedDate = startTimeLap + timedelta(seconds=delta)
                            wp.Timestamp = formatedDate

                            wp.Location = Location()
                            if "latitudeInDegree" in pt:
                                wp.Location.Latitude = float(pt.get('latitudeInDegree'))
                            if "longitudeInDegree" in pt:
                                wp.Location.Longitude = float(pt.get('longitudeInDegree'))
                            if "elevationInMeters" in pt:
                                wp.Location.Altitude = int(pt.get('elevationInMeters'))

                            if "totalDistanceInMeters" in pt:
                                wp.Distance = int(pt.get('totalDistanceInMeters'))

                            #if "elevationInMeters" in pt:
                            #    ridedata[delta]['LAP'] = int(pt.get('elevationInMeters'))

                            if "speedMetersPerSecond" in pt:
                                wp.Speed = int(pt.get('speedMetersPerSecond'))

                            if "heartRate" in pt:
                                print(pt.get('heartRate'))
                                wp.HR = int(pt.get('heartRate'))

                            # current sample is = to lap occur , sobuild a new lap
                            if delta in lapsdata:
                                lap = Lap(stats=activity.Stats, startTime=startTimeLap, endTime=formatedDate)
                                lap.Waypoints = lapWaypoints
                                activity.Laps.append(lap)
                                # re init a new lap
                                startTimeLap = formatedDate
                                lapWaypoints = []
                            # add occur
                            lapWaypoints.append(wp)

                        # build last lap
                        if len(lapWaypoints) > 0:
                            lap = Lap(stats=activity.Stats, startTime=startTimeLap, endTime=formatedDate)
                            lap.Waypoints = lapWaypoints
                            activity.Laps.append(lap)
                    else:
                        activity.Laps = [Lap(startTime=activity.StartTime, endTime=activity.EndTime, stats=activity.Stats)]

                    break
                else:
                    print('C est pas la bonne')

        return activity

    # Garmin Health is on read only access, we can't upload activities
    def UploadActivity(self, svcRecord, activity):
        logging.info("UPLOAD To Garming Health is not possible")

        return None

    def DeleteCachedData(self, serviceRecord):
        cachedb.fitbit_cache.remove({"Owner": serviceRecord.ExternalID})
        cachedb.fitbit_activity_cache.remove({"Owner": serviceRecord.ExternalID})

