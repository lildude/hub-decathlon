# Synchronization module for SUUNTO
from tapiriik.settings import WEB_ROOT, SUUNTO_CLIENT_SECRET, SUUNTO_CLIENT_ID, SUUNTO_SUBSCRIPTION_KEY
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatisticUnit, ActivityStatistic, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity
from tapiriik.services.fit import FITIO
from tapiriik.database import db

from datetime import datetime, timedelta
from django.core.urlresolvers import reverse
from urllib.parse import urlencode

import logging
import pytz
import requests
import time
import json

logger = logging.getLogger(__name__)


class SuuntoService(ServiceBase):
    ID = "suunto"
    DisplayName = "Suunto"
    DisplayAbbreviation = "SUN"
    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True  # Because all services does that

    # Does it?
    ReceivesActivities = True  # Any at all?
    ReceivesStationaryActivities = True  # Manually-entered?
    ReceivesNonGPSActivitiesWithOtherSensorData = False  # Trainer-ish?
    SuppliesActivities = True

    SupportsExhaustiveListing = True
    SupportsActivityDeletion = False

    _activityTypeMappings = {
        ActivityType.Other: 9,
        ActivityType.Wheelchair: 9,
        ActivityType.RollerSkiing: 56,
        ActivityType.Running: 1,
        ActivityType.Cycling: 2,
        ActivityType.MountainBiking: 10,
        ActivityType.Elliptical: 55,
        ActivityType.Swimming: 21,
        ActivityType.Gym: 20,
        ActivityType.StrengthTraining: 17,
        ActivityType.Walking: 0,
        ActivityType.CrossCountrySkiing: 12,
        ActivityType.DownhillSkiing: 13,
        ActivityType.Snowboarding: 30,
        ActivityType.Rowing: 15,
        ActivityType.Hiking: 11,
        ActivityType.Skating: 49,
        ActivityType.StandUpPaddling: 61,
        ActivityType.Climbing: 29
    }

    _reverseActivityTypeMappings = {
        0: ActivityType.Walking,
        1: ActivityType.Running,
        2: ActivityType.Cycling,
        3: ActivityType.CrossCountrySkiing,
        4: ActivityType.Other,
        5: ActivityType.Other,
        6: ActivityType.Other,
        7: ActivityType.Other,
        8: ActivityType.Other,
        9: ActivityType.Other,
        10: ActivityType.MountainBiking,
        11: ActivityType.Hiking,
        12: ActivityType.CrossCountrySkiing,
        13: ActivityType.DownhillSkiing,
        14: ActivityType.Other,
        15: ActivityType.Rowing,
        16: ActivityType.Other,
        17: ActivityType.StrengthTraining,
        18: ActivityType.Other,
        19: ActivityType.Other,
        20: ActivityType.Gym,
        21: ActivityType.Swimming,
        22: ActivityType.Running,
        23: ActivityType.StrengthTraining,
        24: ActivityType.Walking,
        25: ActivityType.Other,
        26: ActivityType.Other,
        27: ActivityType.Other,
        28: ActivityType.Swimming,
        29: ActivityType.Climbing,
        30: ActivityType.Snowboarding,
        31: ActivityType.CrossCountrySkiing,
        32: ActivityType.Gym,
        33: ActivityType.Other,
        34: ActivityType.Other,
        35: ActivityType.Other,
        36: ActivityType.Other,
        37: ActivityType.Other,
        38: ActivityType.Other,
        39: ActivityType.Other,
        40: ActivityType.Other,
        41: ActivityType.Other,
        42: ActivityType.Other,
        43: ActivityType.Other,
        44: ActivityType.Other,
        45: ActivityType.Other,
        46: ActivityType.Other,
        47: ActivityType.Other,
        48: ActivityType.Other,
        49: ActivityType.Skating,
        50: ActivityType.Other,
        51: ActivityType.Other,
        52: ActivityType.Other,
        53: ActivityType.Other,
        54: ActivityType.StrengthTraining,
        55: ActivityType.Elliptical,
        56: ActivityType.RollerSkiing,
        57: ActivityType.Rowing,
        61: ActivityType.StandUpPaddling,
        69: ActivityType.StrengthTraining,
        81: ActivityType.Gym,
        85: ActivityType.Swimming
    }

    SupportedActivities = list(_activityTypeMappings.keys())

    def WebInit(self):
        params = {
            'client_id': SUUNTO_CLIENT_ID,
            'redirect_uri': WEB_ROOT + reverse("oauth_return", kwargs={"service": "suunto"}),
            'response_type': 'code'
        }
        self.UserAuthorizationURL = "https://cloudapi-oauth.suunto.com/oauth/authorize?" + \
            urlencode(params)

    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": SUUNTO_CLIENT_ID,
            "client_secret": SUUNTO_CLIENT_SECRET,
            "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "suunto"})
        }

        # TODO Implement this
        # self._rate_limit()

        response = requests.post(
            "https://cloudapi-oauth.suunto.com/oauth/token", data=params)
        if response.status_code != 200:
            raise APIException("Invalid code")
        data = response.json()

        authorizationData = {
            "AccessToken": data["access_token"],
            "AccessTokenExpiresAt": time.time()+data["expires_in"],
            "RefreshToken": data["refresh_token"]
        }
        return (data["user"], authorizationData)

    def DeleteCachedData(self, serviceRecord):
        # cachedb.suunto_cache.delete_many({"Owner": serviceRecord.ExternalID})
        # cachedb.suunto_activity_cache.delete_many({"Owner": serviceRecord.ExternalID})
        pass

    def RevokeAuthorization(self, serviceRecord):
        resp = self._requestWithAuth(lambda session: session.get(
            "https://cloudapi-oauth.suunto.com/oauth/deauthorize?"+urlencode({'client_id': SUUNTO_CLIENT_ID})), serviceRecord)
        if resp.status_code != 200:
            raise APIException("Unable to deauthorize Suunto auth token, status " +
                str(resp.status_code) + " resp " + resp.text)

    def _requestWithAuth(self, reqLambda, serviceRecord):
        session = requests.Session()
        # TODO Implement this
        # self._rate_limit()

        # If the token expires in 60 seconds or it is expired
        if time.time() > serviceRecord.Authorization.get("AccessTokenExpiresAt", 0) - 60:
            # We ask for refreshement
            response = requests.post("https://cloudapi-oauth.suunto.com/oauth/token", data={
                'client_id': SUUNTO_CLIENT_ID,
                'client_secret': SUUNTO_CLIENT_SECRET,
                'grant_type': "refresh_token",
                'refresh_token': serviceRecord.Authorization.get("RefreshToken")
            })

            if response.status_code != 200:
                raise APIException("No authorization to refresh token", block=True, user_exception=UserException(
                    UserExceptionType.Authorization, intervention_required=True))

            data = response.json()

            # We update the new token info in mongo
            authorizationData = {
                "AccessToken": data["access_token"],
                # Adding 30 days in sec as specified in the coros API doc
                "AccessTokenExpiresAt": time.time()+data["expires_in"],
                "RefreshToken": data["refresh_token"]
            }
            serviceRecord.Authorization.update(authorizationData)
            db.connections.update({"_id": serviceRecord._id}, {
                                  "$set": {"Authorization": authorizationData}})

        session.headers.update({
            "Authorization": "Bearer %s" % serviceRecord.Authorization["AccessToken"],
            "Ocp-Apim-Subscription-Key": SUUNTO_SUBSCRIPTION_KEY
        })
        return reqLambda(session)

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []

        # We make a date string epoch (with ms) of 2 years or 7 days before now for the exhaustive mechanism.
        beginDate = str((datetime.today()- timedelta(days=730 if exhaustive else 7)).strftime("%s")) + "000"

        resp = self._requestWithAuth(lambda session: session.get(
            "https://cloudapi.suunto.com/v2/workouts?since="+beginDate), svcRecord)

        if resp.status_code == 401:
            raise APIException("No authorization to retrieve activity list", block=True, user_exception=UserException(
                UserExceptionType.Authorization, intervention_required=True))
        elif resp.status_code != 200:
            raise APIException("Can't get user activity list")

        reqdata = resp.json()
        for ride in reqdata["payload"]:
            activity = UploadedActivity()

            activity.TZ = pytz.timezone("UTC")
            activity.StartTime = datetime.fromtimestamp(
                int(ride["startTime"]/1000))
            activity.EndTime = datetime.fromtimestamp(
                int(ride["startTime"]/1000)+ride["totalTime"])
            # Dont confuse the ActivityID in the activity's object instance in "ServiceData"
            #   and the Suunto API response "activityId" wich represent the sports type.
            # I know someone has messed up ^^.
            activity.ServiceData = {"ActivityID": ride["workoutKey"]}

            if ride["activityId"] not in self._reverseActivityTypeMappings:
                exclusions.append(
                    APIExcludeActivity("Unsupported activity type %s" %
                    ride["activityId"], 
                    activity_id=ride["workoutKey"], 
                    user_exception=UserException(UserExceptionType.Other))
                )
                logger.debug("\t\tUnknown activity")
                continue

            activity.Type = self._reverseActivityTypeMappings[ride["activityId"]]

            activity.Stats.Distance = ActivityStatistic(
                ActivityStatisticUnit.Meters, value=ride["totalDistance"])
            activity.Stats.Speed = ActivityStatistic(
                ActivityStatisticUnit.MetersPerSecond, avg=ride["avgSpeed"] if "avgSpeed" in ride else None, max=None)
            if "extensions" in ride.keys() and "SUMMARY" in ride["extensionTypes"]:
                activity.Stats.RunCadence.update(ActivityStatistic(
                    ActivityStatisticUnit.StepsPerMinute, avg=ride["extensions"][0]["avgCadence"]))
            activity.Stats.Energy = ActivityStatistic(
                ActivityStatisticUnit.Kilocalories, value=(ride["energyConsumption"]/1000))

            activity.Name = ride["description"] if "description" in ride.keys(
            ) else activity.Type

            isStationary = ride["isManuallyAdded"] or (ride["totalDistance"] == 0 and ride["startPosition"]
                ["x"] == ride["startPosition"]["x"] and ride["stopPosition"]["y"] == ride["stopPosition"]["y"])
            activity.Stationary = isStationary
            activity.GPS = not isStationary
            activity.Laps = [
                Lap(activity.StartTime, activity.EndTime, stats=activity.Stats)]

            activity.AdjustTZ()
            activity.CalculateUID()
            activities.append(activity)

        return activities, exclusions

    def DownloadActivity(self, svcRecord, activity):
        # If it's tagged stationnary, the fit file will exist but it will contain nothing except the file header
        if not activity.Stationary:
            # We don't redownload the activities but only the fit file thanks to the fitURL
            resp = self._requestWithAuth(lambda session: session.get(
                "https://cloudapi.suunto.com/v2/workout/exportFit/"+str(activity.ServiceData["ActivityID"])), svcRecord)
            fitFileBinary = resp.content
            activity = FITIO.Parse(fitFileBinary, activity)
        else:
            activity.GPS = False
            activity.Laps = [
                Lap(activity.StartTime, activity.EndTime, stats=activity.Stats)
            ]

        return activity

    def UploadActivity(self, svcRecord, activity):
        # Forcing a TimerTime mostly for manual activities. If it's None Suunto will not read the Fit File
        if activity.Stats.TimerTime.asUnits(ActivityStatisticUnit.Seconds).Value == None:
            activity.Stats.TimerTime = ActivityStatistic(ActivityStatisticUnit.Seconds, value=(activity.EndTime - activity.StartTime))

        initParams = {
            "description": activity.Name,
            "comment": "",
            "notifyUser": False
        }

        # Initialisation of the upload. Basically suunto send an unique URL for upload?
        initResp = self._requestWithAuth(lambda session: session.post("https://cloudapi.suunto.com/v2/upload/", data=json.dumps(initParams), headers={'Content-Type': 'application/json'}), svcRecord)

        # Suunto ask for some headers to be set for the PUT request
        putHeaders = initResp.json()["headers"]
        putHeaders["Content-Type"] = "application/octet-stream"

        # Here we have to simulate a file buffer with the activity bytes
        # because all my attempts to pass through the "data=" parameter have failed
        # But passing activity bytes through "files=" parameter works ¯\_(ツ)_/¯
        from io import BytesIO
        file_like = BytesIO(FITIO.Dump(activity))
        files = {'act1.fit': file_like}

        # We send the activity through the link sent by suunto.
        putResp = requests.request("PUT", initResp.json()["url"], files=files, headers=putHeaders)
        if putResp.status_code != 201:
            raise APIException("Unable to upload activity " + activity.UID + " response " + putResp.text + " status " + str(putResp.status_code))

        # We must sleep because the status that bring the workout ID is not instant
        # During test 1 sec is enough but to prevent some overload in suunto side we put 5 sec
        time.sleep(5)
        
        uploadStatus = self._requestWithAuth(lambda session: session.get("https://cloudapi.suunto.com/v2/upload/"+initResp.json()["id"]), svcRecord)
        if uploadStatus.json()["workoutKey"] == "":
            if uploadStatus.json()["status"] == "ERROR":
                raise APIException("Error: Suunto can't process the activity " + activity.UID + " response " + uploadStatus.text)
            raise APIException("Initialisation OK but the data was not sent " + activity.UID + " response " + uploadStatus.text)

        return uploadStatus.json()["workoutKey"]
