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
from datetime import datetime, time, timezone, timedelta
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
        #ActivityType.Cycling: "Ride",
        #ActivityType.MountainBiking: "Ride",
        ActivityType.Hiking: 90012,
        ActivityType.Running: 8,
        ActivityType.Walking: 27,
        #ActivityType.Snowboarding: "Snowboard",
        ActivityType.Skating: 15580,
        #ActivityType.CrossCountrySkiing: "NordicSki",
        #ActivityType.DownhillSkiing: "AlpineSki",
        #ActivityType.Swimming: "Swim",
        ActivityType.Gym: 3015,
        #ActivityType.Rowing: "Rowing",
        #ActivityType.Elliptical: "Elliptical",
        #ActivityType.RollerSkiing: "RollerSki",
        #ActivityType.StrengthTraining: "WeightTraining",
        ActivityType.Climbing: 15535,
        ActivityType.Other: 20,
        ActivityType.Swimming: 90024,
        ActivityType.Cycling: 90001,
        #ActivityType.StandUpPaddling: "StandUpPaddling",
    }

    _reverseActivityTypeMappings = {

        17165: ActivityType.Walking, #	90013	27	Walking the dog	Walk	Walking
    }

    SupportedActivities = list(_activityTypeMappings.keys())

    def _randomString(self, stringLength=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

    def _generateOauthHeader(self):

        ts = calendar.timegm(time.gmtime())
        header_string ='oauth_consumer_key="' + GARMIN_KEY + '"&oauth_nonce="' + self._randomString(16) \
               + '"&oauth_signature_method="HMACSHA1"&oauth_timestamp="' + ts + '"&oauth_version="1.0"'
        return header_string
        #header_byte = header_string.encode("utf-8")
        #header_encode = base64.b64encode(header_byte)
        #header = header_encode.decode("utf-8")
        #return header

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

        print(headers)
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

        db.test.update_one(
            {'_id': 'garmin_tokens'},
            {"$set": {'_id': 'garmin_tokens', 'token': self.token, 'secret': self.token_secret}},
            upsert=True
        )

        return resp

    def UserUploadedActivityURL(self, uploadId):
        return "https://www.fitbit.com/activities"

    # Use this function to get Autorization URL
    def WebInit(self):
        current_conn = db.test.find_one({'_id': 'garmin_tokens'})

        if current_conn:
            self.token = current_conn['token']
            self.token_secret = current_conn['secret']

        # If there is no current token for garmin health (for all user), get it and set it into mongo
        if not self.token or self.token is None or not self.token_secret or self.token_secret is None:
            response = self._unauthorized_request()

        print(self.token)
        print(self.token_secret)

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

    def _request_signin(self, http_method, path, user_tokens):

        request_info = {
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
                           + "&oauth_token=" + oauth_token \
                           + "&oauth_version=" + version
        parameter_string_encoded = urllib.parse.quote(parameter_string, safe="%")
        # 4) Signature string
        signature_string = http_method_encoded + "&" + path_encoded + "&" + parameter_string_encoded
        # 5) Base string encode
        base_string = signature_string.encode()
        # 6) Key encode
        # TODO : Pour generer la secret, j'ai besoin de consumer secret (local settings) et du request token secret (etape 1)
        key = GARMIN_SECRET + "&"
        key = key.encode()
        # 7) hashed
        hashed = hmac.new(key, base_string, sha1)
        hashed_encode = base64.b64encode(hashed.digest())
        # 8) generate Signature
        signature = urllib.parse.quote(hashed_encode, safe="%")

        # Building header
        # 1) generate Header string
        header_oauth_string = 'oauth_consumer_key="' + garmin_key_encoded \
                              + '",oauth_nonce="' + oauth_nonce_encoded \
                              + '",oauth_signature="' + signature \
                              + '",oauth_signature_method="' + method_encoded \
                              + '",oauth_timestamp="' + timestamp_now_encoded \
                              + '",oauth_token="' + oauth_token_encoded \
                              + '",oauth_version="' + version_encoded + '"'

        headers = {
            'Authorization': 'OAuth ' + header_oauth_string
        }

        request_info['headers'] = headers

        return request_info


    # This function is used to set token info for a user, get expiration date, refresh and access token
    def RetrieveAuthorizationToken(self, req, level):

        oauth_token = self.token#req.GET.get("oauth_token")#
        #oauth_token = "0d5885b5-3fbf-4b25-aed8-845ab7d30409"
        oauth_token_encoded = urllib.parse.quote_plus(oauth_token, safe='%')

        oauth_token_secret = self.token_secret
        #oauth_token_secret = "tnW46HVTp3s9N8CNWppFVEZIB6JdcZ06l8n"
        oauth_token_secret_encoded = urllib.parse.quote_plus(oauth_token_secret, safe='%')
        oauth_verifier = req.GET.get("oauth_verifier")
        #oauth_verifier = "7RbOgYBBZS"
        oauth_verifier_encoded = urllib.parse.quote_plus(oauth_verifier, safe='%')

        print(' Token --------')
        print(oauth_token)
        print(' Token Verifier --------')
        print(oauth_verifier)
        print(' Token secret self --------')
        print(oauth_token_secret)
        print('----------')

        # Common parameters
        date_now = datetime.now()
        timestamp_now = str(int(date_now.timestamp()))
        #timestamp_now = "1558353617"
        timestamp_now_encoded = urllib.parse.quote_plus(timestamp_now, safe='%')

        oauth_nonce = self._randomString(16)#"2950197265"
        oauth_nonce = str("%10d" % randint(0,9999999999))
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
        path = self.ACCESS_TOKEN  # "https://connectapi.garmin.com/oauth-service/oauth/access_token"
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

        print(' Verifier ----------')
        print(oauth_verifier)
        print(oauth_verifier_encoded)
        print('----------')

        #'OAuth oauth_nonce="2950197265", oauth_signature="FennN8y52JIRNFrfKdcbISkMs9w%3D", oauth_consumer_key="899561ca-4602-4ef7-936b-2ea447a10efe", oauth_token="0d5885b5-3fbf-4b25-aed8-845ab7d30409", oauth_timestamp="1558353617", oauth_verifier="7RbOgYBBZS", oauth_signature_method="HMAC-SHA1", oauth_version="1.0"'
        #'OAuth oauth_nonce="2950197265",oauth_signature="FennN8y52JIRNFrfKdcbISkMs9w%3D", oauth_consumer_key="899561ca-4602-4ef7-936b-2ea447a10efe", oauth_signature_method="HMAC-SHA1",oauth_timestamp="1558353617",oauth_token="0d5885b5-3fbf-4b25-aed8-845ab7d30409",oauth_verifier="7RbOgYBBZS",oauth_version="1.0"'
        # 4) Signature string
        signature_string = http_method_encoded + "&" + path_encoded + "&" + parameter_string_encoded

        # 5) Base string encode
        base_string = signature_string.encode()
        print(' Base string ----------')
        print(base_string)
        print('----------')

        # 6) Key encode (garmin secret & verifier)
        key = GARMIN_SECRET + "&" + oauth_token_secret #+ "&"
        #key = GARMIN_SECRET + "&" + oauth_verifier #+ "&"

        # 7) hashed
        print(' Key ----------')
        print(key)
        print('----------')

        key = key.encode()
        print(' Key encoded ----------')
        print(key)
        print('----------')


        # 7) hashed
        hashed = hmac.new(key, base_string, sha1)
        hashed_encode = base64.b64encode(hashed.digest())
        # 8) generate Signature
        signature = urllib.parse.quote(hashed_encode, safe="%")
        # 9) generate Header string
        print(' OAuth nonce & timestamp ----------')
        print(oauth_nonce_encoded)
        print(timestamp_now_encoded)
        print('----------')
        
        header_oauth_string = 'oauth_nonce="' + oauth_nonce_encoded \
                              + '", oauth_signature="' + signature \
                              + '", oauth_consumer_key="' + garmin_key_encoded \
                              + '", oauth_token="' + oauth_token_encoded \
                              + '", oauth_timestamp="' + timestamp_now_encoded \
                              + '", oauth_verifier="' + oauth_verifier_encoded \
                              + '", oauth_signature_method="' + method_encoded \
                              + '", oauth_version="' + version_encoded + '"'

        payload = ""
        from_garmin = 'nonce="6407187735", oauth_signature="rFMgPFElM1PaP59us3%2FIXRkUhzE%3D", oauth_consumer_key="899561ca-4602-4ef7-936b-2ea447a10efe", oauth_token="d33825ca-3e25-418e-ac58-bddc191c0110", oauth_timestamp="1558450463", oauth_verifier="YbnikzbvKF", oauth_signature_method="HMAC-SHA1", oauth_version="1.0"'
        headers = {
            'Authorization': 'OAuth ' + from_garmin #+ header_oauth_string
        }

        print(' Headers ----------')
        print(header_oauth_string)
        
        print(headers)
        print('----------')

        # Call request_token
        resp = requests.request("POST", self.REQUEST_TOKEN, data=payload, headers=headers)
        #resp = None
        # FROM WEB TOOL GARMIN ( WORKING)
        #OAuth oauth_nonce="4821830223",
        # oauth_signature="TzOm%2BXYO2nj9CC0ArmqOt9Y60aM%3D",
        # oauth_consumer_key="899561ca-4602-4ef7-936b-2ea447a10efe",
        # oauth_token="87c7986c-90aa-41d7-8e0f-be5b5b9ded0f",
        # oauth_timestamp="1558449344",
        # oauth_verifier="KlaAgw7RYK",
        # oauth_signature_method="HMAC-SHA1",
        # oauth_version="1.0"

        # FROM DEV ( NOT WORKING)
        #OAuth oauth_nonce="7588745923",
        # oauth_signature="l8EJ%2BR%2FsgUgejfOIhs8O%2BvUgbl4%3D",
        # oauth_consumer_key="899561ca-4602-4ef7-936b-2ea447a10efe",
        # oauth_token="3dddeaa3-ffd8-44ba-95a9-4da53169b381",
        # oauth_timestamp="1558449097",
        # oauth_verifier="c7MgS8MJXX",
        # oauth_signature_method="HMAC-SHA1",
        # oauth_version="1.0"

        print(resp)
        print('----------')

        if resp.status_code != 200:
            data = resp.text
            print(data)
            print('----------')

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
        print(credentials)
        print('----------')
        access_token = credentials.get(b'oauth_token')[0]
        access_token_secret = credentials.get(b'oauth_token_secret')[0]

        # Get user ID
        now = datetime.now(timezone.utc)

        # Build signin header
        user_tokens = {
            'access_token': access_token,
            'access_token_secret': access_token_secret,
            'oauth_token': oauth_token
        }
        signin_info = self._request_signin('GET', self.URI_USER_ID, user_tokens)

        print(signin_info)

        # Request garmin api to get user id
        resp = requests.request("GET", self.URI_USER_ID, data=payload, headers=headers)
        print(resp)
        data = resp.json
        user_id = data['userId']
        print(data)

        authorizationData = {
            "OAuthToken": oauth_token,
            "AccessToken": access_token,
            "AccessTokenSecret": access_token_secret,
            "AccessTokenRequestedAt": now,
        }

        return (user_id, authorizationData)

    # This function is used to revoke access token
    def RevokeAuthorization(self, serviceRecord):

        resp = self._requestWithAuth(lambda session: session.post(self.FITBIT_REVOKE_URI,
                                                                  data={
                                                                      "token": serviceRecord.Authorization.get('AccessToken')
                                                                  },
                                                                  headers={
                                                                      'Authorization': 'Basic '+ self.header_encode,
                                                                      'Content-Type': 'application/x-www-form-urlencoded'
                                                                  }), serviceRecord)

        if resp.status_code != 204 and resp.status_code != 200:
            raise APIException("Unable to deauthorize Fitbit auth token, status " + str(resp.status_code) + " resp " + resp.text)

        logging.info("Revoke Fitbit Authorization")

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []
        before = earliestDate = None

        # define low parameter
        limit = 20
        offset = 0
        sort = "desc"
        # get user Fitbit ID
        userID = svcRecord.ExternalID
        # get service Tapiriik ID
        service_id = svcRecord._id
        # get user "start sync from date" info
        # then prepare afterDate var (this var determine the date since we download activities)
        user = db.users.find_one({'ConnectedServices': {'$elemMatch': {'ID': service_id, 'Service': 'fitbit'}}})
        afterDateObj = datetime.now() - timedelta(days=1)

        if user['Config']['sync_skip_before'] is not None:
            afterDateObj = user['Config']['sync_skip_before']
        else:
            if exhaustive:
                afterDateObj = datetime.now() - timedelta(days=3650) # throw back to 10 years

        afterDate = afterDateObj.strftime("%Y-%m-%d")
        logging.info("\t Download Fitbit activities since : " + afterDate)

        # prepare parameters to set in fitbit request uri
        uri_parameters = {
            'limit': limit,
            'offset': offset,
            'sort': sort,
            'afterDate': afterDate,
            'token': svcRecord.Authorization.get('AccessToken')
        }
        # set base fitbit request uri
        activities_uri_origin = 'https://api.fitbit.com/1/user/' + userID + '/activities/list.json'

        # first execute offset = 0,
        # offset will be set to -1 if fitbit response don't give next pagination info
        # offset will be incremented by 1 if fitbit response give next pagination info
        index_total = 0
        while offset > -1:

            # prepare uri parameters
            uri_parameters['offset'] = offset
            # build fitbit uri with new parameters
            activities_uri = activities_uri_origin + "?" + urlencode(uri_parameters)
            # execute fitbit request using "request with auth" function (it refreshes token if needed)
            logging.info("\t\t downloading offset : " + str(offset))
            resp = self._requestWithAuth(lambda session: session.get(
                activities_uri,
                headers={
                    'Authorization': 'Bearer ' + svcRecord.Authorization.get('AccessToken')
                }), svcRecord)

            # check if request has error
            if resp.status_code != 204 and resp.status_code != 200:
                raise APIException("Unable to find Fitbit activities")

            # get request data
            data = {}
            try:
                data = resp.json()
            except ValueError:
                raise APIException("Failed parsing fitbit list response %s - %s" % (resp.status_code, resp.text))

            # if request return activities infos
            if data['activities']:
                ftbt_activities = data['activities']
                logging.info("\t\t nb activity : " + str(len(ftbt_activities)))

                # for every activities in this request pagination
                # (Fitbit give 20 activities MAXIMUM, use limit parameter)
                for ftbt_activity in ftbt_activities:
                    index_total = index_total +1
                    activity = UploadedActivity()

                    #parse date start to get timezone and date
                    parsedDate = ftbt_activity["startTime"][0:19] + ftbt_activity["startTime"][23:]
                    activity.StartTime = datetime.strptime(parsedDate, "%Y-%m-%dT%H:%M:%S%z")
                    activity.TZ = pytz.utc

                    logger.debug("\tActivity s/t %s: %s" % (activity.StartTime, ftbt_activity["activityName"]))

                    activity.EndTime = activity.StartTime + timedelta(0, (ftbt_activity["duration"]/1000))
                    activity.ServiceData = {"ActivityID": ftbt_activity["logId"], "Manual": ftbt_activity["logType"]}

                    # check if activity type ID exists
                    if ftbt_activity["activityTypeId"] not in self._reverseActivityTypeMappings:
                        exclusions.append(APIExcludeActivity("Unsupported activity type %s" % ftbt_activity["activityTypeId"],
                                                             activity_id=ftbt_activity["logId"],
                                                             user_exception=UserException(UserExceptionType.Other)))
                        logger.info("\t\tUnknown activity")
                        continue

                    activity.Type = self._reverseActivityTypeMappings[ftbt_activity["activityTypeId"]]

                    activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Kilometers,
                                                                value=ftbt_activity["distance"])

                    if "speed" in ftbt_activity:
                        activity.Stats.Speed = ActivityStatistic(
                            ActivityStatisticUnit.KilometersPerHour,
                            avg=ftbt_activity["speed"],
                            max=ftbt_activity["speed"]
                        )
                    activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=ftbt_activity["calories"])
                    # Todo: find fitbit data name
                    #activity.Stats.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=ride[
                    #    "moving_time"] if "moving_time" in ride and ride[
                    #    "moving_time"] > 0 else None)  # They don't let you manually enter this, and I think it returns 0 for those activities.
                    # Todo: find fitbit data name
                    #if "average_watts" in ride:
                    #    activity.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts,
                    #                                             avg=ride["average_watts"])

                    if "averageHeartRate" in ftbt_activity:
                        activity.Stats.HR.update(
                            ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=ftbt_activity["averageHeartRate"]))
                    # Todo: find fitbit data name
                    #if "max_heartrate" in ride:
                    #    activity.Stats.HR.update(
                    #        ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, max=ride["max_heartrate"]))
                    # Todo: find fitbit data name
                    #if "average_cadence" in ride:
                    #    activity.Stats.Cadence.update(ActivityStatistic(ActivityStatisticUnit.RevolutionsPerMinute,
                    #                                                    avg=ride["average_cadence"]))
                    # Todo: find fitbit data name
                    #if "average_temp" in ride:
                    #    activity.Stats.Temperature.update(
                    #        ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, avg=ride["average_temp"]))

                    if "calories" in ftbt_activity:
                        activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories,
                                                                  value=ftbt_activity["calories"])
                    activity.Name = ftbt_activity["activityName"]


                    activity.Private = False
                    if ftbt_activity['logType'] is 'manual':
                        activity.Stationary = True
                    else:
                        activity.Stationary = False


                    # Todo: find fitbit data
                    #activity.GPS = ("start_latlng" in ride) and (ride["start_latlng"] is not None)
                    activity.AdjustTZ()
                    activity.CalculateUID()
                    activities.append(activity)
                    logging.info("\t\t Fitbit Activity ID : " + str(ftbt_activity["logId"]))

                if not exhaustive:
                    break
            # get next info for while condition and prepare offset for next request
            if 'next' not in data['pagination'] or not data['pagination']['next']:
                next = None
                offset = -1
            else:
                next = data['pagination']['next']
                offset = offset + 1

        logging.info("\t\t total Fitbit activities downloaded : " + str(index_total))
        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):

        userID = svcRecord.ExternalID
        activity_id = activity.ServiceData["ActivityID"]

        logging.info("\t\t FITBIT LOADING  : " + str(activity_id))
        activity_tcx_uri = 'https://api.fitbit.com/1/user/' + userID + '/activities/' + str(activity_id) + '.tcx'
        resp = self._requestWithAuth(lambda session: session.get(
            activity_tcx_uri,
            headers={
                'Authorization': 'Bearer ' + svcRecord.Authorization.get('AccessToken')
            }), svcRecord)
        # check if request has error
        if resp.status_code != 204 and resp.status_code != 200:
            raise APIException("Unable to find Fitbit TCX activity")

        # Prepare tcxio params
        ns = copy.deepcopy(TCXIO.Namespaces)
        ns["tcx"] = ns[None]
        del ns[None]

        # Read tcx to know if this is a stationary activity or not
        try:
            root = etree.XML(resp.text.encode('utf-8'))
        except:
            root = etree.fromstring(resp.text.encode('utf-8'))

        xacts = root.find("tcx:Activities", namespaces=ns)
        if xacts is None:
            raise ValueError("No activities element in TCX")

        xact = xacts.find("tcx:Activity", namespaces=ns)
        if xact is None:
            raise ValueError("No activity element in TCX")

        # Define activity type from tcx
        if not activity.Type or activity.Type == ActivityType.Other:
            if xact.attrib["Sport"] == "Biking":
                activity.Type = ActivityType.Cycling
            elif xact.attrib["Sport"] == "Running":
                activity.Type = ActivityType.Running

        # Find all lap in tcx
        xlaps = xact.findall("tcx:Lap", namespaces=ns)
        if len(xlaps) > 0:
            activity = TCXIO.Parse(resp.text.encode('utf-8'), activity)
        else:
            # Define lap for activity
            lap = Lap(stats=activity.Stats, startTime=activity.StartTime, endTime=activity.EndTime)
            activity.Laps = [lap]
            lap.Waypoints = []
            activity.GPS = False
            activity.Stationary = len(lap.Waypoints) == 0

        return activity

    # Garmin Health is on read only access, we can't upload activities
    def UploadActivity(self, svcRecord, activity):
        logging.info("UPLOAD To Fitbit Activity tz " + str(activity.TZ) + " dt tz " + str(
            activity.StartTime.tzinfo) + " starttime " + str(activity.StartTime))

        logger.info("Activity tz " + str(activity.TZ) + " dt tz " + str(activity.StartTime.tzinfo) + " starttime " + str(activity.StartTime))

        # Check if we're currently uploading item
        if self.LastUpload is not None:
            while (datetime.now() - self.LastUpload).total_seconds() < 5:
                time.sleep(1)
                logger.debug("Inter-upload cooldown")

        # Get activity source
        source_svc = None
        if hasattr(activity, "ServiceDataCollection"):
            source_svc = str(list(activity.ServiceDataCollection.keys())[0])

        upload_id = None

        userID = svcRecord.ExternalID
        activity_id = activity.ServiceData["ActivityID"]

        activity_date = activity.StartTime.strftime("%Y-%m-%d")
        activity_time = activity.StartTime.strftime("%H:%M:%S")

        durationDelta = activity.EndTime - activity.StartTime
        duration = durationDelta.total_seconds() * 1000

        distance = 0
        if activity.Stats.Distance:
            distance = activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value

        calories = 0
        if activity.Stats.Energy:
            calories = activity.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value

        parameters = {
            'manualCalories': int(calories),
            'startTime': activity_time,
            'date': activity_date,
            'durationMillis': int(duration),
            'distance': distance,
            'distanceUnit': 'Meter',

        }

        # If activity type is "other" set name into parameters, else set activity type
        # uri parameters doesn't accept both on same post
        if activity.Type != 20:
            activity_name = activity.StartTime.strftime("%d/%m/%Y")
            if activity.Name:
                activity_name = activity.Name
            parameters['activityName'] = activity_name
        else:
            parameters['activityId'] = self._activityTypeMappings[activity.Type]


        activity_upload_uri = 'https://api.fitbit.com/1/user/' + userID + '/activities.json'
        resp = self._requestWithAuth(lambda session: session.post(
            activity_upload_uri,
            data=parameters,
            headers={
                'Authorization': 'Bearer ' + svcRecord.Authorization.get('AccessToken')
            }), svcRecord)

        self.LastUpload = datetime.now()

        if resp.status_code != 201 and resp.status_code != 200:
            if resp.status_code == 401:
                raise APIException(
                    "No authorization to upload activity " + activity.UID + " response " + resp.text + " status " + str(
                        resp.status_code), block=True,
                    user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))

            raise APIException(
                "Unable to upload activity " + activity.UID + " response " + resp.text + " status " + str(
                    resp.status_code))

        resp_json = resp.json()
        upload_id = resp_json['activityLog']['activityId']

        return upload_id

    def DeleteCachedData(self, serviceRecord):
        cachedb.fitbit_cache.remove({"Owner": serviceRecord.ExternalID})
        cachedb.fitbit_activity_cache.remove({"Owner": serviceRecord.ExternalID})

