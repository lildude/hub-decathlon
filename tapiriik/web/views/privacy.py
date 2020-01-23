from django.shortcuts import render
from tapiriik.services import Service
from tapiriik.settings import WITHDRAWN_SERVICES, SOFT_LAUNCH_SERVICES
from tapiriik.auth import User
def privacy(request):

    OPTIN = "<span class=\"optin policy\">Opt-in</span>"
    NO = "<span class=\"no policy\">No</span>"
    YES = "<span class=\"yes policy\">Yes</span>"
    CACHED = "<span class=\"cached policy\">Cached</span>"
    SEEBELOW = "See below"

    services = dict([[x.ID, {"DisplayName": x.DisplayName, "ID": x.ID}] for x in Service.List() if x.ID not in WITHDRAWN_SERVICES])

    if "garminconnect" in services :
        services["garminconnect"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    if "strava" in services :
        services["strava"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "sporttracks" in services :
        services["sporttracks"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "dropbox" in services :
        services["dropbox"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":CACHED})
    if "runkeeper" in services :
        services["runkeeper"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "rwgps" in services :
        services["rwgps"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    if "trainingpeaks" in services :
        services["trainingpeaks"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "endomondo" in services :
        services["endomondo"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "motivato" in services :
        services["motivato"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    if "nikeplus" in services :
        services["nikeplus"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    if "velohero" in services :
        services["velohero"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    if "runsense" in services :
        services["runsense"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "trainerroad" in services :
        services["trainerroad"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    if "smashrun" in services :
        services["smashrun"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "beginnertriathlete" in services :
        services["beginnertriathlete"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data": NO})
    if "trainasone" in services :
        services["trainasone"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "pulsstory" in services :
        services["pulsstory"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "setio" in services :
        services["setio"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "singletracker" in services :
        services["singletracker"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "aerobia" in services :
        services["aerobia"].update({"email": OPTIN, "password": OPTIN, "tokens": NO, "metadata": YES, "data":NO})
    if "polarflow" in services :
        services["polarflow"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "decathlon" in services :
        services["decathlon"].update({"email": NO, "password": NO, "tokens": YES, "metadata": YES, "data":NO})
    if "fitbit" in services :
        services["fitbit"].update({"email": NO, "password": NO, "tokens": YES, "metadata": NO, "data":YES})
    if "garminhealth" in services :
        services["garminhealth"].update({"email": NO, "password": NO, "tokens": YES, "metadata": NO, "data":YES})
    if "relive" in services :
        services["relive"].update({"email": NO, "password": NO, "tokens": YES, "metadata": NO, "data":NO})
    #services["polarpersonaltrainer"].update({"email": YES, "password": YES, "tokens": NO, "metadata": YES, "data":NO})

    for svc_id in SOFT_LAUNCH_SERVICES:
        if svc_id in services:
            del services[svc_id]

    services_list = sorted(services.values(), key=lambda service: service["ID"])
    return render(request, "privacy.html", {"services": services_list})
