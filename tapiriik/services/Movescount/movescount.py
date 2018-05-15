# Synchronization module for movescount.com
# (c) 2018 Anton Ashmarin, aashmarin@gmail.com
from tapiriik.settings import WEB_ROOT, MOVESCOUNT_APP_KEY
from tapiriik.services.service_base import ServiceAuthenticationType, ServiceBase
from tapiriik.services.service_record import ServiceRecord
from tapiriik.services.api import APIException, UserException, UserExceptionType

from django.core.urlresolvers import reverse
from urllib.parse import urlencode

import requests

class MovescountService(ServiceBase):
    ID = "movescount"
    DisplayName = "Movescount"
    DisplayAbbreviation = "MC"
    AuthenticationType = ServiceAuthenticationType.OAuth
    AuthenticationNoFrame = True # otherwise looks ugly in the small frame

    def WebInit(self):
        params = {'client_id': MOVESCOUNT_APP_KEY,
                  'redirect_uri': WEB_ROOT + reverse("oauth_return", kwargs={"service": "movescount"})}
        self.UserAuthorizationURL = "https://partner-ui.movescount.com/auth?" + urlencode(params)

    def RetrieveAuthorizationToken(self, req, level):
        params = {'client_id': MOVESCOUNT_APP_KEY,
                  "redirect_uri": WEB_ROOT + reverse("oauth_return", kwargs={"service": "movescount"})}

        #response = requests.post("https://polarremote.com/v2/oauth2/token", data=params, auth=HTTPBasicAuth(POLAR_CLIENT_ID, POLAR_CLIENT_SECRET))
        response = requests.post(self.UserAuthorizationURL)
        data = response.json()

        if response.status_code != 200:
            raise APIException(data["error"])

        authorizationData = {"OAuthToken": data["access_token"]}
        userId = data["x_user_id"]

        try:
            pass#self._register_user(data["access_token"])
        except requests.exceptions.HTTPError as err:
            # Error 409 Conflict means that the user has already been registered for this client.
            # That error can be ignored
            if err.response.status_code != 409:
                raise APIException("Unable to link user", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))

        return (userId, authorizationData)

    def RevokeAuthorization(self, serviceRecord):
        pass#self._delete_user(serviceRecord)