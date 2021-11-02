from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from tapiriik.services import Service, ServiceRecord
import logging

@ensure_csrf_cookie
def dashboard(req):
    if req.user == None and req.COOKIES.get("device_support") == "mobile" or req.user == None and "mobile" in req.GET:
        return render(req, "static/onboarding.html")
    else:
        sync_errors = Service.GetServiceRecordByID(next((svc["ID"] for svc in req.user.get("ConnectedServices") if svc.get("Service") == "decathlon"), None)).SyncErrors
        is_std_refresh_token_problem = next((se for se in sync_errors if se["UserException"]["InterventionRequired"] and se["Block"] and se["UserException"]["Type"] == "auth"),False) != False
        logging.info(is_std_refresh_token_problem)
        return render(req, "dashboard.html")
