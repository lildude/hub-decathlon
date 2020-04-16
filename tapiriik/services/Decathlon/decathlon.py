# Synchronization module for decathloncoach.com
# (c) 2018 Charles Anssens, charles.anssens@decathlon.com
from tapiriik.settings import WEB_ROOT, DECATHLON_CLIENT_SECRET, DECATHLON_CLIENT_ID, DECATHLON_API_KEY, DECATHLON_API_BASE_URL, DECATHLON_RATE_LIMITS
from tapiriik.services.ratelimiting import RateLimit, RateLimitExceededException
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.database import cachedb
from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit, Waypoint, WaypointType, Location, Lap
from tapiriik.services.api import APIException, UserException, UserExceptionType, APIExcludeActivity, ServiceException
from tapiriik.database import db

from django.core.urlresolvers import reverse
from datetime import datetime, timedelta
from urllib.parse import urlencode
import calendar
import requests
import os
import logging
import pytz
import re
import time
import json
from dateutil.parser import parse


class DecathlonService(ServiceBase):
    ID = "decathlon"
    DisplayName = "Decathlon"
    DisplayAbbreviation = "DC"
    AuthenticationType = ServiceAuthenticationType.OAuth
    UserProfileURL = "https://www.decathloncoach.com/fr-fr/portal/?{0}"
    UserActivityURL = "http://www.decathloncoach.com/fr-fr/portal/activities/{1}"
    accountOauth = "https://account.geonaute.com/oauth"
    AuthenticationNoFrame = True  # They don't prevent the iframe, it just looks really ugly.
    PartialSyncRequiresTrigger = False
    LastUpload = None

    GlobalRateLimits = DECATHLON_RATE_LIMITS

    OauthEndpoint = "https://account.geonaute.com"
    
    SupportsHR = SupportsCadence = SupportsTemp = SupportsPower = False

    SupportsActivityDeletion = False

    # For mapping common->Decathlon sport id
    _activityTypeMappings = {
        ActivityType.Cycling: "381",
        ActivityType.MountainBiking: "388",
        ActivityType.Hiking: "153",
        ActivityType.Running: "121",
        ActivityType.Walking: "113",
        ActivityType.Snowboarding: "185",
        ActivityType.Skating: "20",
        ActivityType.CrossCountrySkiing: "183",
        ActivityType.DownhillSkiing: "176",
        ActivityType.Swimming: "274",
        ActivityType.Gym: "91",
        ActivityType.Rowing: "398",
        ActivityType.Elliptical: "397",
        ActivityType.RollerSkiing: "367",
        ActivityType.StrengthTraining: "98",
        ActivityType.Climbing: "153",
        ActivityType.Other: "121"
    }

    # For mapping Decathlon sport id->common
    _reverseActivityTypeMappings = {
        "381": ActivityType.Cycling,
        "385": ActivityType.Cycling,
        "401": ActivityType.Cycling,#Home Trainer"
        "388": ActivityType.MountainBiking,
        "121": ActivityType.Running,
        "126": ActivityType.Running,#trail
        "153": ActivityType.Hiking,
        "113": ActivityType.Walking,
        "114": ActivityType.Walking,#nordic walking
        "320": ActivityType.Walking,
        "176": ActivityType.DownhillSkiing,
        "177": ActivityType.CrossCountrySkiing,#Nordic skiing
        "183": ActivityType.CrossCountrySkiing,#Nordic skiing alternatif
        "184": ActivityType.CrossCountrySkiing,#Nordic skiing skating
        "185": ActivityType.Snowboarding,
        "274": ActivityType.Swimming,
        "91": ActivityType.Gym,
        "263": ActivityType.Rowing,
        "98": ActivityType.StrengthTraining,
        "161" : ActivityType.Climbing,
        "397" : ActivityType.Elliptical,
        "367" : ActivityType.RollerSkiing,
        "99" : ActivityType.Other,
        "168": ActivityType.Walking,
        #"402": ActivityType.Walking,
        "109":ActivityType.Gym,#pilates
        "174": ActivityType.DownhillSkiing,
        "264" : ActivityType.Other, #bodyboard
        "296" : ActivityType.Other, #Surf
        "301" : ActivityType.Other, #sailling
        "173": ActivityType.Walking, #ski racket
        "110": ActivityType.Cycling,#bike room
        "395": ActivityType.Running,
        "79" : ActivityType.Other, #dansing
        "265" : ActivityType.Other,#Canoë kayak
        "77" : ActivityType.Other,#Triathlon
        "200" : ActivityType.Other,#horse riding
        "273" : ActivityType.Other,#Kite surf
        "280" : ActivityType.Other,#sailbard
        "360" : ActivityType.Other,#BMX"
        "374" : ActivityType.Other,#Skate board
        "260" : ActivityType.Other,#Aquagym
        "45" : ActivityType.Other,#Martial arts
        "335" : ActivityType.Other,#Badminton
        "10" : ActivityType.Other,#Basketball
        "35" : ActivityType.Other,#Boxe
        "13" : ActivityType.Other,#Football
        "18" : ActivityType.Other,#Handball
        "20" : ActivityType.Other,#Hockey
        "284" : ActivityType.Other,#diving
        "398" : ActivityType.Rowing,#rower machine
        "27" : ActivityType.Other,#Rugby
        "357" : ActivityType.Other,#Tennis
        "32" : ActivityType.Other,#Volleyball
        "399" : ActivityType.Other,#Run & Bike
        "105" : ActivityType.Other,#Yoga
        "354" : ActivityType.Other,#Squash
        "358" : ActivityType.Other,#Table tennis
        "7" : ActivityType.Other,#paragliding
        "400" : ActivityType.Other,#Stand Up Paddle
        "340" : ActivityType.Other,#Padel
        "326" : ActivityType.Other,#archery
        "366" : ActivityType.Other#Yatching
    }
    
    _unitMap = {
        "duration": "24",
        "distance": "5",
        "kcal" : "23",
        "speedaverage" : "9",
        "hrcurrent" : "1",
        "speedcurrent" : "6",
        "hravg" : "4"
    }

    SupportedActivities = list(_activityTypeMappings.keys())

    def __init__(self):
        logging.getLogger('Decathlon SVC')
        return None

    def UserUploadedActivityURL(self, uploadId):
        return "https://www.decathloncoach.com/fr-FR/portal/activities/%d" % uploadId


    def WebInit(self):
        params = {
                  'client_id':DECATHLON_CLIENT_ID,
                  'response_type':'code',
                  'redirect_uri':WEB_ROOT + reverse("oauth_return", kwargs={"service": "decathlon"})}
        self.UserAuthorizationURL = self.OauthEndpoint +"/oauth/authorize?" + urlencode(params)


    def RetrieveAuthorizationToken(self, req, level):
        code = req.GET.get("code")
        params = {"grant_type": "authorization_code", "code": code, "client_id": DECATHLON_CLIENT_ID, "client_secret": DECATHLON_CLIENT_SECRET, "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "decathlon"})}

        response = requests.get(self.accountOauth + "/accessToken", params=params)
        if response.status_code != 200:
            raise APIException("Invalid code")
        data = response.json()
        refresh_token = data["access_token"]
        
        # Retrieve the user ID, meh.
        id_resp = requests.get(self.OauthEndpoint + "/api/me?access_token=" + data["access_token"])

        # register the webhook to receive callbacks for new activities
        jwt = id_resp.json()["requestKey"]
        headers = {"Authorization": "Bearer %s" % jwt, 'User-Agent': 'Hub User-Agent' , 'X-Api-Key': DECATHLON_API_KEY, 'Content-Type': 'application/json'}
        # first check if not exist
        webhook_exists = False
        resp = requests.get(DECATHLON_API_BASE_URL + "/v2/user_web_hooks", headers=headers)
        if resp.status_code == 200 :
            answer_json = json.loads(resp.content)
            for web_hook in answer_json['hydra:member'] :
                if web_hook["url"] == WEB_ROOT+'/sync/remote_callback/trigger_partial_sync/'+self.ID :
                    webhook_exists = True
        
        if webhook_exists == False :
            data_json = '{"user": "/v2/users/'+id_resp.json()["ldid"]+'", "url": "'+WEB_ROOT+'/sync/remote_callback/trigger_partial_sync/'+self.ID+'", "events": ["activity_create"]}'
            requests.post(DECATHLON_API_BASE_URL + "/v2/user_web_hooks", data=data_json, headers=headers)
        self._rate_limit()
        

        return (id_resp.json()["ldid"], {"RefreshToken": refresh_token})

    def RevokeAuthorization(self, serviceRecord):
        resp = requests.get(self.OauthEndpoint + "/logout?access_token="+serviceRecord.Authorization["RefreshToken"])
        if resp.status_code != 204 and resp.status_code != 200:
            raise APIException("Unable to deauthorize Decathlon auth token, status " + str(resp.status_code) + " resp " + resp.text)
        pass

    def _getAuthHeaders(self, serviceRecord=None):
        response = requests.get(self.OauthEndpoint + "/api/me?access_token="+serviceRecord.Authorization["RefreshToken"])
        if response.status_code != 200:
            if response.status_code >= 400 and response.status_code < 500:
                raise APIException("Could not retrieve refreshed token %s %s" % (response.status_code, response.text), block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
            raise APIException("Could not retrieve refreshed token %s %s" % (response.status_code, response.text))
        requestKey = response.json()["requestKey"]
        return {"Authorization": "Bearer %s" % requestKey, 'Content-Type' : 'application/json', 'User-Agent': 'Hub User-Agent' , 'X-Api-Key' : DECATHLON_API_KEY}

    def _parseDate(self, date):
        #model '2017-12-01T12:00:00+00:00'
        return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+%Z").replace(tzinfo=pytz.utc)

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []

        page_number = 0
        page_total = 1

        while page_number < page_total:
            page_number += 1
            headers = self._getAuthHeaders(svcRecord)
            resp = requests.get(DECATHLON_API_BASE_URL + "/v2/activities?user=" + str(svcRecord.ExternalID) + "&page=" + str(page_number), headers=headers)
            if resp.status_code == 400:
                logging.info(resp.content)
                raise APIException("No authorization to retrieve activity list", block = True, user_exception = UserException(UserExceptionType.Authorization, intervention_required = True))
            if resp.status_code == 401:
                logging.info(resp.content)
                raise APIException("No authorization to retrieve activity list", block = True, user_exception = UserException(UserExceptionType.Authorization, intervention_required = True))
            if resp.status_code == 403:
                logging.info(resp.content)
                raise APIException("No authorization to retrieve activity list", block = True, user_exception = UserException(UserExceptionType.Authorization, intervention_required = True))

            resp_activities = json.loads(resp.content.decode('utf-8'))

            #set page total
            if "hydra:next" in resp_activities["hydra:view"] :
                if resp_activities["hydra:view"]["hydra:next"] is not None :
                    page_total += 1
                    
      
            logging.info("\t\t nb activity : " + str(len(resp_activities["hydra:member"])))
            for ride in resp_activities["hydra:member"]:
    
                activity = UploadedActivity()
                activity.TZ = pytz.timezone("UTC")  

                startdate = ride["startdate"]
                datebase = parse(startdate)
                

                activity.StartTime = datebase #pytz.utc.localize(datebase)
                
                activity.ServiceData = {"ActivityID": ride["id"], "Manual": ride["manual"]}
                
                logging.info("\t\t Decathlon Activity ID : " + ride["id"])
    
                sport_uri = ride["sport"]
                sport = sport_uri.replace("/v2/sports/", "")
                if sport not in self._reverseActivityTypeMappings:
                    exclusions.append(APIExcludeActivity("Unsupported activity type %s" % sport, activity_id=ride["id"], user_exception=UserException(UserExceptionType.Other)))
                    logging.info("\t\tDecathlon Unknown activity, sport id " + sport + " is not mapped")
                    continue
    
                activity.Type = self._reverseActivityTypeMappings[sport]
                
                val = ride["dataSummaries"]
                if self._unitMap["duration"] in val:
                    activity.EndTime = activity.StartTime + timedelta(0, int(val[self._unitMap["duration"]]))
                if self._unitMap["distance"] in val:
                    activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=int(val[self._unitMap["distance"]]))
                if self._unitMap["kcal"] in val:
                    activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=int(val[self._unitMap["kcal"]]))
                if self._unitMap["hravg"] in val:
                    activity.Stats.HR.Average = int(val[self._unitMap["hravg"]])
                if self._unitMap["speedaverage"] in val:
                    meterperhour = int(val[self._unitMap["speedaverage"]])
                    kmperhour = float(meterperhour/1000)
                    activity.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.KilometersPerHour, avg=kmperhour, max= None)
    
                if ride["name"] == "" or ride["name"] is None:
                    txtdate = startdate.split(' ')
                    activity.Name = "Sport Decathlon " + txtdate[0]
                else:
                    activity.Name = ride["name"]
                
                activity.Private = False
                if ride["manual"] == True :
                    activity.Stationary = True
                else :
                    activity.Stationary = False
                activity.GPS = ride["trackFlag"]
                activity.AdjustTZ()
                activity.CalculateUID()
                activities.append(activity)

            if not exhaustive:
                break

        return activities, exclusions

    def ExternalIDsForPartialSyncTrigger(self, req):
        # BE CAREFUL Decathlon is sending only one elem

        data = json.loads(req.body.decode("UTF-8"))
        # Get user id to sync
        external_user_ids = []
        external_user_ids.append(data['user_id'])

        return external_user_ids

    def DownloadActivity(self, svcRecord, activity):
        activityID = activity.ServiceData["ActivityID"]

        logging.info("\t\t DC LOADING  : " + str(activityID))

        headers = self._getAuthHeaders(svcRecord)
        self._rate_limit()
        resp = requests.get(DECATHLON_API_BASE_URL + "/v2/activities/" + activityID , headers=headers)

        if resp.status_code == 401:
            raise APIException("No authorization to download activity", block = True, user_exception = UserException(UserExceptionType.Authorization, intervention_required = True))

        try:
            root = json.loads(resp.content.decode('utf-8'))
        except:
            raise APIException("Stream data returned from Decathlon is not JSON")

        activity.GPS = False
        activity.Stationary = True
        #work on date
        startdate = root["startdate"]
        datebase = parse(startdate)

        ridedata = {}
        ridedataindex = []

        if "locations" in root and root["locations"] is not None:
            for pt in root["locations"]:
                delta = int(pt)
                ridedataindex.append(delta)
                ridedata[delta] = {}
                ridedata[delta]['LATITUDE'] = float(root["locations"][pt]["latitude"])
                ridedata[delta]['LONGITUDE'] = float(root["locations"][pt]["longitude"])
                ridedata[delta]['ELEVATION'] = int(root["locations"][pt]["elevation"])
            
        if len(ridedata)>0 :
            activity.GPS = True
            activity.Stationary = False

        if "datastream" in root and root["datastream"] is not None:
            for measure in root["datastream"]:
                delta = int(measure)
                if delta not in ridedataindex :
                    ridedataindex.append(delta)
                    ridedata[delta] = {}

                if "5" in root["datastream"][measure]:
                    ridedata[delta]['DISTANCE'] = int(root["datastream"][measure]["5"])
                if "1" in root["datastream"][pt]:
                    ridedata[delta]['HR'] = int(root["datastream"][pt]["1"])
                if "6" in root["datastream"][measure]:
                    ridedata[delta]['SPEED'] = int(root["datastream"][measure]["6"])
                if "20" in root["datastream"][measure]:
                    ridedata[delta]['LAP'] = int(root["datastream"][measure]["20"])

        ridedataindex.sort()


        if len(ridedata) == 0 :
            lap = Lap(stats=activity.Stats, startTime=activity.StartTime, endTime=activity.EndTime)
            activity.Laps = [lap]
        else :
            lapWaypoints = []
            startTimeLap = activity.StartTime
            for elapsedTime in ridedataindex:
                rd = ridedata[elapsedTime]
                wp = Waypoint()
                delta = elapsedTime
                formatedDate = datebase + timedelta(seconds=delta)
                wp.Timestamp = formatedDate#self._parseDate(formatedDate.isoformat())

                if 'LATITUDE' in rd :
                    wp.Location = Location()
                    wp.Location.Latitude = rd['LATITUDE']
                    wp.Location.Longitude = rd['LONGITUDE']
                    wp.Location.Altitude = rd['ELEVATION']

                if 'HR' in rd :
                    wp.HR = rd['HR']

                if 'SPEED' in rd :
                    wp.Speed = round(rd['SPEED'] / 3600,2)

                if 'DISTANCE' in rd :
                    wp.Distance = rd['DISTANCE']

                lapWaypoints.append(wp)

                if "LAP" in rd :
                    #build the lap
                    lap = Lap(stats = activity.Stats, startTime = startTimeLap, endTime = formatedDate) 
                    lap.Waypoints = lapWaypoints
                    activity.Laps.append(lap)
                    # re init a new lap
                    startTimeLap = formatedDate
                    lapWaypoints = []

            #build last lap
            if len(lapWaypoints)>0 :
                lap = Lap(stats = activity.Stats, startTime = startTimeLap, endTime = formatedDate) 
                lap.Waypoints = lapWaypoints
                activity.Laps.append(lap)
  
        return activity

    
    def UploadActivity(self, svcRecord, activity):
        logging.info("UPLOAD To Decathlon Activity tz " + str(activity.TZ) + " dt tz " + str(activity.StartTime.tzinfo) + " starttime " + str(activity.StartTime))
        
        #JSON build
        root = {}

        root["name"] = activity.Name
        root["startdate"] = str(activity.StartTime).replace(" ","T") 
        duration = int((activity.EndTime - activity.StartTime).total_seconds())
        root["duration"] = duration
        
        root["sport"] = "/v2/sports/" + self._activityTypeMappings[activity.Type]
        
        root["user"] = "/v2/users/" + str(svcRecord.ExternalID)
        
        root["manual"] = True
        root["connector"] = "/v2/connectors/" + "901" #hub Connector id

        dataSummaries = {}
        
        # duration 
        dataSummaries[self._unitMap["duration"]]= duration

        if activity.Stats.Distance.Value is not None and activity.Stats.Distance.Value > 0 :
            dataSummaries[self._unitMap["distance"]] = int(activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)
        
        if activity.Stats.Energy.Value is not None:
            dataSummaries[self._unitMap["kcal"]] = int(activity.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value)

        if activity.Stats.HR.Average is not None and activity.Stats.HR.Average > 0:
            dataSummaries[self._unitMap["hravg"]] = int(activity.Stats.HR.Average)

        #Speed average, We accept meter/hour
        if activity.Stats.Speed.Average is not None and activity.Stats.Speed.Average > 0 :
            speed_kmh = activity.Stats.Speed.asUnits(ActivityStatisticUnit.KilometersPerHour).Average
            speed_mh = 1000 * speed_kmh
            dataSummaries[self._unitMap["speedaverage"]] = int(speed_mh)


        root["dataSummaries"] = dataSummaries


        dataStream = {}
        
        if len(activity.Laps) > 1 :
            addLap = True
        else :
            addLap = False

        oneMeasureLocation = None
        for lap in activity.Laps:
            for wp in lap.Waypoints:
                if wp.HR is not None or wp.Speed is not None or wp.Distance is not None or wp.Calories is not None:
                    oneMeasureLocation = {}
                    elapsedTime = str(duration - int((activity.EndTime - wp.Timestamp).total_seconds()))
                    if wp.HR is not None:
                        oneMeasureLocation[self._unitMap["hrcurrent"]] = int(wp.HR)
                    if wp.Speed is not None:
                        oneMeasureLocation[self._unitMap["speedcurrent"]] = int(wp.Speed*3600)
                    if wp.Calories is not None:
                        oneMeasureLocation[self._unitMap["kcal"]] = int(wp.Calories)
                    if wp.Distance is not None:
                        oneMeasureLocation[self._unitMap["distance"]] = int(wp.Distance)
                    dataStream[elapsedTime] = oneMeasureLocation
            if addLap and oneMeasureLocation is not None:
                oneMeasureLocation["20"] = 1

        
        
        if len(activity.GetFlatWaypoints()) > 0:
            if activity.GetFlatWaypoints()[0].Location is not None:
                if activity.GetFlatWaypoints()[0].Location.Latitude is not None:
                    locations = {}
                    root["latitude"] = activity.GetFlatWaypoints()[0].Location.Latitude
                    root["longitude"] = activity.GetFlatWaypoints()[0].Location.Longitude
                    root["elevation"] = activity.GetFlatWaypoints()[0].Location.Altitude

                    for wp in activity.GetFlatWaypoints():
                        if wp.Location is None or wp.Location.Latitude is None or wp.Location.Longitude is None:
                            continue  # drop the point
                        oneLocation = {}
                        oneLocation["latitude"] = wp.Location.Latitude
                        oneLocation["longitude"] = wp.Location.Longitude
                        if wp.Location.Altitude is not None:
                            oneLocation["elevation"] = wp.Location.Altitude
                        else:
                            oneLocation["elevation"] = 0 
                        elapsedTime = str(duration - int((activity.EndTime - wp.Timestamp).total_seconds()))
                        locations[elapsedTime] = oneLocation
                    root["locations"] = locations
    
        activityJSON = json.dumps(root)

        headers = self._getAuthHeaders(svcRecord)
        self._rate_limit()
        upload_resp = requests.post(DECATHLON_API_BASE_URL + "/v2/activities", data=activityJSON, headers=headers)

        if upload_resp.status_code != 201:
            raise APIException("Could not upload activity %s %s" % (upload_resp.status_code, upload_resp.text))
        
        upload_id = None    

        try:
            root = json.loads(upload_resp.content.decode('utf-8'))
            upload_id = root["id"]
        except:
            raise APIException("Stream data returned is not JSON")

        return upload_id

    def _rate_limit(self):
        try:
            RateLimit.Limit(self.ID)
        except RateLimitExceededException:
            raise ServiceException("Global rate limit reached", user_exception=UserException(UserExceptionType.RateLimited))

    def DeleteCachedData(self, serviceRecord):
        cachedb.decathlon_cache.delete_many({"Owner": serviceRecord.ExternalID})
        cachedb.decathlon_activity_cache.delete_many({"Owner": serviceRecord.ExternalID})

    
    def DeleteActivity(self, serviceRecord, uploadId):
        headers = self._getAuthHeaders(serviceRecord)
        self._rate_limit()
        del_res = requests.delete(DECATHLON_API_BASE_URL + "/v2/activities/+d" % uploadId, headers=headers)
        del_res.raise_for_status()
