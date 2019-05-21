## Picking the right Exception
### Errors
ServiceExceptions generated in Services are eventually turn into Sync Errors, which...

  - May apply to a specific activity, or an entire remote account.
  - May be blocking (that scope will not be processed until the error is cleared).
  - May be displayed to the user.
  - May allow user intervention to clear a blocking error (e.g. user is prompted to re-authenticate after an authentication failure). Currently, all exceptions displayed to the user require user intervention.
    - Clearing happens in groups (e.g. all 400 authentication failures are cleared at once).

All of these attributes are set through the constructor of the `ServiceException` (or its little-used, entirely-useless subclass `APIException`):

  - `message` (required)
  - `scope` - one of `ServiceExceptionScope.Service` or `ServiceExceptionScope.Account`
  - `block` - boolean for whether the error should block processing of the given scope
  - `user_exception` - an instance of `UserException`

Exceptions thrown in `DownloadActivityList()` will result the service being omitted ("excluded" is the term used in the handling code) from the remainder of the synchronization. 

#### UserException

ServiceExceptions thrown with a UserException given will be displayed to the user as a an error on the dashboard. The constructor takes the following arguments:

  - `type` (required) - one of `UserExceptionType.Authorization`, `UserExceptionType.AccountFull` or `UserExceptionType.AccountExpired`. Determines which message is shown to the user.
  - `intervention_required` (required) - currently all of the UserExceptionTypes assume this is set to True and offer the user a way to clear the associated Sync Error by performing the appropriate action (e.g. successfully reauthorizing the Service Record's remote account)
  - `clear_group` - Clearing one error in a given clear_group clears all other errors in that group. Defaults to `type` if not specified.

ServiceExceptions bearing UserExceptions are generally thrown during synchronization, but may also be generated in the Authorize() function (present in services that use UsernamePassword authentication). These errors are passed to the front-end JS for further case-specific handling (e.g. the TrainingPeaks non-premium account error).

### Exclusions

`APIExcludeActivity` generated within calls to `DownloadActivityList()` or `DownloadActivity()` are turned into Exclusions. An Exclusion applies to a specific activity (identified either by the external ID or a Activity object) in a specific Service Record. Exclusions may be permanent (never cleared) or not permanent (exist only until the beginning of the next synchronization). Excluding an Activity means that the excluding Service will not be called upon to provide further information regarding that Activity (but other Services may be, should they posses the same Activity).

When excluding activities in `DownloadActivityList()`, do not raise the `APIExcludeActivity` - instead, append it to a list to be returned as the second member of the tuple.

The `APIExcludeActivity` constructor takes the following arguments:

 - `message` (required)
 - `activity` (required if not being raised from within `DownloadActivity` AND if `activityId` is not specified) - an instance of an Activity which is to be excluded
 - `activityId` (required if not being raised from within `DownloadActivity` AND if `activity` is not specified) - a unique identifier of the activity to be excluded
 - `permanent` (required) - whether the exclusion should apply permanently (e.g. corrupt file) or until the next synchronization (e.g. a live-tracking activity in progress).

# [Back to summary](000-summary.md)
