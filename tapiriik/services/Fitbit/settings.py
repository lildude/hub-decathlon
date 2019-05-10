from tapiriik.services.interchange import ActivityType


_activityTypeMappings = {
    ActivityType.Cycling: "Ride",
    ActivityType.MountainBiking: "Ride",
    ActivityType.Hiking: "Hike",
    ActivityType.Running: "Run",
    ActivityType.Walking: "Walk",
    ActivityType.Snowboarding: "Snowboard",
    ActivityType.Skating: "IceSkate",
    ActivityType.CrossCountrySkiing: "NordicSki",
    ActivityType.DownhillSkiing: "AlpineSki",
    ActivityType.Swimming: "Swim",
    ActivityType.Gym: "Workout",
    ActivityType.Rowing: "Rowing",
    ActivityType.Elliptical: "Elliptical",
    ActivityType.RollerSkiing: "RollerSki",
    ActivityType.StrengthTraining: "WeightTraining",
    ActivityType.Climbing: "RockClimbing",
    ActivityType.StandUpPaddling: "StandUpPaddling",
}

# For mapping Strava->common
_reverseActivityTypeMappings = {
    "Ride": ActivityType.Cycling,
    "VirtualRide": ActivityType.Cycling,
    "EBikeRide": ActivityType.Cycling,
    "MountainBiking": ActivityType.MountainBiking,
    "VirtualRun": ActivityType.Running,
    "Run": ActivityType.Running,
    "Hike": ActivityType.Hiking,
    "Walk": ActivityType.Walking,
    "AlpineSki": ActivityType.DownhillSkiing,
    "CrossCountrySkiing": ActivityType.CrossCountrySkiing,
    "NordicSki": ActivityType.CrossCountrySkiing,
    "BackcountrySki": ActivityType.DownhillSkiing,
    "Snowboard": ActivityType.Snowboarding,
    "Swim": ActivityType.Swimming,
    "IceSkate": ActivityType.Skating,
    "Workout": ActivityType.Gym,
    "Rowing": ActivityType.Rowing,
    "Kayaking": ActivityType.Rowing,
    "Canoeing": ActivityType.Rowing,
    "StandUpPaddling": ActivityType.StandUpPaddling,
    "Elliptical": ActivityType.Elliptical,
    "RollerSki": ActivityType.RollerSkiing,
    "WeightTraining": ActivityType.StrengthTraining,
    "RockClimbing" : ActivityType.Climbing,
}

walking = [90013,17151,17152,17170,17190,17200,17220,17230,17231]

#activité ID = 21738640934