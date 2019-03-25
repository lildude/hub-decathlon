# Uploaded activities.py

## Summary
Uploaded activities collection is used to store activities.
One document represent any activities for one user.
It is related to any connections (an activity_record can be set to any connection service)

## Relations 
* `uploaded_activities.UserExternalID` N <-> N `connections.ExternalID`

## Data model : 
```JSON
{ 
    "_id" : ObjectId("xxxxxxx"), 
    "ExternalID" : "xxxxx", 
    "Service" : "[SERVICE NAME]", 
    "UserExternalID" : "xxxxxxxx", 
    "Timestamp" : ISODate("YYYY-MM-DDTHH:mm:ssZ")
}

```

# [Back to datamodel summary](000-datamodel-summary.md)


