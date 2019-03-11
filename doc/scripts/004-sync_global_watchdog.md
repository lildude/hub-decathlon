# sync_global_watchdog.py

Ce script a pour but d'être appelé à chaque besoin de synchronisation. Il utilise les modules Tapiriik et Pymongo.

Déroulement du script : 
- Récupération des documents sync_watchdog en DB
- Pour chacun d'entre eux, s'ils sont en timeout (5mn), on ré-initialise la synchronisation des users concernés par les process en timeout.
```
db.users.update({"SynchronizationHost": host_record["Host"]}, {"$unset": {"SynchronizationWorker": True}}, multi=True)
```
- On supprime de la base les sync_workers représentant les process en timeout
- On supprime de la base les sync_watchdog qui sont en timeout 

# [Back to script summary](000-script-summary.md)


