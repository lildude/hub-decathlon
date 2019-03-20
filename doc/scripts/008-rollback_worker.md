# rollback_worker.py

Ce script a pour but de limiter le nombre de CPU utilisé par les différents process de synchronisation
Ce script est en exécution permanente, c'est à dire qu'il ne s'arrêtera pas de tourner tant qu'il n'y aura pas de plantage, ni d'intervention humaine pour l'arrêter.
Il utilise les modules tapiriik, pymongo et kombu.

## Déclaration de classe :
### _celeryConfig:
```python
class _celeryConfig:
    CELERY_ROUTES = {
        "rollback_worker.rollback_task": {"queue": "tapiriik-rollback"}
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

### rollback_task
```
@celery_app.task()
def rollback_task(task_id):
``` 
#### Déroulement de la fonction : 
- Récupère le détail d'une tâche pour un ID donné
- Lance l'exécution de la tâche

### schedule_rollback_task
```
def schedule_rollback_task(task_id):
``` 
#### Déroulement de la fonction : 
- Lance le process de synchronisation d'une tâche donnée en mode "scheduler"

# [Back to script summary](000-script-summary.md)

