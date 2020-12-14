# Synchronization module for COROS
# Imports are based on the polarflow ones they will be afinated later
from tapiriik.settings import WEB_ROOT, COROS_CLIENT_SECRET, COROS_CLIENT_ID, COROS_API_BASE_URL, _GLOBAL_LOGGER, COLOG
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.api import APIException, UserException, UserExceptionType
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit
# from tapiriik.services.tcx import TCXIO
from tapiriik.database import db

from datetime import datetime, timedelta
from django.core.urlresolvers import reverse
from urllib.parse import urlencode
# from requests.auth import HTTPBasicAuth
# from io import StringIO

# import uuid
# import gzip
import logging
# import lxml
# import pytz
import requests
# import isodate
# import json
import time

logger = logging.getLogger(__name__)

class CorosService(ServiceBase):
    ID = "coros"
    DisplayName = "Coros"
    DisplayAbbreviation = "CRS"
    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True # Because all services does that
    # For the 2 following vars, waiting for more infos from Coros
    UserProfileURL = None
    UserActivityURL = None

    # Used only in tests | But to be verified in case of
    SupportsHR = SupportsCalories = SupportsCadence = SupportsTemp = SupportsPower = False

    # Enables extended auth ("Save these details") functionality
    RequiresExtendedAuthorizationDetails = False

    # URL to direct user to when starting authentication
    UserAuthorizationURL = None

    # List of ActivityTypes
    SupportedActivities = None

    
    # Does it?
    ReceivesActivities = True # Any at all?
    ReceivesStationaryActivities = True # Manually-entered?
    ReceivesNonGPSActivitiesWithOtherSensorData = True # Trainer-ish?
    SuppliesActivities = True
    # Services with this flag unset will receive an explicit date range for activity listing,
    # rather than the exhaustive flag alone. They are also processed after all other services.
    # An account must have at least one service that supports exhaustive listing.
    SupportsExhaustiveListing = True


    SupportsActivityDeletion = False


    # Causes synchronizations to be skipped until...
    #  - One is triggered (via IDs returned by ExternalIDsForPartialSyncTrigger or PollPartialSyncTrigger)
    #  - One is necessitated (non-partial sync, possibility of uploading new activities, etc)
    PartialSyncRequiresTrigger = False
    PartialSyncTriggerRequiresSubscription = False
    PartialSyncTriggerStatusCode = 200
    # Timedelta for polling to happen at (or None for no polling)
    PartialSyncTriggerPollInterval = None
    # How many times to call the polling method per interval (this is for the multiple_index kwarg)
    PartialSyncTriggerPollMultiple = 1

    # How many times should we try each operation on an activity before giving up?
    # (only ever tries once per sync run - so ~1 hour interval on average)
    UploadRetryCount = 5
    DownloadRetryCount = 5

    # Global rate limiting options
    # For when there's a limit on the API key itself
    GlobalRateLimits = []


    # For mapping common->Coros
    _activityTypeMappings = {
        ActivityType.Running: "8",
        ActivityType.Cycling: "9",
        ActivityType.Swimming: "10",
        ActivityType.Climbing: "14",
        ActivityType.Hiking: "16",
        ActivityType.Walking: "16", # There is no walking in coros but as it is a very common one it will be displayed ad hiking
        ActivityType.Gym: "18",
        ActivityType.CrossCountrySkiing: "19",
        ActivityType.Snowboarding: "21",
        ActivityType.DownhillSkiing: "21",
        ActivityType.StrengthTraining: "23"
        # ActivityType.Skating: "IceSkate",
        # ActivityType.Rowing: "Rowing",
        # ActivityType.Elliptical: "Elliptical",
        # ActivityType.RollerSkiing: "RollerSki",
        # ActivityType.StandUpPaddling: "StandUpPaddling",
    }

    # For mapping Coros->common
    _reverseActivityTypeMappings = {
        "8": ActivityType.Running,
        "9": ActivityType.Cycling,
        "10": ActivityType.Swimming,
        # "13": ActivityType. # TRIATHLON and MULTISPORT
        "14": ActivityType.Climbing,
        "15": ActivityType.Running,
        "16": ActivityType.Hiking,
        "18": ActivityType.Gym,
        "19": ActivityType.CrossCountrySkiing,
        "20": ActivityType.Running,
        "21": ActivityType.DownhillSkiing,
        # "22": ActivityType. # PILOT
        "23": ActivityType.StrengthTraining
    }

    SupportedActivities = list(_activityTypeMappings.keys())


    _BaseUrl = COROS_API_BASE_URL

    def WebInit(self):
        params = {
            'client_id': COROS_CLIENT_ID,
            'redirect_uri': WEB_ROOT + reverse("oauth_return", kwargs={"service": "coros"}),
            # Kinda look like the challenge string of strava (To test in conditions), but required though.
            'state': 'Potato',
            'response_type': 'code'
        }
        self.UserAuthorizationURL = self._BaseUrl+"/oauth2/authorize?" + urlencode(params)

    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {
            "grant_type": "authorization_code", 
            "code": code, 
            "client_id": COROS_CLIENT_ID, 
            "client_secret": COROS_CLIENT_SECRET, 
            "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "coros"})
        }

        # Implement this one if there is actual rate limits for coros
        # self._rate_limit()
        response = requests.post(self._BaseUrl+"/oauth2/accesstoken", data=params)
        if response.status_code != 200:
            raise APIException("Invalid code")
        data = response.json()

        authorizationData = {
            "AccessToken": data["access_token"],
            "AccessTokenExpiresAt": time.time()+data["expires_in"],
            "RefreshToken": data["refresh_token"]
        }
        return (data["openId"], authorizationData)

    def DeleteCachedData(self, serviceRecord):
        # Nothing to delete according to the Coros API specs
        pass

    def RevokeAuthorization(self, serviceRecord):
        # As there are no disconnect endpoints from coros this functions does not seem to be useful
        # For example for Strava we call https://www.strava.com/oauth/deauthorize
        # For polar flow we make a DELETE https://www.polaraccesslink.com/v3/users/{userid}
        pass

    def _refresh_token(self, serviceRecord):
        params = {
            'client_id': COROS_CLIENT_ID,
            'client_secret': COROS_CLIENT_SECRET,
            'grant_type': "refresh_token",
            'refresh_token': serviceRecord.Authorization.get("RefreshToken")
        }
        response = requests.post(self._BaseUrl+"/oauth2/refresh-token", data=params)

        tokenRefreshmentStatus = response.json()
        if tokenRefreshmentStatus["message"] != "OK":
            raise APIException("Can't refresh token")

        authorizationData = {
                "AccessToken": serviceRecord.Authorization.get("AccessToken"),
                "AccessTokenExpiresAt": time.time()+2592000, # Adding 30 days in sec as specified in the coros API doc
                "RefreshToken": serviceRecord.Authorization.get("RefreshToken")
            }

        serviceRecord.Authorization.update(authorizationData)
        db.connections.update({"_id": serviceRecord._id}, {"$set": {"Authorization": authorizationData}})

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []
        # before = earliestDate = None
        now = datetime.now()
        nowLessThirty = now - timedelta(days=30)

        params = {
            'token': svcRecord.Authorization.get("AccessToken"),
            'openId': svcRecord.ExternalID,
            'startDate': now.strftime("%Y%m%d"),
            'endDate': nowLessThirty.strftime("%Y%m%d")
        }

        # We refresh the token before asking for data
        self._refresh_token(svcRecord)
        # Then we ask for the activities done in coros
        response = requests.get(self._BaseUrl+"/v2/coros/sport/list?"+ urlencode(params))

        # If there is no data in the response so there is an error it can be everything (expired or wrong token, etc.)
        if response.json()["data"] == None:
            raise APIException("Bad request to Coros")
        
        reqdata = response.json()["data"]
        
        for ride in reqdata:
            activity = UploadedActivity()
            activity.TZ = ride["start_date"]
            activity.StartTime = ride["startTime"]
            activity.EndTime = ride["endTime"]
            activity.ServiceData = {"ActivityID": ride["labelId"]}

            if ride["type"] not in self._reverseActivityTypeMappings:
                exclusions.append(APIExcludeActivity("Unsupported activity type %s" % ride["type"], activity_id=ride["id"], user_exception=UserException(UserExceptionType.Other)))
                logger.debug("\t\tUnknown activity")
                continue

            activity.Type = self._reverseActivityTypeMappings[ride["type"]]

            activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=ride["distance"])
            if "avgSpeed" in ride:
                activity.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, avg=ride["avgSpeed"] if "avgSpeed" in ride else None, max=None)
            
            # activity.Stats.MovingTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=ride["moving_time"] if "moving_time" in ride and ride["moving_time"] > 0 else None)  # They don't let you manually enter this, and I think it returns 0 for those activities.
            # Strava doesn't handle "timer time" to the best of my knowledge - although they say they do look at the FIT total_timer_time field, so...?
            # if "average_watts" in ride:
            #     activity.Stats.Power = ActivityStatistic(ActivityStatisticUnit.Watts, avg=ride["average_watts"])

            # if "average_heartrate" in ride:
            #     activity.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=ride["average_heartrate"]))
            # if "max_heartrate" in ride:
            #     activity.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, max=ride["max_heartrate"]))

            if "avgFrequency" in ride:
                activity.Stats.Cadence.update(ActivityStatistic(ActivityStatisticUnit.StepsPerMinute, avg=ride["avgFrequency"]))

            # if "average_temp" in ride:
            #     activity.Stats.Temperature.update(ActivityStatistic(ActivityStatisticUnit.DegreesCelcius, avg=ride["average_temp"]))

            if "calorie" in ride:
                activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=ride["calorie"])

            activity.Name = ride["deviceName"]
            # activity.Stationary = ride["manual"]
            # activity.GPS = ("start_latlng" in ride) and (ride["start_latlng"] is not None)
            activity.AdjustTZ()
            activity.CalculateUID()
            activities.append(activity)


        return activities, exclusions