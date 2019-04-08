# sync_watchdog.py

This script is catching timeout or crashed process.
If process is killed, users touched by this one will be "unlock". This change will perform a new resync worker for these users. 
It uses Tapiriik modules.

### Script flow  :
- Getting all sync_workers documents in DB
```
for worker in db.sync_workers.find({"Host": host}):
```
- For each sync_worker, try to kill the associated process
```
os.kill(worker["Process"], 0)
```
- If process is still running, check if it's in timeout statement
- If it's in timeout statement, kill it
```
os.kill(worker["Process"], signal.SIGKILL)
```
- Remove timeout process from sync_worker collection in DB
- Unlock users attached to the kill process
```
db.users.update({"SynchronizationWorker": worker["Process"], "SynchronizationHost": host}, {"$unset":{"SynchronizationWorker": True}}, multi=True)
```
- Insert / update  a sync_watchdog row in DB with datetime() and host info
```
db.sync_watchdogs.update({"Host": host}, {"Host": host, "Timestamp": datetime.utcnow()}, upsert=True)
```

# [Back to script summary](000-script-summary.md)

