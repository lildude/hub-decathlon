# Deduplication
The rules to deduplicate activities are described in `_accumulateActivities`. In short, if the activities have identical start times, or their start times are +/- 3 minutes, or their start times are +/- 30 seconds plus [-38, 38] hours and/or 30/-30 minutes (for TZ mistakes), and their activity types match (or are reasonably similar, e.g. MTB vs. Biking), then the activity is considered the same. Otherwise it will be re-uploaded.

Once Activities are determined to be duplicate, their details are coalesced into a single Activity. In general, the first activity to be listed is given preference, with exceptions for...

 - Start/End time - the timezone from the latter activity will apply to the former if the former is not TZ-aware and the latter is.
 - Activity Type - the most specific activity type is chosen (e.g. Mountain Biking over Cycling)
 - Private - the most restrictive setting is chosen
 - Stationary - False overrides True
 - Stats - they are averaged

# [Back to summary](000-summary.md)
## [Back to conception summary](010-conception.md)
