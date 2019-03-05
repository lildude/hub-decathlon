# Terminology
- **User**: A dict representing a user of tapiriik.
- **Service**: A module, implementing the ServiceBase class, which interacts with a remote site.
- **Service Record**/**Connection**: An object representing a user's connection to a Service.
- **Activity**: A fitness activity. 
- **Non-GPS Activity**: an activity without GPS data
- **Stationary Activity**: an activity with statistical data, but no GPS track *or sensor data* (i.e. stationary activities are a subset of non-GPS activities).
- **Activity UID**: The unique ID of an activity. *NOT* used for deduplication, but is used to locally record activity presence on remote services.
- **External ID**: An ID provided by a remote site.
- **Extended Authorization** vs **Authorization**: Authorization is for storing regular authorization data, Extended Authorization is for storing data the user must opt-in to remember (i.e. passwords).
- **Flow Exception**: Allow the user to control which direction activities flow between connected sites.
- **Exclusion**: An activity may be Excluded if it is not suitable for synchronization: occurs too far in the future, corrupt source files, etc. See below for details.
- **Sync Error**: An error generated during synchronization. See below for the complete guide.
- **Synchronization Worker**: The process that performs the actual synchronization.
- **Synchronization Watchdog**: The process that monitors the Synchronization Workers for stalling or crashes.
- **Stats cron**: The process that calculates and stores all synchronization statistics.


I will attempt to use "function" when referring to an idempotent operation which returns its results, and "method" otherwise. Parameters not marked as (required) are optional.

# [Back to summary](000-summary.md)
## [Back to conception summary](010-conception.md)
