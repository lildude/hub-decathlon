from tapiriik.settings import WEB_ROOT, RELIVE_CLIENT_SECRET, RELIVE_CLIENT_ID
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.api import APIException, UserException, UserExceptionType
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit
from tapiriik.services.tcx import TCXIO
from tapiriik.database import cachedb, db


from datetime import datetime, timedelta
from django.core.urlresolvers import reverse
from urllib.parse import urlencode
from requests.auth import HTTPBasicAuth
from io import StringIO

import uuid
import gzip
import logging
import lxml
import requests
import time


logger = logging.getLogger(__name__)

class ReliveService(ServiceBase):
    ID = "relive"
    DisplayName = "Relive"
    DisplayAbbreviation = "RL"
    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True # otherwise looks ugly in the small frame

    UserProfileURL = "https://www.relive.cc/settings/profile"
    UserActivityURL = "https://www.relive.cc/settings/profile"

    SupportsHR = SupportsCalories = SupportsCadence = SupportsTemp = SupportsPower = True

    
    PartialSyncRequiresTrigger = True
    
    PartialSyncTriggerPollInterval = timedelta(minutes=1)

    # For mapping common->Relive
    _activity_type_mappings = {
        ActivityType.Cycling: "ride",
        ActivityType.MountainBiking: "ride",
        ActivityType.Hiking: "hike",
        ActivityType.Running: "run",
        ActivityType.Walking: "walk",
        ActivityType.Snowboarding: "snowboard",
        ActivityType.Swimming: "swim",
        ActivityType.Climbing: "hike",
        ActivityType.Other: "other",
    }

    # Relive -> common
    _reverse_activity_type_mappings = {
        "run": ActivityType.Running,
        "ride": ActivityType.Cycling,
        "ride": ActivityType.MountainBiking,
        "walk": ActivityType.Walking,
        "hike": ActivityType.Hiking,
        "ski": ActivityType.DownhillSkiing,
        "ski": ActivityType.CrossCountrySkiing,
        "snowboard": ActivityType.Snowboarding,
        "other": ActivityType.Other,

      
    }

    SupportedActivities = list(_activity_type_mappings.keys())

    _api_endpoint = "https://public.api.relive.cc/v1"



    def WebInit(self):
        params = {'response_type':'code',
                  'client_id': RELIVE_CLIENT_ID,
                  'state':'12345',
                  'redirect_uri': WEB_ROOT + reverse("oauth_return", kwargs={"service": "relive"})}
        self.UserAuthorizationURL = "https://www.relive.cc/oauth/authorize?scope=activity%3Aread%20activity%3Awrite&" + urlencode(params)

    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {"grant_type": "authorization_code",
                  "code": code,
                  "client_id": RELIVE_CLIENT_ID,
                  "client_secret": RELIVE_CLIENT_SECRET,
                  "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "relive"})}

        response = requests.post(self._api_endpoint + "/oauth/token", data=params)
        data = response.json()

        if response.status_code != 200:
            raise APIException(data["error"])

        
        #Get user ID from Relive
        params = {"Authorization": "Bearer "+ data["access_token"]}

        responseUser = requests.get(self._api_endpoint + "/user", headers=params)
        if responseUser.status_code != 200:
            raise APIException("Invalid code")
        dataUser = responseUser.json()
        userId = dataUser["user_id"]

        expiresAt = time.time() + data["expires_in"]

        authorizationData = {
            "AccessToken": data["access_token"],
            "AccessTokenExpiresAt": expiresAt,
            "RefreshToken": data["refresh_token"]
        }

        return (userId, authorizationData)


    def _apiHeaders(self, serviceRecord):
        if serviceRecord.Authorization["AccessTokenExpiresAt"] < time.time() :
            #refresh access token

            response = requests.post(self._api_endpoint + "/oauth/token", data={
                "grant_type": "refresh_token",
                "refresh_token": serviceRecord.Authorization["RefreshToken"],
                "client_id": RELIVE_CLIENT_ID,
                "client_secret": RELIVE_CLIENT_SECRET,
            })
            if response.status_code != 200:
                raise APIException("No authorization to refresh token", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
            data = response.json()
            
            expiresAt = time.time() + data["expires_in"]
            authorizationData = {
                        "AccessToken": data["access_token"],
                        "AccessTokenExpiresAt": expiresAt,
                        "RefreshToken": data["refresh_token"]
                    }
            serviceRecord.Authorization.update(authorizationData)
            db.connections.update({"_id": serviceRecord._id}, {"$set": {"Authorization": authorizationData}})


        return {"Authorization": "Bearer " + serviceRecord.Authorization["AccessToken"]}

    def RevokeAuthorization(self, serviceRecord):
        pass

    def SubscribeToPartialSyncTrigger(self, serviceRecord):
        serviceRecord.SetPartialSyncTriggerSubscriptionState(True)

    def UnsubscribeFromPartialSyncTrigger(self, serviceRecord):
        serviceRecord.SetPartialSyncTriggerSubscriptionState(False)

    def PollPartialSyncTrigger(self, multiple_index):
        pass

    def DownloadActivityList(self, serviceRecord, exhaustive=False):
        activities = []
        exclusions = []
        
        res = requests.get(self._api_endpoint + "/user/activities", headers=self._apiHeaders(serviceRecord))
        
        if res.status_code == 200: # otherwise no new data, skip
            for activity_url in res.json()["activities"]:
                data = requests.get(activity_url, headers=self._apiHeaders(serviceRecord))
                if data.status_code == 200:
                    activity = self._create_activity(data.json())
                    activities.append(activity)
                else:
                    # may be just deleted, who knows, skip
                    logger.debug("Cannot recieve training at url: {}".format(activity_url))

        return activities, exclusions

    def _create_activity(self, activity_data):
        activity = UploadedActivity()

        activity.GPS = not activity_data["has-route"]
        if "detailed-sport-info" in activity_data and activity_data["detailed-sport-info"] in self._reverse_activity_type_mappings:
            activity.Type = self._reverse_activity_type_mappings[activity_data["detailed-sport-info"]]
        else:
            activity.Type = ActivityType.Other

        activity.StartTime = pytz.utc.localize(isodate.parse_datetime(activity_data["start-time"]))
        activity.EndTime = activity.StartTime + isodate.parse_duration(activity_data["duration"])

        distance = activity_data["distance"] if "distance" in activity_data else None
        activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=float(distance) if distance else None)
        hr_data = activity_data["heart-rate"] if "heart-rate" in activity_data else None
        avg_hr = hr_data["average"] if "average" in hr_data else None
        max_hr = hr_data["maximum"] if "maximum" in hr_data else None
        activity.Stats.HR.update(ActivityStatistic(ActivityStatisticUnit.BeatsPerMinute, avg=float(avg_hr) if avg_hr else None, max=float(max_hr) if max_hr else None))
        calories = activity_data["calories"] if "calories" in activity_data else None
        activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=int(calories) if calories else None)

        activity.ServiceData = {"ActivityID": activity_data["id"]}

        logger.debug("\tActivity s/t {}: {}".format(activity.StartTime, activity.Type))

        activity.CalculateUID()
        return activity

    def DownloadActivity(self, serviceRecord, activity):
        # NOTE tcx have to be gzipped but it actually doesn't
        # https://www.polar.com/accesslink-api/?python#get-tcx
        #tcx_data_raw = requests.get(activity_link + "/tcx", headers=self._api_headers(serviceRecord))
        #tcx_data = gzip.GzipFile(fileobj=StringIO(tcx_data_raw)).read()
        tcx_url = serviceRecord.ServiceData["Transaction-uri"] + "/exercises/{}/tcx".format(activity.ServiceData["ActivityID"])
        response = requests.get(tcx_url, headers=self._apiHeaders(serviceRecord, {"Accept": "application/vnd.garmin.tcx+xml"}))
        if response.status_code == 404:
            # Transaction was disbanded, all data linked to it will be returned in next transaction
            raise APIException("Transaction disbanded", user_exception=UserException(UserExceptionType.DownloadError))
        try:
            tcx_data = response.text
            activity = TCXIO.Parse(tcx_data.encode('utf-8'), activity)
        except lxml.etree.XMLSyntaxError:
            raise APIException("Cannot recieve training tcx at url: {}".format(tcx_url), user_exception=UserException(UserExceptionType.DownloadError))
        return activity

    def DeleteCachedData(self, serviceRecord):
        # Nothing to delete
        pass

    def DeleteActivity(self, serviceRecord, uploadId):
        # Not supported
        pass

    def UploadActivity(self, serviceRecord, activity):
        # Not supported
        pass
