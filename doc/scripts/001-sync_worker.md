# sync_worker.py

Ce script a pour but d'être appelé à chaque besoin de synchronisation. Il utilise les modules Tapiriik et Pymongo.

Déroulement du script : 
- Déclaration d'un nouveau "sous-process"
- Récupération d'un document sync_workers par son process ID et son host (1), puis mise à jour de celui-ci (2) : 
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
- Définition des variables global pour la synchronisation et déclaration du message en queue
```
Sync.InitializeWorkerBindings()
```
- Lancement de la procédure de synchronisation (1) et mise à jour du "heartbeat" du sync_worker en cours d'exécution (2) 
```
(1)
Sync.PerformGlobalSync(heartbeat_callback=sync_heartbeat, version=WorkerVersion, max_users=RecycleInterval)

(2)
def sync_heartbeat(state, user=None):
    db.sync_workers.update({"_id": heartbeat_rec_id}, {"$set": {"Heartbeat": datetime.utcnow(), "State": state, "User": user}})
```


# [Back to script summary](000-script-summary.md)
## [Back to conception summary](010-conception.md)
```````````````````````````

