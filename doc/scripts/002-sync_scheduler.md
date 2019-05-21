# sync_scheduler.py

This script is getting user list. These users have to be sync. For every user, a new message is set in queue.
This script is in permanent execution, that is to say, it won't stop running until there is no crash, nor any human intervention to stop it.
It uses tapiriif, pymongo and kombu modules.

### Script flow : 
- Define new global vars for sync and new queue message reader
```
Sync.InitializeWorkerBindings()
```
- Define new kombu producer. This one allow to set a new message in queue
```
producer = kombu.Producer(Sync._channel, Sync._exchange)
```
- Define a user liste who has to be sync
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
- Update users list with "queued" status
```
"$set": {"QueuedAt": queueing_at, "QueuedGeneration": generation}, "$unset": {"NextSynchronization": True}
```
- For every item in list, write a message into queue

# [Back to script summary](000-script-summary.md)

