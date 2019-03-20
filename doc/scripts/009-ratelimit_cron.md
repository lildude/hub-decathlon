# ratelimite_cron.py

Ce script fait appel au service ratelimiting de Tapiriik.
Il permet de rafraichir la liste des taux limites enregistrés dans la collection limit.
Ces taux représentent le nombre d'appel maximum d'un service. Ils sont enregistrés en base car ce sont des limites à ne pas dépasser.

### Déroulement du script : 
- appel de la fonction Refresh du service RateLimit de Tapiriik
```python
for svc in Service.List():
	RateLimit.Refresh(svc.ID, svc.GlobalRateLimits)
``` 
# [Back to script summary](000-script-summary.md)

