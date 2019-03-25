# ratelimite_cron.py

This script calls ratelimiting of Tapiriik.
It's refreshing some limit rate store un limit collection.
These rates represent the maximum number of calls for a service. They are registered in base because they are not supposed to be exceeded.

### Script flow: 
- Call Refresh function of the RateLimit service of Tapiriik
```python
for svc in Service.List():
	RateLimit.Refresh(svc.ID, svc.GlobalRateLimits)
``` 
# [Back to script summary](000-script-summary.md)

