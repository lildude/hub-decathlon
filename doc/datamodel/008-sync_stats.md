# Sync stats.py

## Summary
One document represent one synchronisation stat for one activity.
It is related to one couple (worker + host).

## Relations 
* `sync_stats.ActivityID` 1 <-> 1 `activity_records.Activities.UIDS`
* `sync_stats.ActivityID` 1 <-> N `connections.SynchronizedActivities`

## Data model : 
```JSON
{ 
    "_id" : ObjectId("xxxxxx"), 
    "ActivityID" : "xxxxxx", 
    "DestinationServices" : [
        "[SERVICE NAME]"
    ], 
    "Distance" : NumberInt(xxxx), 
    "SourceServices" : [
        "[SERVICE NAME]"
    ], 
    "Timestamp" : ISODate("YYYY-MM-DDTHH:mm:ssZ")
}

```

# [Back to datamodel summary](000-datamodel-summary.md)


