# sync_watchdog.py

Ce script a pour but de détecter si un process de synchronisation est en timeout ou crash.
Si le process est kill, les users concernés seront "unlocké" pour être de nouveau synchronisé au prochain run worker.
Il utilise les modules Tapiriik.

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

