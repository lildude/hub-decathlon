# sync_poll_trigger.py

Ce script gère la synchronisation automatique des users ayant un abonnement aux services payants (Garmin, PolarFlow).
Il utilise les modules Tapiriik et Celery.

## Fonctions disponibles dans le script :

### schedule_trigger_poll 
```
def schedule_trigger_poll()
```
Déroulement de la fonction : 
- Récupération des trigger_poll_scheduling.
- Pour tous les services ayant besoin d'être "polling"
```
for svc in Service.List():
    if svc.PartialSyncTriggerRequiresPolling:
```
- On vérifie la date de dernière synchronisation du service
- Selon le résultat, on applique une synchronisation avec Celery en appellant la fonction trigger_poll
- Puis on met à jour / ajoute dans la collection trigger_poll_scheduling, une ligne renseignant le service ID et l'index d'exécution de la synchronisation de celui ci

### trigger_poll
```
@celery_app.task(acks_late=True)
def trigger_poll(service_id, index)
```
Déroulement de la fonction : 
- Cette fonction récupère une liste de users via l'API du service concerné.
- Elle met ensuite les connections de ces users à jour.
- Enfin, les users possédant le service et n'ayant pas terminé leurs abonnement, serontmis à jour de sorte à être identifié comme "à synchroniser" par le worker.
```
"$or": [
    {"Payments.Expiry": {"$gt": datetime.utcnow()}},
    {"Promos.Expiry": {"$gt": datetime.utcnow()}},
    {"Promos.Expiry": {"$type": 10, "$exists": True}} # === null
]seront mis à jour
```
- Une ligne est ensuite ajoutée à la collection poll_stats, indiquant la date et le nombre de user touché par le script

# [Back to script summary](000-script-summary.md)


