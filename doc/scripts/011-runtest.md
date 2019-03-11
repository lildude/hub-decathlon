# ratelimite_cron.py

Ce script permet de faire appel à des séries de tests, réalisés dans un environnement similaire, mais dont les configurations de base de données / queue / sont différentes.


### Déroulement du script : 
- appels des différentes fonctions de réalisation des tests unitaires
```
unittest.main()
```
- suppression des bases de données de test, et cache test.
```
tapiriik.database._connection.drop_database("tapiriik_test")
tapiriik.database._connection.drop_database("tapiriik_cache_test")
```
 
# [Back to script summary](000-script-summary.md)

