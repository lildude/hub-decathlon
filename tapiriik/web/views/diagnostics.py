from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
from django.views.decorators.http import require_POST
from tapiriik.settings import DIAG_AUTH_LOGIN_SECRET, DIAG_AUTH_PASSWORD, SITE_VER
from tapiriik.database import *
from tapiriik.sync import Sync
from tapiriik.auth import TOTP, DiagnosticsUser, User
from tapiriik.services.service import Service
from tapiriik.settings import WITHDRAWN_SERVICES
from tapiriik.services.service_record import ServiceRecord
from bson.objectid import ObjectId
from tapiriik.helper.common_use import *
import hashlib
import json
import urllib.parse
from datetime import datetime, timedelta
import shutil

import os

def diag_requireAuth(view):
    def authWrapper(req, *args, **kwargs):
        if not DiagnosticsUser.IsAuthenticated(req):
            return redirect("diagnostics_login")
        return view(req, *args, **kwargs)
    return authWrapper

@diag_requireAuth
def diag_stats(req):
    import time
    time_begin = time.perf_counter_ns()

    context = {}

    context["userCount"] = db.users.count()
    context["connCount"] = db.connections.count()
    context["userConnectedOnlySTDCount"] = db.users.count({ "$and": [{"ConnectedServices":{"$size" : 1}}, {"ConnectedServices.Service":"decathlon"}]})

    active_services_list = [svc for svc in Service.List() if svc.ID not in WITHDRAWN_SERVICES]

    partners_count_aggregation = db.connections.aggregate([
        {"$group": {"_id":"$Service", "count":{"$sum": 1}}}
    ])
    partner_connections_counts = {counts.get("_id"): counts.get("count") for counts in partners_count_aggregation}


    context["services_stats"] = []
    for active_service in active_services_list:
        context["services_stats"].append({
            "Name": active_service.DisplayName,
            "NbUsers" : partner_connections_counts.get(active_service.ID) if partner_connections_counts.get(active_service.ID) is not None else 0
        })
    
    time_end = time.perf_counter_ns()
    time_delta_ms = (time_end - time_begin) // 1000000
    context["queriesExecutionTime"] = time_delta_ms

    return render(req, "diag/services_diag.html", context)

@diag_requireAuth
def diag_dashboard(req):
    return redirect("diagnostics_queue_dashboard")


@diag_requireAuth
def diag_queue_dashboard(req):
    context = {}
    stats = db.stats.find_one()

    stall_timeout = timedelta(minutes=1)

    # We fetch this twice so the (orphaned) indicators are correct even if there were writes during all these other queries
    context["allWorkerPIDsPre"] = [x["Process"] for x in db.sync_workers.find()]

    context["lockedSyncUsers"] = list(db.users.find({"SynchronizationWorker": {"$ne": None}}))
    context["lockedSyncRecords"] = len(context["lockedSyncUsers"])
    context["queuedUnlockedUsers"] = list(db.users.find({"SynchronizationWorker": {"$exists": False}, "QueuedAt": {"$ne": None}}))

    context["userCt"] = db.users.count()
    context["scheduledCt"] = db.users.find({"$or":[{"NextSynchronization": {"$ne": None, "$exists": True}}, {"QueuedAt": {"$ne": None, "$exists": True}}]}).count()
    context["autosyncCt"] = db.users.find(User.PaidUserMongoQuery()).count()

    context["errorUsersCt"] = db.users.find({"NonblockingSyncErrorCount": {"$gt": 0}}).count()
    context["exclusionUsers"] = db.users.find({"SyncExclusionCount": {"$gt": 0}}).count()

    context["allWorkers"] = list(db.sync_workers.find())

    synchronizingUserIds = [x["User"] if "User" in x else None for x in context["allWorkers"]]
    context["duplicatedUserSynchronizations"] = set([x for x in synchronizingUserIds if synchronizingUserIds.count(x) > 1])

    context["hostWorkerCount"] = {host:len([1 for x in context["allWorkers"] if x["Host"] == host]) for host in set([x["Host"] for x in context["allWorkers"]])}

    # Each worker can be engaged for <= 60*60 seconds in an hour
    if len(context["allWorkers"]) > 0 and stats:
        context["loadFactor"] = stats["TotalSyncTimeUsed"] / (len(context["allWorkers"]) * 60 * 60)
    else:
        context["loadFactor"] = 0

    context["allWorkerPIDs"] = [x["Process"] for x in context["allWorkers"]]
    context["activeWorkers"] = [x for x in context["allWorkers"] if x["Heartbeat"] > datetime.utcnow() - stall_timeout]

    context["workerStates"]= {}
    workerStates = set(x["State"] for x in context["allWorkers"])
    for state in workerStates:
        context["workerStates"][state] = len([x for x in context["allWorkers"] if x["State"] == state])


    context["stalledWorkers"] = [x for x in context["allWorkers"] if x["Heartbeat"] < datetime.utcnow() - stall_timeout]
    context["stalledWorkerPIDs"] = [x["Process"] for x in context["stalledWorkers"]]

    delta = False
    if "deleteStalledWorker" in req.POST:
        db.sync_workers.delete_many({"Process": int(req.POST["pid"])})
        delta = True
    if "unlockOrphaned" in req.POST:
        orphanedUserIDs = [x["_id"] for x in context["lockedSyncUsers"] if x["SynchronizationWorker"] not in context["allWorkerPIDs"]]
        db.users.update_many({"_id":{"$in":orphanedUserIDs}}, {"$unset": {"SynchronizationWorker": None}})
        delta = True
    if "requeueQueued" in req.POST:
        db.users.update_many({"QueuedAt": {"$lt": datetime.utcnow()}, "$or": [{"SynchronizationWorker": {"$exists": False}}, {"SynchronizationWorker": None}]}, {"$set": {"NextSynchronization": datetime.utcnow(), "QueuedGeneration": "manual"}, "$unset": {"QueuedAt": True}})

    if delta:
        return redirect("diagnostics_queue_dashboard")

    return render(req, "diag/dashboard.html", context)

