# Object Hierarchy
## Sync
Contains the main synchronization methods (`PerformGlobalSync` and `PerformUserSync`), and associated functions for deduplicating & coalescing activities, determining destination services, etc.

## User
Contains a list of dicts (`user["ConnectedServices"] = [{"Service": "strava", "ID": ObjectId("1234")}, ...]`) referencing the user's Service Records, along with other metadata (next sync time, total sync error count, etc.)

## ServiceRecord
Representation of a Service Record, includes methods to retrieve and update configuration of that specific Record. 
  * `ExternalID`, `Authorization` and `ExtendedAuthorization` are the values returned by the Service's `Authorize()` function. See above for the difference between `Authorization` and `ExtendedAuthorization`.
  * `SynchronizedActivities` is a list of Activity UIDs which the remote account is known to posses.
  * `Config` is a dict of configuration variables for that service - please use the `GetConfiguration()` function instead, as it automatically resolves default configuration variables.
  * `Service` is a dynamic reference to the Service that the Service Record represents a connection to. 
  * `SyncErrors` and `SyncExclusions` are lists of errors and exclusions, maintained by the synchronization core. Do not directly modify these, instead, raise appropriate exceptions within the Service. Do not access them during a synchronization (they will be empty).

## Activity
Representation of a single activity. Includes all raw activity data, summary statistics, metadata (timezone, type, etc.) and any data attached to it by the originating Service(s).
  * `Stationary` - marks the activity as Stationary or not - must be set to True or False in either DownloadActivityList or DownloadActivity (see below)
  * `GPS` - indicates that the activity has GPS data. Similar to `Stationary`, it must be set to True or False in DownloadActivityList or DownloadActivity
  * `ActivityType` (`Activity.Type`) - what sort of activity this is (running, cycling, etc...)
  * `Device` (`Activity.Device`) - an object specifying the device where the activity data originated, if known (otherwise None)
    * `Serial` (`Activity.Device.Serial`) - the serial number of the device - must be an integer for proper behaviour in FIT and TCX export
    * `VersionMajor`/`VersionMinor` (`Activity.Device.VersionMajor`/`Activity.Device.VersionMinor`) - the version of the device. These correspond with TCX's VersionMajor and VersionMinor elements, and are represented as `Major.Minor` in FIT export (following Garmin's practice)
    * `DeviceIdentifier` (`Activity.Device.Identifier`) - an object specifying the model of device where the activity data originated, if known. Refer to TCXIO, FITIO, and `devices.py` for examples of usage.
  * `ActivityStatistics` (`Activity.Stats`) - includes members for each group of statistics (e.g. heart rate, power)
    * `ActivityStatistic` (e.g. `Activity.Stats.HR`) - includes a standard set of metrics for each statistic group: Value, Average, Max, Min, Gain, Loss. 
      * Not all metrics are relevant to each grouping (e.g. `HR.Gain` or `Distance.Average`), and not all services populate all relevant metrics.
      * Each `ActivityStatistic` has an associated unit of measure (`ActivityStatisticUnit`, in `ActivityStatistic.Unit`), and can be represented in any desired unit (within reason) using the `asUnits(ActivityStatisticUnit.xyz)` function.
  * `Lap` (`Activity.Laps`) - representation of a single lap.
    * In the case of stationary activities without lap information, the `Laps` list must still be populated with a single lap. The statistics of said lap must be identical to the activity as a whole.
    * All laps must have a StartTime and EndTime. Ideally this would be "total time" (vs. moving time, in Lap.Stats.MovingTime), but can also represent moving time (in which case, Lap.Stats.MovingTime should still be set appropriately).
    * `ActivityStatistics` also appear here (in `Lap.Stats`) - these statistics apply only to this lap (e.g. Distance should be the distance travelled between the StartTime and EndTime of the lap)
    * `Waypoint` is a single data point in the lap - inserted chronologically into `Lap.Waypoints`. All `Waypoint`s must contain a `Timestamp` (datetime) and a `Type` (`WaypointType.xyz`). Laps do not need Waypoints - note the section on Stationary activities.
      * They may additionally contain any combination of the following members (if not, the member will be `None`)
        * `Location` - an object containing at either a Latitude and Longitude (WGS84), an `Altitude` (m), or both. Not required, but currently if an activity has waypoints, at least one must contain a valid Lat/Lng.
        * `HR` - BPM
        * `Calories` - kilocalories burned up until and including that point in the Activity
        * `Distance` - distance travelled (m) up until including that point in the Activity
        * `Power` - Watts
        * `Cadence` - RPM
        * `RunCadence` - SPM
        * `Speed` - m/s
        * `Temp` - ºC

## FITIO, TCXIO, GPXIO, PWXIO
Classes to support generation of their respective file formats from an Activity (`Dump(act)`) or creation of an Activity from an existing file (`Parse(data)`). Function signatures vary slightly.

# [Back to summary](000-summary.md)
## [Back to conception summary](010-conception.md)
