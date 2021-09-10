from django.http.response import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from tapiriik.services import Service
from tapiriik.settings import WITHDRAWN_SERVICES
import logging

@ensure_csrf_cookie
def providers(req):
    if req.user != None:
        user_connections = [conns.get("Service") for conns in req.user.get("ConnectedServices")]
        active_providers = [{"id": x.ID, "displayName": x.DisplayName, "isReceiver": x.ReceivesActivities, "isSupplier": x.ProvidesActivities, "isConnected": True if x.ID in user_connections else False, "authURI": x.UserAuthorizationURL} for x in Service.List() if x.ID not in WITHDRAWN_SERVICES and x.ID != "decathlon"]        
        return JsonResponse({"providers": active_providers})
    else:
        return HttpResponse(content="<h1>Unauthorized</h1>" ,status=403)
