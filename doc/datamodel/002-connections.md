# Connections.py

## Summary
Connections collection is used to store connections data.
One document represent one connection to one service.
Many activities are store under "SynchronizedActivities" and refer to some stats.
It is related to one user, any uploaded_activities and any sync_stats.

## Relations 
* `connections._SynchronizedActivities` N <-> 1 `sync_stats.ActivityID`
* `connections.ExternalID` 1 <-> N `uploaded_activities.UserExternalID`
* `connections._id` 1 <-> 1 `users.ConnectedServices.x.ID`

## Data model : 
```JSON
{ 
    "_id" : ObjectId("xxxxxxx"), 
    "ExternalID" : "xxxxxxx", 
    "Service" : "[SERVICE NAME]", 
    "SynchronizedActivities" : [
        "xxxxxxxx", 
        "yyyyyyyy", 
        "zzzzzzzz"
    ], 
    "Authorization" : {
        "RefreshToken" : "xxxxxxx"
    }, 
    "ExtendedAuthorization" : null, 
    "ExcludedActivities" : {

    }, 
    "SyncErrors" : [

    ]
}
```

# [Back to datamodel summary](000-datamodel-summary.md)


