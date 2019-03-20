# stats_cron.py

Ce script fait appel au service ratelimiting de Tapiriik.
Il permet de rafraichir la liste des taux limites enregistrés dans la collection limit.
Ces taux représentent le nombre d'appel maximum d'un service. Ils sont enregistrés en base car ce sont des limites à ne pas dépasser.

### Déroulement du script : 
- Récupération des sync_stats enregistrées en DB sur plusieurs interval de temps
- Récupération des users en base et génération de nouvelles stats
- Récupération de statistiques sur la queue RabbitMQ
```
rmq_user_queue_stats = requests.get(RABBITMQ_USER_QUEUE_STATS_URL).json()
rmq_user_queue_length = rmq_user_queue_stats["messages_ready_details"]["avg"]
rmq_user_queue_rate = rmq_user_queue_stats["message_stats"]["ack_details"]["avg_rate"]
rmq_user_queue_wait_time = rmq_user_queue_length / rmq_user_queue_rate
```
- Suppression des sync_worker_stats datant de plus d'une heure
- Récupération de la somme "TimeTaken" des sync_worker_stats restant et calcul du temps moyen
- Génération des stats error/pending/locked basées sur les champs "SynchronizationWorker / NextSynchronization / NonblockingSyncErrorCount" de la collection Users
- Ajout du résultat de ces stats dans la collection sync_status_stats :
```
{
    "Timestamp": datetime.utcnow(),
    "Locked": lockedSyncRecords,
    "Pending": pendingSynchronizations,
    "ErrorUsers": usersWithErrors,
    "TotalErrors": totalErrors,
    "SyncTimeUsed": timeUsed,
    "SyncEnqueueTime": enqueueTime.total_seconds(),
    "SyncQueueHeadTime": rmq_user_queue_wait_time
}
```
- Mise à jour des informations de la collection stats :
```
{
    "TotalDistanceSynced": distanceSynced,
    "LastDayDistanceSynced": lastDayDistanceSynced,
    "LastHourDistanceSynced": lastHourDistanceSynced,
    "TotalSyncTimeUsed": timeUsed,
    "AverageSyncDuration": avgSyncTime,
    "LastHourSynchronizationCount": totalSyncOps,
    "EnqueueTime": enqueueTime.total_seconds(),
    "QueueHeadTime": rmq_user_queue_wait_time,
    "Updated": datetime.utcnow() 
}
```


- appel de la fonction Refresh du service RateLimit de Tapiriik
```python
for svc in Service.List():
	RateLimit.Refresh(svc.ID, svc.GlobalRateLimits)
``` 
# [Back to script summary](000-script-summary.md)

