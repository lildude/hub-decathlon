# Sync workers.py

## Summary
One document represent one worker task for one user and any sync_worker_stats documents.
It is related to one user and to one couple (worker + host).

## Relations 
* `sync_workers.User` N <-> 1 `users._id`
* `sync_worker_stats.Worker` + `sync_worker_stats.Host` N <-> 1 `sync_workers.Process` + `sync_workers.Host`

## Data model : 
```JSON
{ 
    "_id" : ObjectId("xxxxxxxx"), 
    "Host" : "xxxxxxx", 
    "Process" : NumberInt(xxxx), 
    "Heartbeat" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
    "Index" : NumberInt(0), 
    "Startup" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
    "State" : "ready|list|...", 
    "Version" : BinData(0, "xxxxxxxxx"), 
    "User" : null|ObjectId("xxxx")
}

```

# [Back to datamodel summary](000-datamodel-summary.md)


