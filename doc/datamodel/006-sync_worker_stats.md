# Sync worker stats.py

## Summary
One document represent one worker stat for one sync_worker document.
It is related to one couple (worker + host).

## Relations 
* `sync_worker_stats.Worker` + `sync_worker_stats.Host` N <-> 1 `sync_workers.Process` + `sync_workers.Host`

## Data model : 
```JSON
{ 
    "_id" : ObjectId("xxxxxxxxxx"), 
    "Timestamp" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
    "Worker" : NumberInt(xxxx), 
    "Host" : "xxxxxxx", 
    "TimeTaken" : 0.00
}

```

# [Back to datamodel summary](000-datamodel-summary.md)


