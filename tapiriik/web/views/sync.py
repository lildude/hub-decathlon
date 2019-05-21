import json
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from tapiriik.auth import User
from tapiriik.sync import Sync, SynchronizationTask
from tapiriik.database import db
from tapiriik.services import Service
from tapiriik.settings import MONGO_FULL_WRITE_CONCERN
from datetime import datetime
import zlib


def sync_status(req):
    if not req.user:
        return HttpResponse(status=403)

    stats = db.stats.find_one()
    syncHash = 1  # Just used to refresh the dashboard page, until I get on the Angular bandwagon.
    conns = User.GetConnectionRecordsByUser(req.user)

    def svc_id(svc):
        return svc.Service.ID

    def err_msg(err):
        return err["Message"]

    for conn in sorted(conns, key=svc_id):
        syncHash = zlib.adler32(bytes(conn.HasExtendedAuthorizationDetails()), syncHash)
        if not hasattr(conn, "SyncErrors"):
            continue
        for err in sorted(conn.SyncErrors, key=err_msg):
            syncHash = zlib.adler32(bytes(err_msg(err), "UTF-8"), syncHash)

    # Flatten NextSynchronization with QueuedAt
    pendingSyncTime = req.user["NextSynchronization"] if "NextSynchronization" in req.user else None
    if "QueuedAt" in req.user and req.user["QueuedAt"]:
        pendingSyncTime = req.user["QueuedAt"]

    sync_status_dict = {"NextSync": (pendingSyncTime.ctime() + " UTC") if pendingSyncTime else None,
                        "LastSync": (req.user["LastSynchronization"].ctime() + " UTC") if "LastSynchronization" in req.user and req.user["LastSynchronization"] is not None else None,
                        "Synchronizing": "SynchronizationWorker" in req.user,
                        "SynchronizationProgress": req.user["SynchronizationProgress"] if "SynchronizationProgress" in req.user else None,
                        "SynchronizationStep": req.user["SynchronizationStep"] if "SynchronizationStep" in req.user else None,
                        "SynchronizationWaitTime": None, # I wish.
                        "Hash": syncHash}

    if stats and "QueueHeadTime" in stats:
        sync_status_dict["SynchronizationWaitTime"] = (stats["QueueHeadTime"] - (datetime.utcnow() - req.user["NextSynchronization"]).total_seconds()) if "NextSynchronization" in req.user and req.user["NextSynchronization"] is not None else None

    return HttpResponse(json.dumps(sync_status_dict), content_type="application/json")

def sync_recent_activity(req):
    if not req.user:
        return HttpResponse(status=403)
    _synchronization_task = SynchronizationTask(req.user)
    res = _synchronization_task.RecentSyncActivity(req.user)
    return HttpResponse(json.dumps(res), content_type="application/json")

@require_POST
def sync_schedule_immediate(req):
    _sync = Sync()
    if not req.user:
        return HttpResponse(status=401)
    if "LastSynchronization" in req.user and req.user["LastSynchronization"] is not None and datetime.utcnow() - req.user["LastSynchronization"] < _sync.MinimumSyncInterval:
        return HttpResponse(status=403)
    exhaustive = None
    if "LastSynchronization" in req.user and req.user["LastSynchronization"] is not None and datetime.utcnow() - req.user["LastSynchronization"] > _sync.MaximumIntervalBeforeExhaustiveSync:
        exhaustive = True
    _sync.ScheduleImmediateSync(req.user, exhaustive)
    return HttpResponse()

@require_POST
def sync_clear_errorgroup(req, service, group):
    _sync = Sync()
    if not req.user:
        return HttpResponse(status=401)

    rec = User.GetConnectionRecord(req.user, service)
    if not rec:
        return HttpResponse(status=404)

    # Prevent this becoming a vehicle for rapid synchronization
    to_clear_count = 0
    for x in rec.SyncErrors:
        if "UserException" in x and "ClearGroup" in x["UserException"] and x["UserException"]["ClearGroup"] == group:
            to_clear_count += 1

    _sync = Sync()
    if to_clear_count > 0:
            db.connections.update_one({"_id": rec._id}, {"$pull":{"SyncErrors":{"UserException_ClearGroup": group}}})
            db.users.update_one({"_id": req.user["_id"]}, {'$inc':{"BlockingSyncErrorCount":-to_clear_count}}) # In the interests of data integrity, update the summary counts immediately as opposed to waiting for a sync to complete.
            _sync.ScheduleImmediateSync(req.user, True) # And schedule them for an immediate full resynchronization, so the now-unblocked services can be brought up to speed.            return HttpResponse()
            return HttpResponse()

    return HttpResponse(status=404)

@csrf_exempt
def sync_trigger_partial_sync_callback(req, service):
    svc = Service.FromID(service)
    if req.method == "POST":
        # if whe're using decathlon services, force resync
        # Get users ids list, depending of services
        response = svc.ExternalIDsForPartialSyncTrigger(req)

        _sync = Sync()
        # Get users _id list from external ID
        users_to_sync = _sync.getUsersIDFromExternalId(response, service)

        if not users_to_sync:
            return HttpResponse(status=401)
        else:
            for user in users_to_sync:

                # For each users, if we can sync now
                if "LastSynchronization" in user and user["LastSynchronization"] is not None and datetime.utcnow() - \
                        user["LastSynchronization"] < _sync.MinimumSyncInterval:
                    return HttpResponse(status=403)
                exhaustive = None
                if "LastSynchronization" in user and user["LastSynchronization"] is not None and datetime.utcnow() - \
                        user["LastSynchronization"] > _sync.MaximumIntervalBeforeExhaustiveSync:
                    exhaustive = True
                # Force immadiate sync
                _sync.ScheduleImmediateSync(user, exhaustive)

        return HttpResponse(status=204)

    elif req.method == "GET":	
        return svc.PartialSyncTriggerGET(req)
    else:
        return HttpResponse(status=400)
