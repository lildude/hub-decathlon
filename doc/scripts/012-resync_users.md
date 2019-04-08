# resync_users.py

This script reset all pending users. Use this script ONLY if a user(s) are registered with "queued" information in database and if their message in queue are not found / not available.

BE CAREFUL: this script reset ALL queued users. It means ALL users will be resync on same time !

### Script flow : 
- find all users with "QueuedAt" info, unset this attribute and set NextSynchronization with datetime now.

```
response = db.users.update_many(
    {
        "QueuedAt": {"$exists": True}
    },
    {
        "$set": {
            "NextSynchronization": datetime.utcnow(),
        },
        "$unset": {
            "QueuedAt": True
        }
    }
)
```
 
# [Back to script summary](000-script-summary.md)

