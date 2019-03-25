# Rollback tasks.py

## Summary
One document represent one rollback stat for one user.
It is logging rollback task.

## Relations 
* `rollback_tasks.UserID` N <-> 1 `users._id`
* `rollback_tasks.PendingDeletions.[SERVICE_NAME]` N <-> N `uploaded_activities.ExternalID`

## Data model : 
```JSON
{ 
    "_id" : ObjectId("xxxxxxx"), 
    "PendingDeletions" : {
        "decathloncoachpreprod" : [
            "eu2beb87e79e8c211f9e", 
            "eu2d2c55122ae47a6183", 
            "eu2aaee0699037fb4f56", 
            "eu26ff6af9aac884ee7b", 
            "eu2caa85f322153860da"
        ], 
        "decathloncoach" : [
            "eu26c0cd3d3f39a428ae", 
            "eu2e760061b3d09d848f", 
            "eu2dd187a7d48d24b24d"
        ]
    }, 
    "Created" : ISODate("YYYY-MM-DDTHH:mm:ssZ"), 
    "UserID" : ObjectId("xxxxxxxxx")
}
```

# [Back to datamodel summary](000-datamodel-summary.md)


