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
from requests_oauthlib import OAuth1Session

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
    REQUEST_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/request_token"
    # POST # URI to get user token/token_secret
    ACCESS_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
    # GET # URI to get user auth and verifier token
    OAUTH_TOKEN_URL ="http://connect.garmin.com/oauthConfirm"
    # GET # URI to get user ID
    URI_USER_ID = "https://healthapi.garmin.com/wellness-api/rest/user/id"
    # GET # URI to get user activities summary
    URI_ACTIVITIES_SUMMARY = "https://healthapi.garmin.com/wellness-api/rest/activities"
    URI_ACTIVITIES_DETAIL = "https://healthapi.garmin.com/wellness-api/rest/activityDetails"

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
        ActivityType.Yoga: "YOGA",
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
        "INDOOR_CARDIO": ActivityType.Gym,
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
        "YOGA": ActivityType.Yoga
    }

    SupportedActivities = list(_activityTypeMappings.keys())

    def UserUploadedActivityURL(self, uploadId):
        return "https://connect.garmin.com/modern/activity/" + str(uploadId)

    # Use this function to get Autorization URL
    def WebInit(self):
        self.UserAuthorizationURL = reverse("oauth_redirect", kwargs={"service": "garminhealth"})


    # Helper to initialize the Oauth v1 Session
    def _oauthSession(self, connection=None, **params):
        if connection:
            params["resource_owner_key"] = connection.Authorization["AccessToken"]
            params["resource_owner_secret"] = connection.Authorization["AccessTokenSecret"]
        return OAuth1Session(GARMINHEALTH_KEY, client_secret=GARMINHEALTH_SECRET, **params)

    def GenerateUserAuthorizationURL(self, session, level=None):
        # Generation of an Oauth v1 session (This should be empty at this point)
        oauthSession = self._oauthSession(callback_uri=WEB_ROOT + reverse("oauth_return", kwargs={"service": "garminhealth"}))
        # Fetching the tokens from the session
        tokens = oauthSession.fetch_request_token(self.REQUEST_TOKEN_URL)
        # The secret is saved in redis else it will be lost when we exit the function.
        redis_token_key = "garminhealth:oauth:%s" % tokens["oauth_token"]
        redis.setex(redis_token_key, tokens["oauth_token_secret"], timedelta(hours=24))
        return oauthSession.authorization_url(self.OAUTH_TOKEN_URL)


    # This function is used to set token info for a user, get expiration date, refresh and access token
    def RetrieveAuthorizationToken(self, req, level):
        # Retrieving the previously saved secret
        redis_token_key = "garminhealth:oauth:%s" % req.GET.get("oauth_token")
        secret = redis.get(redis_token_key)
        redis.delete(redis_token_key)

        # Now getting the access token
        oauthSession = self._oauthSession(resource_owner_secret=secret)
        oauthSession.parse_authorization_response(req.get_full_path())
        tokens = oauthSession.fetch_access_token(self.ACCESS_TOKEN_URL)

        # We are now ready to send auth request to the service so we get the user ID to save it in mongo
        userInfo = oauthSession.get(self.URI_USER_ID)
        OAuth_data = {
            "OAuthToken": req.GET.get("oauth_token"),
            "AccessToken": tokens["oauth_token"],
            "AccessTokenSecret": tokens["oauth_token_secret"],
            "AccessTokenRequestedAt": datetime.now(timezone.utc)
        }
        return (userInfo.json()["userId"], OAuth_data)


    # This function is used to revoke access token
    def RevokeAuthorization(self, serviceRecord):
        # Garmin has no revoke Auth endpoint. 
        # Their doc says that users have to disconnect the app directly in garmin connect.
        # https://connect.garmin.com/modern/account
        logging.info("Revoke Garmin Authorization")
        pass
  

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        oauthSession = self._oauthSession(svcRecord)

        activities = []
        exclusions = []

        # WARNING : BE CAREFULL ABOUT DATE FILTER
        # date filter of this request will follow this process :
        # - fetching activity with uploaded date between  upload_start_time & upload_end_time
        # - return matched activities
        # For example :
        # if you upload at 20-05-2019 an activity into Garmin with start date 01-01-2019
        # and you use upload_start_time=20-05-2019 & upload_end_time=21-05-2019
        # the 01-01-2019 will be return
        # So we download activities from upload date

        redis_key = "garminhealth:webhook:"+str(svcRecord.ExternalID)
        activity_urls_list = redis.lrange(redis_key, 0, -1)
        pre_download_counter = post_download_counter = 0

        for act_url in activity_urls_list:
            # We delete it from the redis list to avoid syncing a second time
            # For an strange reason we have to do :
            #       redis.lrem(key, value)
            # Even if redis, redis-py docs and the signature of the function in the container ask to do
            #       redis.lrem(key, count ,value)
            result = redis.lrem(redis_key, act_url)
            if result == 0:
                logger.warning("Cant delete the activity id from the redis key %s" % (redis_key))
            elif result > 1 :
                logger.warning("Found more than one time the activity id from the redis key %s" % (redis_key))

            resp = oauthSession.get(act_url)

            if resp.status_code != 204 and resp.status_code != 200:
                logger.info("\tAn error occured while downloading Garmin Health activity, status code %s, content %s" % (
                    (str(resp.status_code), resp.content)))

            try:
                json_data = resp.json()
            except ValueError:
                raise APIException("Failed parsing Garmin Health response %s - %s" % (resp.status_code, resp.text), trigger_exhaustive=False)

            logger.info(json_data)
            item = json_data[0].get("summary")
            itemID = json_data[0].get("summaryId")[:-7]

            pre_download_counter += 1
            activity = UploadedActivity()
            activity_name = item['activityType'] + " - " + item['deviceName'] if item['deviceName'] != 'unknown' else item['activityType']

            # parse date start to get timezone and date
            activity.TZ = pytz.utc
            activity.StartTime = datetime.utcfromtimestamp(item['startTimeInSeconds'])
            activity.EndTime = activity.StartTime + timedelta(seconds=item["durationInSeconds"])
            logger.debug("\tActivity start s/t %s: %s" % (activity.StartTime, activity_name))

            activity.ServiceData = {"ActivityID": itemID}
            activity.ServiceData['Manual'] = "manual" in item

            # check if activity type ID exists
            logger.info("\tActivity Type Garmin : " + str(item["activityType"]) + " - user_id " + svcRecord.ExternalID )
            if item["activityType"] not in self._reverseActivityTypeMappings:
                # TODO : Uncomment it when test are done
                #exclusions.append(
                #    APIExcludeActivity("Unsupported activity type %s" % item["activityType"],
                #                       activity_id=item["summaryId"],
                #                       user_exception=UserException(UserExceptionType.Other)))
                logger.info("\t\tUnknown activity")
                continue

            activity.Type = self._reverseActivityTypeMappings[item["activityType"]]

            activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=item.get("distanceInMeters"))
            activity.Stats.Speed = ActivityStatistic(
                ActivityStatisticUnit.MetersPerSecond,
                avg=item.get("averageSpeedInMetersPerSecond"),
                max=item.get("maxSpeedInMetersPerSecond")
            )

            activity.Stats.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=item.get("movingDurationInSeconds"))
            activity.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts,avg=item.get("powerInWatts"))
            activity.Stats.HR = ActivityStatistic(
                ActivityStatisticUnit.BeatsPerMinute,
                avg=item.get("averageHeartRateInBeatsPerMinute"),
                max=item.get("maxHeartRateInBeatsPerMinute"))

            activity.Stats.Cadence = ActivityStatistic(
                ActivityStatisticUnit.RevolutionsPerMinute,
                avg=item.get("averageBikeCadenceInRoundsPerMinute"),
                max=item.get("maxBikeCadenceInRoundsPerMinute"))

            activity.Stats.RunCadence = ActivityStatistic(
                ActivityStatisticUnit.StepsPerMinute,
                avg=item.get("averageRunCadenceInStepsPerMinute"),
                max=item.get("maxRunCadenceInStepsPerMinute"))
            
            # TODO: See if temperature should be body temperature or air temperature
            #       Because Garmin provides "airTemperatureCelcius" in data
            # if "average_temp" in ride:
            #    activity.Stats.Temperature.update(
            #        ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, avg=ride["average_temp"]))

            activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=item.get("activeKilocalories"))
            activity.Stationary = not "startingLatitudeInDegree" in item
            activity.GPS = "startingLatitudeInDegree" in item

            activity.AdjustTZ()
            activity.CalculateUID()
            post_download_counter += 1
            activities.append(activity)
            logger.info("\tGarmin Activity ID : " + itemID)

        logger.info("\t\t total Garmin activities downloaded : %i" % pre_download_counter)
        logger.info("\t\t\t Listed activities by redis : %i" % len(activity_urls_list))
        logger.info("\t\t\t Number of activities passed though download : %i" % post_download_counter)
        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):
        oauthSession = self._oauthSession(svcRecord)

        data = {
                'uploadStartTimeInSeconds': (datetime.now()-timedelta(days=1)).strftime('%s'),
                'uploadEndTimeInSeconds': datetime.now().strftime('%s'),
            }
        resp = oauthSession.get(self.URI_ACTIVITIES_DETAIL +"?"+ urlencode(data))

        if resp.status_code != 204 and resp.status_code != 200:
            logging.info("\t An error occured while downloading Garmin Health activities from %s to %s " % (
                    (datetime.now()-timedelta(days=1)).strftime('%s'), datetime.now().strftime('%s')))

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
        # Get user ids to sync
        external_user_ids = []
        if data.get('activityDetails') != None :
            for activity in data['activityDetails']:
                # Pushing the callback url in redis that will be used in downloadActivityList
                redis.rpush("garminhealth:webhook:%s" % activity['userId'], activity["callbackURL"])
                external_user_ids.append(activity['userId'])
                logging.info("\tGARMIN CALLBACK user to sync "+ activity['userId'])

        return external_user_ids



