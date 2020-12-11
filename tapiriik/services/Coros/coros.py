# Synchronization module for COROS
# Imports are based on the polarflow ones they will be afinated later
from tapiriik.settings import WEB_ROOT, COROS_CLIENT_SECRET, COROS_CLIENT_ID, COROS_API_BASE_URL, _GLOBAL_LOGGER, COLOG
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.api import APIException, UserException, UserExceptionType
# from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit
# from tapiriik.services.tcx import TCXIO
from tapiriik.database import db

# from datetime import datetime, timedelta
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
        params = {"grant_type": "authorization_code", "code": code, "client_id": COROS_CLIENT_ID, "client_secret": COROS_CLIENT_SECRET, "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "coros"})}

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
                "AccessToken": serviceRecord.Authorization.get("RefreshToken"),
                "AccessTokenExpiresAt": time.time()+2592000, # Adding 30 days in sec as specified in the coros API doc
                "RefreshToken": serviceRecord.Authorization.get("RefreshToken")
            }

        serviceRecord.Authorization.update(authorizationData)
        db.connections.update({"_id": serviceRecord._id}, {"$set": {"Authorization": authorizationData}})
