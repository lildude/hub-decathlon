# stats_cron.py

This script insert / update some sync_status_stats and stats document.
These stats are calculated from users collection.

### Script flow : 
- Getting some sync_stats stored in DB, for multiple time interval
- Getting users in DB and some new stats
- Getting all RabbitMQ queue's stats
```
rmq_user_queue_stats = requests.get(RABBITMQ_USER_QUEUE_STATS_URL).json()
rmq_user_queue_length = rmq_user_queue_stats["messages_ready_details"]["avg"]
rmq_user_queue_rate = rmq_user_queue_stats["message_stats"]["ack_details"]["avg_rate"]
rmq_user_queue_wait_time = rmq_user_queue_length / rmq_user_queue_rate
```
- Delete all sync_worker_stats older than "now - 1 hour"
- Getting the sum of "TimeTaken" of all sync_worker_stats and getting average time of execution.
- Getting some stats (error/pending/locked) based on "SynchronizationWorker / NextSynchronization / NonblockingSyncErrorCount" fields of users collection
- Add result into sync_status_stats collection :
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
- Update stats collection infos
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

# [Back to script summary](000-script-summary.md)

