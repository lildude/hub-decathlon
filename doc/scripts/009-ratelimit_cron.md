# ratelimite_cron.py

This script calls ratelimiting of Tapiriik.
It's refreshing some limit rate store un limit collection.
These rates represent the maximum number of calls for a service. They are registered in base because they are not supposed to be exceeded.

## Script flow: 
- Call Refresh function of the RateLimit service of Tapiriik
```python
for svc in Service.List():
	RateLimit.Refresh(svc.ID, svc.GlobalRateLimits)
``` 

## Conf implementation:
Var to set in local_settings.py for Decathlon Service
```python
import datetime

DECATHLON_RATE_LIMITS=[(datetime.timedelta(seconds=xxx), yyy), (datetime.timedelta(seconds=xxx2), yyy2), ...]
```
##How it works ?
For a named service (decathlon for example). A new function is called before EVERY api request. This function increments counter in limit collection, for specific service.
- Example code :
```python
#Check rate limit, increment and block process if limit excedeed 
self._rate_limit()
#API request
resp = requests.get("url")
```
- Decathlon _rate_limit function:
```python
def _rate_limit(self):
    try:
        RateLimit.Limit(self.ID)
    except RateLimitExceededException:
        raise ServiceException("Global rate limit reached", user_exception=UserException(UserExceptionType.RateLimited))

```

# [Back to script summary](000-script-summary.md)

