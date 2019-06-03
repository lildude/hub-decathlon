from tapiriik.services import Service
from tapiriik.services.ratelimiting import RateLimit

for svc in Service.List():
	print("service : " + svc.DisplayName)
	RateLimit.Refresh(svc.ID, svc.GlobalRateLimits)
