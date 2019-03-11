# sync_watchdog.py

Ce script a pour but de détecter si un process de synchronisation est en timeout ou crash.
Si le process est kill, les users concernés seront "unlocké" pour être de nouveau synchronisé au prochain run worker.
Il utilise les modules Tapiriik.

Déroulement du script :
- Récupère la liste de tous les documents sync_workers en base,
```
for worker in db.sync_workers.find({"Host": host}):
```
- Pour chacun d'entre eux on essaye de kill le process associé
```
os.kill(worker["Process"], 0)
```
- Si le process est toujours en exécution, on vérifie s'il était en timeout ou non
- Si le process est en timeout, on le kill
```
os.kill(worker["Process"], signal.SIGKILL)
```
- On met à jour la DB en supprimant les sync_workers concernés
- On débloque les users attachés au process qui vient d'être kill
```
db.users.update({"SynchronizationWorker": worker["Process"], "SynchronizationHost": host}, {"$unset":{"SynchronizationWorker": True}}, multi=True)
```
- En fin de script, on ajoute / met à jour un sync_watchdog en DB avec la datetime(), pour un host précis.
```
db.sync_watchdogs.update({"Host": host}, {"Host": host, "Timestamp": datetime.utcnow()}, upsert=True)
```

# [Back to script summary](000-script-summary.md)

