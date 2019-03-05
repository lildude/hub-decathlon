# Creating your own Service

Great! It's not all that hard, you could probably figure it out just by looking at the existing Services. Here are some areas to watch out for:

## Authorization
Services may authorize remote accounts via OAuth or direct Username/Password entry. 

### OAuth
Services should specify the appropriate `UserAuthorizationURL`, and implement `GenerateUserAuthorizationURL` if the authorization URL must be unique (take a look at Dropbox for an example of this). This is the URL that the user will be redirected to when they click Connect. The appropriate return URL can be generated with `WEB_ROOT + reverse("oauth_return", kwargs={"service": "serviceid"})`

Once the user returns from a successful OAuth transaction, `RetrieveAuthorizationToken()` will be called. 

### Username/Password
Services must still specify a UserAuthorizationURL (which will be local to tapiriik - see Endomondo for an example). When a user attempts to authorize, `Authorize()` is called.

The Service should specify `RequiresExtendedAuthorizationDetails = True` if storage of the raw credentials is required (i.e. use of Extended Authorization) is required. If this is True and no Extended Authorization details are available (i.e. user did not opt to have them remembered), the Service will be omitted from synchronization.

### What to return from  `RetrieveAuthorizationToken()`/`Authorize()`
You should return a triple containing:

- External ID of the remote account (required)
- Authorization dict - this will be stored directly in the Service Record. If no authorization details are appropriate (e.g. they are all in Extended Authorization), an empty dict must be specified.
- Extended Authorization dict - this will be made available in the Service Record (where it is stored varies on whether the user opted to save their credentials). The `CredentialStorage` class should be used when appropriate. If no extended authorization details are appropriate, omit this.

## `DownloadActivityList()`
tapiriik operates with two different modes of synchronization: partial and exhaustive/full. If the `exhaustive` kwarg is not set, this function should return only the most recent *n* activities for the given Service Record (common values for *n* are 50 and 25). The exact number returned in this case is not important, just that we are not enumerating thousands of activities over tens of pages, since new activities are only likely to appear in the recent past. If `exhaustive` is set, every activity in the account should be returned.

The `Activity.ServiceData` member is available to store data like remote activity IDs. If set here, its value is made available (in the same member) in future calls to `DownloadActivity()`.

This method should return a tuple, the first member being a list of Activities, the second a list of APIExcludeExceptions. If activities are excluded, they should be omitted from the former list.

## WTH is `WebInit()`?
It's a method called only when the web interface is starting up (i.e. not in the synchronization worker), allowing you to make Django calls like `reverse()`.

# [Back to summary](000-summary.md)
