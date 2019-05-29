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

from lxml import etree
import xml.etree.ElementTree as xml
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
        ActivityType.Rowing: "263",
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
        "398" : ActivityType.Other,#rower machine
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

    def _apiHeaders(self, serviceRecord):
        return {"Authorization": "access_token " + serviceRecord.Authorization["OAuthToken"]}

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

        # # register the webhook to receive callbacks for new activities
        jwt = id_resp.json()["requestKey"]
        headers = {"Authorization": "Bearer %s" % jwt, 'User-Agent': 'Python Tapiriik Hub' , 'X-Api-Key': DECATHLON_API_KEY, 'Content-Type': 'application/json'}
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
        return {"Authorization": "Bearer %s" % requestKey, 'User-Agent': 'Python Tapiriik Hub' , 'X-Api-Key':DECATHLON_API_KEY}

    def _parseDate(self, date):
        #model '2017-12-01T12:00:00+00:00'
        return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+%Z").replace(tzinfo=pytz.utc)

    def DownloadActivityList(self, svcRecord, exhaustive=False):
        activities = []
        exclusions = []

        now = datetime.now()
        prev = now - timedelta(6*365/12)

        period = []
        
        aperiod = "%s%02d-%s%02d" % (prev.year, prev.month, now.year, now.month)
        period.append(aperiod)
        
        if exhaustive:
            for _ in range(20):
                now = prev
                prev = now - timedelta(6*365/12)
                aperiod = "%s%02d-%s%02d" % (prev.year, prev.month, now.year, now.month)
                period.append(aperiod)
        
        for dateInterval in period:
            headers = self._getAuthHeaders(svcRecord)
            resp = requests.get(DECATHLON_API_BASE_URL + "/users/" + str(svcRecord.ExternalID) + "/activities.xml?date=" + dateInterval, headers=headers)
            if resp.status_code == 400:
                logging.info(resp.content)
                raise APIException("No authorization to retrieve activity list", block = True, user_exception = UserException(UserExceptionType.Authorization, intervention_required = True))
            if resp.status_code == 401:
                logging.info(resp.content)
                raise APIException("No authorization to retrieve activity list", block = True, user_exception = UserException(UserExceptionType.Authorization, intervention_required = True))
            if resp.status_code == 403:
                logging.info(resp.content)
                raise APIException("No authorization to retrieve activity list", block = True, user_exception = UserException(UserExceptionType.Authorization, intervention_required = True))

            root = xml.fromstring(resp.content)
      
            logging.info("\t\t nb activity : " + str(len(root.findall('.//ID'))))
            for ride in root.iter('ACTIVITY'):
    
                activity = UploadedActivity()
                activity.TZ = pytz.timezone("UTC")  

                startdate = ride.find('.//STARTDATE').text + ride.find('.//TIMEZONE').text
                datebase = parse(startdate)

                activity.StartTime = datebase#pytz.utc.localize(datebase)
                
                activity.ServiceData = {"ActivityID": ride.find('ID').text, "Manual": ride.find('MANUAL').text}
                
                logging.info("\t\t Decathlon Activity ID : " + ride.find('ID').text)
    
    
                if ride.find('SPORTID').text not in self._reverseActivityTypeMappings:
                    exclusions.append(APIExcludeActivity("Unsupported activity type %s" % ride.find('SPORTID').text, activity_id=ride.find('ID').text, user_exception=UserException(UserExceptionType.Other)))
                    logging.info("\t\tDecathlon Unknown activity, sport id " + ride.find('SPORTID').text+" is not mapped")
                    continue
    
                activity.Type = self._reverseActivityTypeMappings[ride.find('SPORTID').text]
    
                for val in ride.iter('VALUE'):
                    if val.get('id') == self._unitMap["duration"]:
                        activity.EndTime = activity.StartTime + timedelta(0, int(val.text))
                    if val.get('id') ==  self._unitMap["distance"]:
                        activity.Stats.Distance = ActivityStatistic(ActivityStatisticUnit.Meters, value=int(val.text))
                    if val.get('id') ==  self._unitMap["kcal"]:
                        activity.Stats.Energy = ActivityStatistic(ActivityStatisticUnit.Kilocalories, value=int(val.text))
                    if val.get('id') ==  self._unitMap["hravg"]:
                        activity.Stats.HR.Average = int(val.text)
                    if val.get('id') ==  self._unitMap["speedaverage"]:
                        meterperhour = int(val.text)
                        meterpersecond = meterperhour/3600
                        activity.Stats.Speed = ActivityStatistic(ActivityStatisticUnit.MetersPerSecond, avg=meterpersecond, max= None)
    
                if ride.find('LIBELLE').text == "" or ride.find('LIBELLE').text is None:
                    txtdate = startdate.split(' ')
                    activity.Name = "Sport Decathlon " + txtdate[0]
                else:
                    activity.Name = ride.find('LIBELLE').text
                
                activity.Private = False
                if ride.find('MANUAL').text == "1" :
                    activity.Stationary = True
                else :
                    activity.Stationary = False
                activity.GPS = ride.find('ABOUT').find('TRACK').text
                activity.AdjustTZ()
                activity.CalculateUID()
                activities.append(activity)

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
        resp = requests.get(DECATHLON_API_BASE_URL + "/activity/" + activityID + "/fullactivity.xml", headers=headers)

        if resp.status_code == 401:
            raise APIException("No authorization to download activity", block = True, user_exception = UserException(UserExceptionType.Authorization, intervention_required = True))

        try:
            root = xml.fromstring(resp.content)
        except:
            raise APIException("Stream data returned from Decathlon is not XML")

        activity.GPS = False
        activity.Stationary = True
        #work on date
        startdate = root.find('.//STARTDATE').text
        timezone = root.find('.//TIMEZONE').text
        datebase = parse(startdate+timezone)

        ridedata = {}
        ridedataindex = []

        for pt in root.iter('LOCATION'):
            delta = int(pt.get('elapsed_time'))
            ridedataindex.append(delta)
            ridedata[delta] = {}
            if activityID == 'eu2132ac60d9a40a1d9a' :
                logging.info('========time : '+ str(delta))
                logging.info('========lat : '+ str(float(pt.find('LATITUDE').text[:8])))
            ridedata[delta]['LATITUDE'] = float(pt.find('LATITUDE').text[:8])
            ridedata[delta]['LONGITUDE'] = float(pt.find('LONGITUDE').text[:8])
            ridedata[delta]['ELEVATION'] = int(pt.find('ELEVATION').text[:8])
        
        if len(ridedata)>0 :
            activity.GPS = True
            activity.Stationary = False

        for measure in root.iter('MEASURE'):
            delta = int(measure.get('elapsed_time'))
            if delta not in ridedataindex :
                ridedataindex.append(delta)
                ridedata[delta] = {}

            for measureValue in measure.iter('VALUE'):
                if measureValue.get('id') == "1":
                    ridedata[delta]['HR'] = int(measureValue.text)
                if measureValue.get('id') == "6":
                    ridedata[delta]['SPEED'] = int(measureValue.text)
                if measureValue.get('id') == "5":
                    ridedata[delta]['DISTANCE'] = int(measureValue.text)
                if measureValue.get('id') == "20":
                    ridedata[delta]['LAP'] = int(measureValue.text)

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
                    wp.Speed = rd['SPEED'] / 3600

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
        
        #XML build
        root = etree.Element("ACTIVITY")
        header = etree.SubElement(root, "HEADER")
        etree.SubElement(header, "NAME").text = activity.Name
        etree.SubElement(header, "DATE").text = str(activity.StartTime).replace(" ","T") 
        duration = int((activity.EndTime - activity.StartTime).total_seconds())
        etree.SubElement(header, "DURATION").text =  str(duration)
        
        etree.SubElement(header, "SPORTID").text = self._activityTypeMappings[activity.Type]
        
        etree.SubElement(header, "LDID").text = str(svcRecord.ExternalID)
        etree.SubElement(header, "MANUAL", attrib=None).text = "true"

        summary = etree.SubElement(root,"SUMMARY")
        dataSummaryDuration = etree.SubElement(summary, "VALUE")
        dataSummaryDuration.text = str(int((activity.EndTime - activity.StartTime).total_seconds()))
        dataSummaryDuration.attrib["id"] = self._unitMap["duration"]
    
        if activity.Stats.Distance.Value is not None and activity.Stats.Distance.Value > 0:
            dataSummaryDistance = etree.SubElement(summary, "VALUE")
            dataSummaryDistance.text = str((int(activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value)))
            dataSummaryDistance.attrib["id"] = self._unitMap["distance"]
        
        if activity.Stats.Energy.Value is not None:
            dataSummaryKcal = etree.SubElement(summary, "VALUE")
            dataSummaryKcal.text = str((int(activity.Stats.Energy.asUnits(ActivityStatisticUnit.Kilocalories).Value)))       
            dataSummaryKcal.attrib["id"] = self._unitMap["kcal"]

        if activity.Stats.HR.Average is not None and activity.Stats.HR.Average > 0:
            dataSummaryHR = etree.SubElement(summary, "VALUE")
            dataSummaryHR.text = str(int(activity.Stats.HR.Average))       
            dataSummaryHR.attrib["id"] = self._unitMap["hravg"]

        #Speed average, We accept meter/hour
        if activity.Stats.Speed.Average is not None and activity.Stats.Speed.Average > 0:
            dataSummarySpeedAvg = etree.SubElement(summary, "VALUE")
            speed_kmh = activity.Stats.Speed.asUnits(ActivityStatisticUnit.KilometersPerHour).Average
            speed_mh = 1000 * speed_kmh
            
            dataSummarySpeedAvg.text = str((int(speed_mh)))       
            dataSummarySpeedAvg.attrib["id"] = self._unitMap["speedaverage"]

        datameasure = etree.SubElement(root, "DATA")
        if len(activity.Laps) > 1 :
            addLap = True
        else :
            addLap = False

        oneMeasureLocation = None
        for lap in activity.Laps:
            for wp in lap.Waypoints:
                if wp.HR is not None or wp.Speed is not None or wp.Distance is not None or wp.Calories is not None:
                    oneMeasureLocation = etree.SubElement(datameasure, "MEASURE")
                    oneMeasureLocation.attrib["elapsed_time"] = str(duration - int((activity.EndTime - wp.Timestamp).total_seconds()))
                    if wp.HR is not None:
                        measureHR = etree.SubElement(oneMeasureLocation, "VALUE")
                        measureHR.text = str(int(wp.HR))
                        measureHR.attrib["id"] =  self._unitMap["hrcurrent"]
                    if wp.Speed is not None:
                        measureSpeed = etree.SubElement(oneMeasureLocation, "VALUE")
                        measureSpeed.text = str(int(wp.Speed*3600))
                        measureSpeed.attrib["id"] = self._unitMap["speedcurrent"]
                    if wp.Calories is not None:
                        measureKcaletree = etree.SubElement(oneMeasureLocation, "VALUE")
                        measureKcaletree.text = str(int(wp.Calories))
                        measureKcaletree.attrib["id"] =  self._unitMap["kcal"] 
                    if wp.Distance is not None:
                        measureDistance = etree.SubElement(oneMeasureLocation, "VALUE")
                        measureDistance.text = str(int(wp.Distance))
                        measureDistance.attrib["id"] =  self._unitMap["distance"] 
            if addLap and oneMeasureLocation is not None:
                measureLap = etree.SubElement(oneMeasureLocation, "VALUE")
                measureLap.text = "1"
                measureLap.attrib["id"] =  "20" #add a lap here this elapsed time

        
        
        if len(activity.GetFlatWaypoints()) > 0:
            if activity.GetFlatWaypoints()[0].Location is not None:
                if activity.GetFlatWaypoints()[0].Location.Latitude is not None:
                    track = etree.SubElement(root, "TRACK")
                    tracksummary = etree.SubElement(track, "SUMMARY")
                    etree.SubElement(tracksummary, "LIBELLE").text = ""
                    tracksummarylocation = etree.SubElement(tracksummary, "LOCATION")
                    tracksummarylocation.attrib["elapsed_time"] = "0"
                    etree.SubElement(tracksummarylocation, "LATITUDE").text = str(activity.GetFlatWaypoints()[0].Location.Latitude)[:8]
                    etree.SubElement(tracksummarylocation, "LONGITUDE").text = str(activity.GetFlatWaypoints()[0].Location.Longitude)[:8]
                    etree.SubElement(tracksummarylocation, "ELEVATION").text = "0"
            
                    etree.SubElement(tracksummary, "DISTANCE").text = str(int(activity.Stats.Distance.asUnits(ActivityStatisticUnit.Meters).Value))
                    etree.SubElement(tracksummary, "DURATION").text = str(int((activity.EndTime - activity.StartTime).total_seconds()))
                    etree.SubElement(tracksummary, "SPORTID").text = self._activityTypeMappings[activity.Type]
                    etree.SubElement(tracksummary, "LDID").text = str(svcRecord.ExternalID)

                    for wp in activity.GetFlatWaypoints():
                        if wp.Location is None or wp.Location.Latitude is None or wp.Location.Longitude is None:
                            continue  # drop the point
                        #oneLocation = etree.SubElement(track, "LOCATION")
                        oneLocation = etree.SubElement(track,"LOCATION")
                        oneLocation.attrib["elapsed_time"] = str(duration - int((activity.EndTime - wp.Timestamp).total_seconds()))
                        etree.SubElement(oneLocation, "LATITUDE").text = str(wp.Location.Latitude)[:8]
                        etree.SubElement(oneLocation, "LONGITUDE").text = str(wp.Location.Longitude)[:8]
                        if wp.Location.Altitude is not None:
                            etree.SubElement(oneLocation, "ELEVATION").text = str(int(wp.Location.Altitude))
                        else:
                            etree.SubElement(oneLocation, "ELEVATION").text = "0"
    
        activityXML = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

        headers = self._getAuthHeaders(svcRecord)
        self._rate_limit()
        upload_resp = requests.post(DECATHLON_API_BASE_URL + "/activity/import.xml", data=activityXML, headers=headers)

        if upload_resp.status_code != 200:
            raise APIException("Could not upload activity %s %s" % (upload_resp.status_code, upload_resp.text))
        
        upload_id = None    

        try:
            root = xml.fromstring(upload_resp.content)
            upload_id = root.find('.//ID').text
        except:
            raise APIException("Stream data returned is not XML")

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
        del_res = requests.delete(DECATHLON_API_BASE_URL + "/activity/+d/summary.xml" % uploadId, headers=headers)
        del_res.raise_for_status()