@diag_requireAuth
def server_status(req):

    context = {}
    # Add REDIS ping info
    redis_response = redis.ping()
    context['redis_status'] = redis_response


    # Add db connection info
    context['db'] = {
        'tapiriik': False,
        'tapiriik_cache': False,
        'tapiriik_tz': False,
        'tapiriik_ratelimit': False
    }
    if db:
        context['db']['tapiriik'] = True
    if cachedb:
        context['db']['tapiriik_cache'] = True
    if tzdb:
        context['db']['tapiriik_tz'] = True
    if ratelimit:
        context['db']['tapiriik_ratelimit'] = True

    # Add disk space info
    disk_info = shutil.disk_usage("/")
    disk = {}
    disk['total'] = readable_byte(disk_info.total)
    disk['used'] = readable_byte(disk_info.used)
    disk['free'] = readable_byte(disk_info.free)

    context['disk'] = disk

    return render(req, "server_status.html", context)


def server_status_elb(req):
    return HttpResponse(status=200)


def server_securitytxt(request):
    lines = [
        "# We strongly appreciate exchange about security for the users",
        "Contact: mailto:infra@decathloncoach.com",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

@diag_requireAuth
def diag_errors(req):
    context = {}
    syncErrorListing = list(db.common_sync_errors.find({"value.count": {"$gt": 5}}, {"value.exemplar": 1, "value.count": 1, "value.recency_avg": 1, "_id.service": 1}))
    syncErrorSummary = []
    for error in sorted(syncErrorListing, key=lambda error: error["value"]["count"], reverse=True):
        syncErrorSummary.append({"id": urllib.parse.quote(json.dumps(error["_id"])), "service": error["_id"]["service"], "message": error["value"]["exemplar"], "count": int(error["value"]["count"]), "average_age": error["value"].get("recency_avg", 0)})

    context["syncErrorSummary"] = syncErrorSummary

    return render(req, "diag/errors.html", context)

@diag_requireAuth
def diag_error(req, error):
    error = db.common_sync_errors.find_one({"_id": json.loads(urllib.parse.unquote(error))})
    if not error:
        return render(req, "diag/error_error_not_found.html")
    affected_service_ids = error["value"]["connections"]
    affected_user_ids = [x["_id"] for x in db.users.find({"ConnectedServices.ID": {"$in": affected_service_ids}}, {"_id":1})]

    return render(req, "diag/error.html", {"error": error, "affected_user_ids": affected_user_ids})


@diag_requireAuth
def diag_graphs(req):
    context = {}
    stats_series = list(db.sync_status_stats.find().sort("$natural", -1).limit(24 * 6)) # Last 24 hours (assuming 10 min intervals, monotonic timestamps)
    for item in stats_series:
        item["Timestamp"] = item["Timestamp"].strftime("%H:%M")
        del item["_id"]
    context["dataSeriesJSON"] = json.dumps(stats_series)
    return render(req, "diag/graphs.html", context)

@diag_requireAuth
def diag_user_lookup(req):
    # identity the user by its LDID (decathlon ID)
    if "ldid" in req.POST:
        ldid = req.POST["ldid"]
        connection = db.connections.find_one({ "ExternalID": {"$eq": ldid}, "Service":{"$eq":"decathlon"}})
        if connection is not None:
            user = db.users.find_one({ "ConnectedServices.ID": connection["_id"]})
            if user is not None:
                user_id = user["_id"]
                return redirect("diagnostics_user", user=user_id)
    return redirect("diagnostics_dashboard")

@diag_requireAuth
def diag_user(req, user):
    try:
        userRec = db.users.find_one({"_id": ObjectId(user)})
    except:
        userRec = None
    if not userRec:
        searchOpts = [{"Payments.Txn": user}, {"Payments.Email": user}]
        try:
            searchOpts.append({"AncestorAccounts": ObjectId(user)})
            searchOpts.append({"ConnectedServices.ID": ObjectId(user)})
        except:
            pass # Invalid format for ObjectId
        userRec = db.users.find_one({"$or": searchOpts})
        if not userRec:
            searchOpts = [{"ExternalID": user}]
            try:
                searchOpts.append({"ExternalID": int(user)})
            except:
                pass # Not an int
            svcRec = db.connections.find_one({"$or": searchOpts})
            if svcRec:
                userRec = db.users.find_one({"ConnectedServices.ID": svcRec["_id"]})
        if userRec:
            return redirect("diagnostics_user", user=userRec["_id"])
    if not userRec:
        return render(req, "diag/error_user_not_found.html")
    delta = True # Easier to set this to false in the one no-change case.
    if "sync" in req.POST:
        _sync = Sync()
        _sync.ScheduleImmediateSync(userRec, req.POST["sync"] == "Full")
    elif "unlock" in req.POST:
        db.users.update_one({"_id": ObjectId(user)}, {"$unset": {"SynchronizationWorker": None}})
    elif "lock" in req.POST:
        db.users.update_one({"_id": ObjectId(user)}, {"$set": {"SynchronizationWorker": 1}})
    elif "requeue" in req.POST:
        db.users.update_one({"_id": ObjectId(user)}, {"$unset": {"QueuedAt": None}})
    elif "hostrestrict" in req.POST:
        host = req.POST["host"]
        if host:
            db.users.update_one({"_id": ObjectId(user)}, {"$set": {"SynchronizationHostRestriction": host}})
        else:
            db.users.update_one({"_id": ObjectId(user)}, {"$unset": {"SynchronizationHostRestriction": None}})
    elif "substitute" in req.POST:
        req.session["substituteUserid"] = user
        return redirect("dashboard")
    elif "svc_setauth" in req.POST and len(req.POST["authdetails"]):
        db.connections.update_one({"_id": ObjectId(req.POST["id"])}, {"$set":{"Authorization": json.loads(req.POST["authdetails"])}})
    elif "svc_setconfig" in req.POST and len(req.POST["config"]):
        db.connections.update_one({"_id": ObjectId(req.POST["id"])}, {"$set":{"Config": json.loads(req.POST["config"])}})
    elif "svc_unlink" in req.POST:
        from tapiriik.services import Service
        from tapiriik.auth import User
        svcRec = Service.GetServiceRecordByID(req.POST["id"])
        try:
            Service.DeleteServiceRecord(svcRec)
        except:
            pass
        try:
            User.DisconnectService(svcRec)
        except:
            pass
    elif "svc_marksync" in req.POST:
        db.connections.update_one(
            {"_id": ObjectId(req.POST["id"])},
            {"$addToSet": {"SynchronizedActivities": req.POST["uid"]}}
        )
    elif "svc_clearexc" in req.POST:
        db.connections.update_one({"_id": ObjectId(req.POST["id"])}, {"$unset": {"ExcludedActivities": 1}})
    elif "svc_clearacts" in req.POST:
        db.connections.update_one({"_id": ObjectId(req.POST["id"])}, {"$unset": {"SynchronizedActivities": 1}})
        _sync = Sync()
        _sync.SetNextSyncIsExhaustive(userRec, True)
    elif "svc_toggle_poll_sub" in req.POST:
        from tapiriik.services import Service
        svcRec = Service.GetServiceRecordByID(req.POST["id"])
        svcRec.SetPartialSyncTriggerSubscriptionState(not svcRec.PartialSyncTriggerSubscribed)
    elif "svc_toggle_poll_trigger" in req.POST:
        from tapiriik.services import Service
        svcRec = Service.GetServiceRecordByID(req.POST["id"])
        db.connections.update_one({"_id": ObjectId(req.POST["id"])}, {"$set": {"TriggerPartialSync": not svcRec.TriggerPartialSync}})
    elif "svc_tryagain" in req.POST:
        from tapiriik.services import Service
        svcRec = Service.GetServiceRecordByID(req.POST["id"])
        db.connections.update_one({"_id": ObjectId(req.POST["id"])}, {"$pull": {"SyncErrors": {"Scope": "activity"}}})
        act_recs = db.activity_records.find_one({"UserID": ObjectId(user)})
        for act in act_recs["Activities"]:
            if "FailureCounts" in act and svcRec.Service.ID in act["FailureCounts"]:
                del act["FailureCounts"][svcRec.Service.ID]
        db.activity_records.save(act_recs)
    else:
        delta = False

    if delta:
        return redirect("diagnostics_user", user=user)
    return render(req, "diag/user.html", {"diag_user": userRec})


@diag_requireAuth
def diag_connection(req):
    return render(req, "diag/connection.html")


@require_POST
@diag_requireAuth
def diag_api_search_connection(req):
    body = json.loads(req.body.decode("utf-8"))
    result = []
    response = None

    if "partnerId" in body:
        partner_id_param_str = str(body.get("partnerId"))
        if partner_id_param_str.isdigit():
            partner_id_param_int = int(body.get("partnerId"))
            result = list(db.connections.find({"ExternalID": partner_id_param_int}))
            if len(result) == 0:
                result = list(db.connections.find({"ExternalID": partner_id_param_str}))

        else:
            result = list(db.connections.find({"ExternalID": partner_id_param_str}))

        connections = {
            "connections": result
        }

    else:
        return HttpResponseBadRequest("You must provide a 'partnerId'")

    response = json.loads(json.dumps(connections, default=str))

    return JsonResponse(response)

@diag_requireAuth
def diag_api_connection_by_id(req, connection_id):

    if not ObjectId.is_valid(connection_id):
        return HttpResponseBadRequest("The provided connectionId doesn't respect the format specification (24-character hex string)")
        
    connection = db.connections.find_one({"_id": ObjectId(connection_id)})

    if connection is None:
        return HttpResponseNotFound("Connection with id %s not found" % connection_id)
    
    response = json.loads(json.dumps(connection, default=str))

    return JsonResponse(response)

@diag_requireAuth
def diag_user_activities(req, user):
    return render(req, "diag/user_activities.html", {"uid": user})

@require_POST
@diag_requireAuth
def diag_api_user_activities(req):
    body = json.loads(req.body.decode("utf-8"))
    begin_filter_date = datetime.strptime(body.get("beginFilterDate"), "%m/%d/%Y")
    end_filter_date = datetime.strptime(body.get("endFilterDate"), "%m/%d/%Y")

    user_activity_record = db.activity_records.find_one({"UserID": ObjectId(body.get("user"))}, {"_id":0, "Activities":1})
    user_activities = [
            {
                "Name": act.get("Name"),
                "StartTime": act.get("StartTime"),
                "EndTime": act.get("EndTime"),
                "SportType": act.get("Type"),
                "Prescence": act.get("Prescence",{}),
                "Abscence": act.get("Abscence",{})
            } for act in user_activity_record.get("Activities")
        ]
    
    activities_filtered_by_date = {
        "Activities": [act for act in user_activities if begin_filter_date <= act.get("StartTime") and act.get("StartTime") <= end_filter_date]
    }
    
    return JsonResponse(json.loads(json.dumps(activities_filtered_by_date, default=str)))

@diag_requireAuth
def diag_unsu(req):
    if "substituteUserid" in req.session:
        user = req.session["substituteUserid"]
        del req.session["substituteUserid"]
        return redirect("diagnostics_user", user=user)
    else:
        return redirect("dashboard")

@diag_requireAuth
def diag_payments(req):
    payments = list(db.payments.find())
    for payment in payments:
        payment["Accounts"] = [x["_id"] for x in db.users.find({"Payments.Txn": payment["Txn"]}, {"_id":1})]
    return render(req, "diag/payments.html", {"payments": payments})

@diag_requireAuth
def diag_ip(req):
    from ipware.ip import get_real_ip
    return HttpResponse(get_real_ip(req))

def diag_login(req):
    if "password" in req.POST:
        if hashlib.sha512(req.POST["password"].encode("utf-8")).hexdigest().upper() == DIAG_AUTH_PASSWORD and (DIAG_AUTH_LOGIN_SECRET) == str(req.POST["login"]):
            DiagnosticsUser.Authorize(req)
            return redirect("diagnostics_dashboard")
    return render(req, "diag/login.html")
