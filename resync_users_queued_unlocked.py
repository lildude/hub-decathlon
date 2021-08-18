from tapiriik.database import db
from datetime import datetime
from datetime import date
from datetime import timedelta

# USE THIS SCRIPT ONLY IF SOME USERS ARE QUEUING BUT THEY HAVE NO MESSAGE IN QUEUE

print("-----[ INITIALIZE RESYNC_USERS ]-----")

print("[Resync_users]--- resync all users")



recent_queued = datetime.now() - timedelta(seconds=3600)

response = db.users.update_one(
    {
        "SynchronizationWorker": {"$exists": False}, "QueuedAt": {"$lt": recent_queued}
    },
    {
        "$set": {
            "NextSynchronization": datetime.utcnow(),
        },
        "$unset": {
            "QueuedAt": True
        }
    }
)
print("[Resync_users]--- Matched users: %d " % response.matched_count)
print("[Resync_users]--- Modified users: %d " % response.modified_count)
print("-----[ ENDING RESYNC_USERS ]-----")