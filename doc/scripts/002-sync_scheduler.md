# sync_scheduler.py

Ce script a pour but de récupérer la liste des users ayant besoin d'être synchronisé. Un message en queue est publié pour chacun d'entre eux.
Ce script est en exécution permanente, c'est à dire qu'il ne s'arrêtera pas de tourner tant qu'il n'y aura pas de plantage, ni d'intervention humaine pour l'arrêter.
Il utilise les modules tapiriik, pymongo et kombu.

### Déroulement du script : 
- Définition des variables global pour la synchronisation et d'un message en queue
```
Sync.InitializeWorkerBindings()
```
- Définition d'un "producer" kombu. Le producer permet de publier des messages en queue
```
producer = kombu.Producer(Sync._channel, Sync._exchange)
```
- Définition d'une liste de user qui doivent être synchronisés
```
users = list(db.users.with_options(read_preference=ReadPreference.PRIMARY).find(
    {
        "NextSynchronization": {"$lte": datetime.utcnow()},
        "QueuedAt": {"$exists": False}
    },
    {
        "_id": True,
        "SynchronizationHostRestriction": True
    }
))
```
- Mise à jour de cette liste de users avec un status "queued"
```
"$set": {"QueuedAt": queueing_at, "QueuedGeneration": generation}, "$unset": {"NextSynchronization": True}
```
- Pour chacun des membres de cette liste, écriture d'un message en queue

# [Back to script summary](000-script-summary.md)

