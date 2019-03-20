# I hate time zones
Some sites have great timezone support, some don't. In order to deal with the case of transferring activities from a TZ-naive source to a TZ-aware destination, and to ease deduplication, there are several built in methods on the Activity object.

There are two different places timezones can be applied to an activity - `Activity.TZ` and the individual timestamps within the activity (e.g. `StartTime`, `Waypoint.Timestamp`). `Activity.TZ` should only be set in cases where the time zone of the activity's occurrence is known. Timestamps should be assigned time zones as appropriate for the format (e.g. all timestamps originating from GPXIO will be in UTC, while the same activity from PWXIO would be TZ-naive). TZ-aware and TZ-naive timestamps should not be mixed within an activity (i.e. `StartTime` being TZ-aware but `EndTime` being TZ-naive is a bad thing).

To reconcile this potential discrepancy, the sync core automatically calls `EnsureTZ` immediately before attempting activity uploads.

pytz is used for all timezone operations.

## `Activity.EnsureTZ()`
Long story short, ensures that `Activity.TZ` is set appropriately. Calls `CalulcateTZ()` in all cases, but CalculateTZ will simply return the existing `Activity.TZ` if `recalculate=True` is not given.

## `Activity.CalculateTZ()`
Attempts to determine a time zone for the activity. The most common case involves looking up the first geographic coordinate in the activity in a database of timezone boundaries. 

 - If there are no geographic Waypoints in the activity, or you wish to override the point used for calculation, you may supply `loc=Location()`. 
 - If no geographic Waypoints exist and no `loc` is specified (as is the case with stationary activites), the calculation will fall back to the value of `FallbackTZ` (populated by the synchronization core, determined by the majority of the user's other activities, if available).
 - If none of the above apply, the calculation will fail.

The calculation sets `Activity.TZ` but does not change the timezones associated with any of the timestamps within the Activity.

## `Activity.AdjustTZ()` and `Activity.DefineTZ()`
These methods update all the timestamps contained within the activity to reflect the current value of `Activity.TZ`. Use `DefineTZ()` when the timestamps are TZ-naive, and `AdjustTZ()` when the timestamps are already TZ-aware.

# [Back to summary](000-summary.md)
## [Back to conception summary](010-conception.md)
