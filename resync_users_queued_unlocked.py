from os import wait
from tapiriik.database import db
from datetime import datetime
from datetime import date
from datetime import timedelta
import time


# USE THIS SCRIPT ONLY IF SOME USERS ARE QUEUING BUT THEY HAVE NO MESSAGE IN QUEUE

print("-----[ INITIALIZE RESYNC_USERS ]-----")

print("[Resync_users]--- resync all users")

ACTIVE_WAIT_TIME = 15
STANDBY_WAIT_TIME = 300

wait_time = 15

while True :

    recent_queued = datetime.now() - timedelta(seconds=1800)

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

    if response.matched_count > 0 :
        wait_time = ACTIVE_WAIT_TIME
    else :
        wait_time = STANDBY_WAIT_TIME

    time.sleep(wait_time)
