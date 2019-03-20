# Users.py

## Summary
Users collection is used to store users data.
On document represent one user. Each user can be related to any connections. It is a "central" user, it means he's supposed to be connected to any user from any service.
It is related to any sync_worker task, any activity_records and any connections

## Relations 
* `users._id` 1 <-> N `sync_workers.User`
* `users._id` 1 <-> N  `activity_records.UserID`
* `users.ConnectedServices.x.ID` 1 <-> 1 `connections._id`

## Data model : 
```JSON
{ 
    "_id" : ObjectId("xxxxxxx"), 
    "Created" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
    "CreationIP" : null, 
    "ConnectedServices" : [
        {
            "Service" : "[SERVICE NAME]", 
            "ID" : ObjectId("xxxxxxx")
        }, 
        {
            "Service" : "[SERVICE NAME]", 
            "ID" : ObjectId("xxxxxxx")
        }
    ], 
    "Timezone" : "Europe/Berlin", 
    "Config" : {
        "suppress_auto_sync" : false, 
        "sync_upload_delay" : NumberInt(0), 
        "sync_skip_before" : null, 
        "historical_sync" : false
    }, 
    "Substitute" : false, 
    "QueuedGeneration" : "[QUEUE GENERATION ID]", 
    "SynchronizationHost" : "[HOST ID]", 
    "SynchronizationStartTime" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
    "SynchronizationProgress" : "[SERVICE NAME]", 
    "SynchronizationStep" : "[STEP]", 
    "BlockingSyncErrorCount" : NumberInt(0), 
    "ForcingExhaustiveSyncErrorCount" : NumberInt(0), 
    "NonblockingSyncErrorCount" : NumberInt(0), 
    "SyncExclusionCount" : NumberInt(0), 
    "LastSynchronization" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
    "LastSynchronizationVersion" : BinData(0, "xxxxxxxxxxxxxxxxx"), 
    "NextSynchronization" : ISODate("YYYY-MM-DDTHH:mm:ssZ")
}
```

# [Back to datamodel summary](000-datamodel-summary.md)


