# sync_poll_trigger.py

This script manages the auto sync of users having a subscription (Garmin, PolarFlow)
It uses tapiriif and celery modules.

## Functions statement :

### schedule_trigger_poll 
```
def schedule_trigger_poll()
```
#### Function sequence : 
- Getting all trigger_poll_scheduling.
- For every "polling" service.
```
for svc in Service.List():
    if svc.PartialSyncTriggerRequiresPolling:
```
- Check last sync date of this service
- Call sync with Celery by calling trigger_poll
- Then insert / update trigger_poll_scheduling collection, a new row with service ID and index of sync
### trigger_poll
```
@celery_app.task(acks_late=True)
def trigger_poll(service_id, index)
```
#### Function sequence : 
- Getting user list from API
- Update connection of these users.
- Finally, users who own the service and have not completed their subscription, will be updated as "to synchronize" by the worker.
```
"$or": [
    {"Payments.Expiry": {"$gt": datetime.utcnow()}},
    {"Promos.Expiry": {"$gt": datetime.utcnow()}},
    {"Promos.Expiry": {"$type": 10, "$exists": True}} # === null
]seront mis à jour
```
- New row is set into poll_stats collection. It contains date and the number of user touched by the script.

# [Back to script summary](000-script-summary.md)


