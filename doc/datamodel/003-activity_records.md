# Activity Records.py

## Summary
Activity records collection is used to store activity data.
One document represent any activities for one user.
It is related to any connections (an activity_record can be set to any connection service)

## Relations 
* `activity_records.UserID` N <-> 1 `users._id`
* `activity_records.Activities.UIDS` N <-> N `connections.SynchronizedActivities`

## Data model : 
```JSON
{ 
    "_id" : ObjectId("xxxxxxx"), 
    "UserID" : ObjectId("xxxxxxx"), 
    "Activities" : [
        {
            "StartTime" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
            "EndTime" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
            "Type" : "Running", 
            "Name" : "[ACTIVITY NAME]", 
            "Notes" : null, 
            "Private" : false, 
            "Stationary" : "1", 
            "Distance" : 0.0, 
            "UIDs" : [
                "xxxxxxxxxx"
            ], 
            "Prescence" : {
                "[SERVICE_NAME_1]" : {
                    "Processed" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
                    "Synchronized" : null, 
                    "Exception" : null
                }, 
                "[SERVICE_NAME_2]" : {
                    "Processed" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
                    "Synchronized" : null, 
                    "Exception" : null
                }
            }, 
            "Abscence" : {

            }, 
            "FailureCounts" : {

            }
        },
        ...
    ]
}
```

# [Back to datamodel summary](000-datamodel-summary.md)


