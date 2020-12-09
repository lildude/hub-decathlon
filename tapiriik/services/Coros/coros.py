# Synchronization module for COROS
# Imports are based on the polarflow ones they will be afinated later
from tapiriik.settings import WEB_ROOT, COROS_CLIENT_SECRET, COROS_CLIENT_ID
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.api import APIException, UserException, UserExceptionType
# from tapiriik.services.interchange import UploadedActivity, ActivityType, ActivityStatistic, ActivityStatisticUnit
# from tapiriik.services.tcx import TCXIO

# from datetime import datetime, timedelta
# from django.core.urlresolvers import reverse
# from urllib.parse import urlencode
# from requests.auth import HTTPBasicAuth
# from io import StringIO

# import uuid
# import gzip
import logging
# import lxml
# import pytz
# import requests
# import isodate
# import json

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

    # Enables extended auth ("Save these details") functionality
    RequiresExtendedAuthorizationDetails = False

    # URL to direct user to when starting authentication
    UserAuthorizationURL = None

    # List of ActivityTypes
    SupportedActivities = None

    # Used only in tests | But to be verified in case of
    SupportsHR = SupportsCalories = SupportsCadence = SupportsTemp = SupportsPower = False

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