from tapiriik.database import db
from datetime import datetime
# USE THIS SCRIPT ONLY IF SOME USERS ARE QUEUING BUT THEY HAVE NO MESSAGE IN QUEUE

print("-----[ INITIALIZE RESYNC_USERS ]-----")

print("[Resync_users]--- resync all users")

response = db.users.update_one(
    {
        "SynchronizationWorker": {"$exists": False}, "QueuedAt": {"$ne": None}
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