from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
import logging

@ensure_csrf_cookie
def dashboard(req):
    if req.user == None and req.COOKIES.get("device_support") == "mobile":
        return render(req, "static/onboarding.html")
    else:
        return render(req, "dashboard.html")
