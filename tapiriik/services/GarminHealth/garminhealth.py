from tapiriik.settings import WEB_ROOT, GARMINHEALTH_KEY, GARMINHEALTH_SECRET
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.database import cachedb, db
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatistics, ActivityStatisticUnit, Waypoint, WaypointType, Location, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType
from django.core.urlresolvers import reverse
from datetime import date, datetime, timezone, timedelta
from urllib.parse import urlencode
from tapiriik.database import redis
import requests
import logging
import pytz
import json
from hashlib import sha1
import hmac
import base64
import string
import urllib.parse
from six.moves.urllib.parse import parse_qs
import random

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

    header_line = GARMINHEALTH_KEY + ":" + GARMINHEALTH_SECRET
    header_byte = header_line.encode("utf-8")
    header_encode = base64.b64encode(header_byte)
    header_encode = header_encode.decode("utf-8")


    ID = "garminhealth"
    DisplayName = "Garmin Health"
    DisplayAbbreviation = "GH"

    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True  # They don't prevent the iframe, it just looks really ugly.
    PartialSyncRequiresTrigger = False
    LastUpload = None

    SupportsHR = SupportsCadence = SupportsTemp = SupportsPower = False

    SupportsActivityDeletion = False

    ReceivesActivities = False

    _activityTypeMappings = {
        ActivityType.Running: "RUNNING",
        ActivityType.Cycling: "CYCLING",
        ActivityType.MountainBiking: "MOUNTAIN_BIKING",
        ActivityType.Walking: "WALKING",
        ActivityType.Hiking: "HIKING",
        ActivityType.DownhillSkiing: "DownhillSkiing",
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
        oauth_nonce = self._randomString(32)
        oauth_nonce_encoded = urllib.parse.quote_plus(oauth_nonce, safe='%')
        garmin_key_encoded = urllib.parse.quote_plus(GARMINHEALTH_KEY, safe='%')
        method = "HMAC-SHA1"
        method_encoded = urllib.parse.quote_plus(method, safe='%')
        version = "1.0"
        version_encoded = urllib.parse.quote_plus(version, safe='%')

        # Build signature
        # 1) HTTP METHOD
        http_method = "POST"
        http_method_encoded = urllib.parse.quote(http_method, safe="%")
        # 2) Path
        path = self.REQUEST_TOKEN
        path_encoded = urllib.parse.quote(path, safe="%")
        # 3) Parameter string
        parameter_string = "oauth_consumer_key=" + GARMINHEALTH_KEY \
                           + "&oauth_nonce=" + oauth_nonce \
                           + "&oauth_signature_method=" + method \
                           + "&oauth_timestamp=" + timestamp_now \
                           + "&oauth_version=" + version
        parameter_string_encoded = urllib.parse.quote(parameter_string, safe="%")
        # 4) Signature string
        signature_string = http_method_encoded + "&" + path_encoded + "&" + parameter_string_encoded
        # 5) Base string encode
        base_string = signature_string.encode()
        # 6) Key encode
        key = GARMINHEALTH_SECRET + "&"
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
            raise APIException("No authorization", block=True,
                               user_exception=UserException(UserExceptionType.Authorization,
                                                            intervention_required=True))

        content = resp.content
        credentials = parse_qs(content)

        self.token = credentials.get(b'oauth_token')[0].decode()

        self.token_secret = credentials.get(b'oauth_token_secret')[0].decode()

        redis_token_key = 'garminhealth:oauth:%s' % self.token
        redis.setex(redis_token_key, self.token_secret, timedelta(hours=1))

        return credentials

    def UserUploadedActivityURL(self, uploadId):
        return "https://connect.garmin.com/modern/activity/" + str(uploadId)

    # Use this function to get Autorization URL
    def WebInit(self):
        self.UserAuthorizationURL = reverse("oauth_redirect", kwargs={"service": "garminhealth"})

    def GenerateUserAuthorizationURL(self, session, level=None):
        # Get last used token
        date_now = datetime.now()
        token_ttl = date_now - timedelta(hours=1)
        
        # first generation or TTL is done
        response = self._unauthorized_request()
        self.token = response.get(b'oauth_token')[0].decode()
        self.token_secret = response.get(b'oauth_token_secret')[0].decode()

        uri_parameters = {
            'oauth_token': self.token, #credentials.get(b'oauth_token')[0],
            'oauth_callback': WEB_ROOT + reverse("oauth_return", kwargs={"service": self.ID}),
        }

        url = self.OAUTH_TOKEN + "?" + urlencode(uri_parameters)
        return url

    # This function generate a new signature for api request
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
        garmin_key_encoded = urllib.parse.quote_plus(GARMINHEALTH_KEY, safe='%')
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

        upload_end_time_encoded = urllib.parse.quote_plus(upload_end_time, safe='%')
        upload_start_time_encoded = urllib.parse.quote_plus(upload_start_time, safe='%')

        # Nonce
        oauth_nonce = self._randomString(16)
        oauth_nonce_encoded = urllib.parse.quote_plus(oauth_nonce, safe='%')
        # Method
        method = "HMAC-SHA1"
        method_encoded = urllib.parse.quote_plus(method, safe='%')
        # Version
        version = "1.0"
        version_encoded = urllib.parse.quote_plus(version, safe='%')

        # Building header signature
        # 1) HTTP METHOD
        http_method_encoded = urllib.parse.quote(http_method, safe="%")

        # 2) Path
        path_encoded = urllib.parse.quote(path, safe="%")

        # 3) Parameter string
        parameter_string = "oauth_consumer_key=" + GARMINHEALTH_KEY \
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
        key = GARMINHEALTH_SECRET + "&" + access_token_secret
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
        # Build path construction with two required parameters
        request_info['path'] = path + "?uploadStartTimeInSeconds=" + upload_start_time\
                               + "&uploadEndTimeInSeconds=" + upload_end_time

        return request_info

    # This function is used to set token info for a user, get expiration date, refresh and access token
    def RetrieveAuthorizationToken(self, req, level):

        oauth_token = req.GET.get("oauth_token")
        oauth_token_encoded = urllib.parse.quote_plus(oauth_token, safe='%')
        
        # find secret of this token
        redis_token_key = "garminhealth:oauth:%s" % self.token
        secret = redis.get(redis_token_key)
        redis.delete(redis_token_key)

        oauth_token_secret = secret.decode("utf-8") 
        oauth_token_secret_encoded = urllib.parse.quote_plus(oauth_token_secret, safe='%')
        
        oauth_verifier = req.GET.get("oauth_verifier")
        oauth_verifier_encoded = urllib.parse.quote_plus(oauth_verifier, safe='%')

        # Common parameters
        date_now = datetime.now()
        timestamp_now = str(int(date_now.timestamp()))
        timestamp_now_encoded = urllib.parse.quote_plus(timestamp_now, safe='%')

        oauth_nonce = self._randomString(16)
        oauth_nonce_encoded = urllib.parse.quote_plus(oauth_nonce, safe='%')

        garmin_key_encoded = urllib.parse.quote_plus(GARMINHEALTH_KEY, safe='%')

        method = "HMAC-SHA1"
        method_encoded = urllib.parse.quote_plus(method, safe='%')

        version = "1.0"
        version_encoded = urllib.parse.quote_plus(version, safe='%')

        # 1) HTTP METHOD
        http_method = "POST"
        http_method_encoded = urllib.parse.quote(http_method, safe="%")

        # 2) Path
        path = self.ACCESS_TOKEN # "https://connectapi.garmin.com/oauth-service/oauth/access_token"
        path_encoded = urllib.parse.quote(path, safe="%")

        # 3) Parameter string
        parameter_string = "oauth_consumer_key=" + GARMINHEALTH_KEY \
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
        key = GARMINHEALTH_SECRET + "&" + oauth_token_secret

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


        json_data = json.loads(resp.text)
        user_id = json_data['userId']

        authorizationData = {
            "OAuthToken": oauth_token,
            "AccessToken": access_token,
            "AccessTokenSecret": access_token_secret,
            "AccessTokenRequestedAt": now,
        }
        response = self._unauthorized_request()
        self.WebInit()


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

        # if resp.status_code != 204 and resp.status_code != 200:
        #    raise APIException("Unable to deauthorize Garmin Health auth token, status " + str(resp.status_code) + " resp " + resp.text)

        self.WebInit()
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
        # So we download activities from upload date

        redis_token_key = 'garminhealth:activities:%s' % svcRecord.ExternalID
        thereIsActivities = redis.get(redis_token_key)

        logging.info("\t\t Garmin thereIsActivities : " + str(thereIsActivities))


        if thereIsActivities == b"1":

            logging.info("\t\t Garmin thereIsActivities : PLOPLOP ")

            redis.delete(redis_token_key)
            afterDateObj = datetime.now() - timedelta(days=1)

            afterDate = afterDateObj.strftime("%Y-%m-%d")
            afterDate_tstmp = str(int(afterDateObj.timestamp()))
            date_now = datetime.now()
            now_tstmp = str(int(date_now.timestamp()))

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
                            activity_name = activity_name + " - " + item['deviceName']

                        # parse date start to get timezone and date
                        activity.StartTime = datetime.utcfromtimestamp(item['startTimeInSeconds'])
                        activity.TZ = pytz.utc

                        logging.debug("\tActivity start s/t %s: %s" % (activity.StartTime, activity_name))

                        activity.EndTime = activity.StartTime + timedelta(seconds=item["durationInSeconds"])

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

                        if "distanceInMeters" in item :
                            activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=item["distanceInMeters"])

                        if "averageSpeedInMetersPerSecond" in item and "maxSpeedInMetersPerSecond" in item:
                            activity.Stats.Speed = ActivityStatistic(
                                ActivityStatisticUnit.MetersPerSecond,
                                avg=item["averageSpeedInMetersPerSecond"],
                                max=item["maxSpeedInMetersPerSecond"]
                            )
                        else:
                            if "averageSpeedInMetersPerSecond" in item:
                                activity.Stats.Speed = ActivityStatistic(
                                    ActivityStatisticUnit.MetersPerSecond,
                                    avg=item["averageSpeedInMetersPerSecond"]
                                )
                            if "maxSpeedInMetersPerSecond" in item:
                                activity.Stats.Speed = ActivityStatistic(
                                    ActivityStatisticUnit.MetersPerSecond,
                                    max=item["maxSpeedInMetersPerSecond"]
                                )

                        # Todo: find Garmin data name
                        # activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories,
                        #                                          value=ftbt_activity["calories"])
                        # Todo: find Garmin data name
                        # activity.Stats.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=ride[
                        #    "moving_time"] if "moving_time" in ride and ride[
                        #    "moving_time"] > 0 else None)  # They don't let you manually enter this, and I think it returns 0 for those activities.
                        # Todo: find Garmin data name
                        # if "average_watts" in ride:
                        #    activity.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts,
                        #                                             avg=ride["average_watts"])

                        # Todo: find Garmin data
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
                        elif "activeKilocalories" in item :
                            activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories,
                                                                    value=item["activeKilocalories"])
                        activity.Name = activity_name

                        activity.Private = False

                        activity.Stationary = True
                        activity.GPS = False
                        if "startingLatitudeInDegree" in item :
                            activity.Stationary = False
                            activity.GPS = True

                        activity.AdjustTZ()
                        activity.CalculateUID()
                        activities.append(activity)
                        logging.info("\t\t Garmin Activity ID : " + str(item["summaryId"]))

                start_date = end_date

            logging.info("\t\t total Garmin activities downloaded : " + str(index_total))
        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):
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
                    endTimeLap = activity.EndTime

                    if "samples" in item:
                        activity.GPS = True
                        activity.Stationary = False
                        for pt in item['samples']:
                            wp = Waypoint()

                            delta = int(pt.get('clockDurationInSeconds'))
                            dateStartPoint = int(pt.get('startTimeInSeconds'))
                            dateStartPointDt = datetime.utcfromtimestamp(dateStartPoint)

                            wp.Timestamp = dateStartPointDt

                            wp.Location = Location()
                            if "latitudeInDegree" in pt:
                                wp.Location.Latitude = float(pt.get('latitudeInDegree'))
                            if "longitudeInDegree" in pt:
                                wp.Location.Longitude = float(pt.get('longitudeInDegree'))
                            if "elevationInMeters" in pt:
                                wp.Location.Altitude = int(pt.get('elevationInMeters'))

                            if "totalDistanceInMeters" in pt:
                                wp.Distance = int(pt.get('totalDistanceInMeters'))

                            if "speedMetersPerSecond" in pt:
                                wp.Speed = int(pt.get('speedMetersPerSecond'))

                            if "heartRate" in pt:
                                wp.HR = int(pt.get('heartRate'))

                            # current sample is = to lap occur , so store current nap and build a new one
                            if dateStartPoint in lapsdata:

                                lap = Lap(stats=activity.Stats, startTime=startTimeLap, endTime=dateStartPointDt)
                                lap.Waypoints = lapWaypoints
                                activity.Laps.append(lap)
                                # re init a new lap
                                startTimeLap = datetime.utcfromtimestamp(dateStartPoint)
                                lapWaypoints = []
                            # add occur
                            lapWaypoints.append(wp)

                        # build last lap
                        if len(lapWaypoints) > 0:
                            lap = Lap(stats=activity.Stats, startTime=startTimeLap, endTime=endTimeLap)
                            lap.Waypoints = lapWaypoints
                            activity.Laps.append(lap)
                    else:
                        activity.Laps = [Lap(startTime=activity.StartTime, endTime=activity.EndTime, stats=activity.Stats)]
                        logger.info("\t\tGarmin no laps, full laps")


                    break

        if len(activity.Laps) == 0 :
            activity.Stationary = True
            activity.GPS = False
            activity.Laps = [Lap(startTime=activity.StartTime, endTime=activity.EndTime, stats=activity.Stats)]
        return activity

    # Garmin Health is on read only access, we can't upload activities
    def UploadActivity(self, svcRecord, activity):
        logging.info("UPLOAD To Garming Health is not possible")
        pass

    def DeleteCachedData(self, serviceRecord):
        cachedb.garminhealth_cache.remove({"Owner": serviceRecord.ExternalID})
        cachedb.garminhealth_activity_cache.remove({"Owner": serviceRecord.ExternalID})


    def ExternalIDsForPartialSyncTrigger(self, req):
        data = json.loads(req.body.decode("UTF-8"))
        logger.info("GARMIN CALLBACK POKE")
        logging.info("GARMIN CALLBACK POKE")
        # Get user ids to sync
        external_user_ids = []
        if data['activityDetails'] is not None :
            for activity in data['activityDetails']:
                external_user_ids.append(activity['userId'])
                logging.info("GARMIN CALLBACK user to sync "+ activity['userId'])

                #add Flag in cache to only call when there is new activities
                redis_token_key = 'garminhealth:activities:%s' % activity['userId']
                redis.setex(redis_token_key, "1", timedelta(hours=24))

        return external_user_ids



