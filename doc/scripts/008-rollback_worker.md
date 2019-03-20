# rollback_worker.py

This script define some rollback function using Celery.

## Class statement :
### _celeryConfig:
```python
class _celeryConfig:
    CELERY_ROUTES = {
        "rollback_worker.rollback_task": {"queue": "tapiriik-rollback"}
    }
    CELERYD_CONCURRENCY = 1 # Otherwise the GC rate limiting breaks since file locking is per-process.
    CELERYD_PREFETCH_MULTIPLIER = 1 # The message queue could use some exercise.
``` 
## Function statement :

### celery_shutdown
```
@worker_shutdown.connect
def celery_shutdown(**kwargs):
``` 
#### Function sequence : 
- Close Celery connection

### rollback_task
```
@celery_app.task()
def rollback_task(task_id):
``` 
#### Function sequence : 
- Getting task infos for a specific ID
- Launch task execution

### schedule_rollback_task
```
def schedule_rollback_task(task_id):
``` 
#### Déroulement de la fonction : 
- Launch sync process of scheduled task

# [Back to script summary](000-script-summary.md)

