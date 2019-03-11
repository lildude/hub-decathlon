# sync_remote_trigger.py

Ce script a pour but d'être appelé à chaque besoin de synchronisation. Il utilise les modules Tapiriik et Celery (pour RabbitMQ).

##Déclaration de classe :
### _celeryConfig:
```python
class _celeryConfig:
    CELERY_ROUTES = {
        "sync_remote_triggers.trigger_remote": {"queue": "tapiriik-remote-trigger"}
    }
    CELERYD_CONCURRENCY = 1 # Otherwise the GC rate limiting breaks since file locking is per-process.
    CELERYD_PREFETCH_MULTIPLIER = 1 # The message queue could use some exercise.
``` 
## Fonctions disponibles dans le script :

### celery_shutdown
```
@worker_shutdown.connect
def celery_shutdown(**kwargs):
``` 
#### Déroulement de la fonction : 
- Ferme la connexion Celery

### trigger_remote
```
@celery_app.task(acks_late=True)
def trigger_remote(service_id, affected_connection_external_ids):
``` 
#### Déroulement de la fonction: 
- Récupère le service dont l'ID est passé en parammètre
- Met à jour la liste des connections liées à ce service et dont les ExternalID  sont inclus dans la liste fournit en paramètre, pour déclencher une synchronisation partielle
- Récupère la liste des IDs concernés par la modification
- Mise à jour des users n'ayant pas terminé leurs abonnements et étant toujours en "auto-synchronisation" pour leur définir une nouvelle date de NextSynchronisation

# [Back to script summary](000-script-summary.md)
