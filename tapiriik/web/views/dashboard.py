from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from tapiriik.services import Service
from tapiriik.auth import User

@ensure_csrf_cookie
def dashboard(req):
    if req.user == None and req.COOKIES.get("device_support") == "mobile" or req.user == None and "mobile" in req.GET:
        return render(req, "static/onboarding.html")
    else:
        if req.user != None:
            try:
                svc_record = Service.GetServiceRecordByID(next((svc["ID"] for svc in req.user.get("ConnectedServices") if svc.get("Service") == "decathlon"), None))
                sync_errors = svc_record.SyncErrors
                is_std_refresh_token_problem = next((se for se in sync_errors if se["UserException"]["InterventionRequired"] and se["Block"] and se["UserException"]["Type"] == "auth"),False) != False
                if is_std_refresh_token_problem:
                    User.Logout(req)
                    return redirect(svc_record.Service.UserAuthorizationURL)
            except AttributeError as e:
                # If the user as just connected to STD without any synchronisation there is no SyncErrors.
                # So we cath this specific error, if the error is other we re-raise it.
                if str(e) != "'ServiceRecord' object has no attribute 'SyncErrors'":
                    raise e
        return render(req, "dashboard.html")
