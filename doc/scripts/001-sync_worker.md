# sync_worker.py

This script is call every times we need to sync something.
It uses Tapiriif and Pymongo modules.

### Script flow : 
- Define new "sub-process"
- Get sync_worker document by ID and Host infos (1), then update it (2) 
```
(1)
"Process": os.getpid(),
"Host": socket.gethostname()

(2)
"$set": {
    "Process": os.getpid(),
    "Host": socket.gethostname(),
    "Heartbeat": datetime.utcnow(),
    "Startup":  datetime.utcnow(),
    "Version": WorkerVersion,
    "Index": settings.WORKER_INDEX,
    "State": "startup"
}
```
- Define global vars for synchronization and set reader for queue
```
Sync.InitializeWorkerBindings()
```
- Launch sync process (1) and update "heartbeat" of current sync_worker execution (2)
```
(1)
Sync.PerformGlobalSync(heartbeat_callback=sync_heartbeat, version=WorkerVersion, max_users=RecycleInterval)

(2)
def sync_heartbeat(state, user=None):
    db.sync_workers.update({"_id": heartbeat_rec_id}, {"$set": {"Heartbeat": datetime.utcnow(), "State": state, "User": user}})
```


# [Back to script summary](000-script-summary.md)


