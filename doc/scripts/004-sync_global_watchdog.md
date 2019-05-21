# sync_global_watchdog.py

This scripts aims to be called for each synchronization need.
It uses tapiriik, pymongo and Celery modules.

### Script flow :
- Getting sync_watchdog documents store in DB 
- For each sync_watchdog, if they're in timeout statement (5mn), re-launch users sync touch by the process.
```
db.users.update({"SynchronizationHost": host_record["Host"]}, {"$unset": {"SynchronizationWorker": True}}, multi=True)
```
- Remove "timeout" sync_workers and sync_watchdog of DB  

# [Back to script summary](000-script-summary.md)


