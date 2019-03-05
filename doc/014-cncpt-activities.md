# Stationary activities
Stationary activities do not have sensor data, just summary data. They are handled in the same structures as regular activities. Stationary activities must be marked as such via `Activity.Stationary=[True|False]`. This will disable checks for minimum waypoint count (etc.) and is used by some services in determining the appropriate upload method. Activities should be marked as soon as possible (i.e. if it can be determined in `DownloadActivityList`), and must be set before the time the activity is sanity checked (after `DownloadActivity`). Otherwise, the flag should remain at the default state (`Stationary = None`) to allow effective coalescing when deduplicating activities.

If a service does not support stationary activities, set `ReceivesStationaryActivities = False`.

# Non-GPS activities
Unlike stationary activities, non-GPS (`activity.GPS = False`) activities can still have sensor data recorded in Waypoints (and therefore should not be flagged as Stationary). Services should be written to allow for uploading Waypoints without Location, although they may ignore such waypoints if the remote site does not support them (e.g. GPX export). 

If the service does not support non-GPS activities, set `ReceivesNonGPSActivitiesWithOtherSensorData = False`.

# [Back to summary](000-summary.md)
## [Back to conception summary](010-conception.md)
