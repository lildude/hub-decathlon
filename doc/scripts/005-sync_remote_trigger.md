# sync_remote_trigger.py

This scripts aims to be called for each synchronization need.
It uses tapiriik and Celery modules.

## Class statement :
### _celeryConfig:
```python
class _celeryConfig:
    CELERY_ROUTES = {
        "sync_remote_triggers.trigger_remote": {"queue": "tapiriik-remote-trigger"}
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

### trigger_remote
```
@celery_app.task(acks_late=True)
def trigger_remote(service_id, affected_connection_external_ids):
``` 
#### Function sequence : 
- Getting service from ID (in parameter)
- Update connection list of this service which ExternalID are included in params list, to launch partial sync
- Getting IDs list of updated connections
- Update users who have not completed their subscriptions to flag them as "auto-sync. This flag will allow them to define a new sync date (NextSynchronisation)

# [Back to script summary](000-script-summary.md)
