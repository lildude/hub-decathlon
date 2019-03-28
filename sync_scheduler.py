from tapiriik.database import db
from datetime import datetime
from pymongo.read_preferences import ReadPreference
from tapiriik.helper.sqs.manager import SqsManager
import time
import uuid
import json


print("-----[ INITIALIZE SYNC_SCHEDULER ]-----")
sqsManager = SqsManager()
sqsManager.get_queue()
while True:
    generation = str(uuid.uuid4())
    queueing_at = datetime.utcnow()
    users = list(db.users.with_options(read_preference=ReadPreference.PRIMARY).find(
                {
                    "NextSynchronization": {"$lte": datetime.utcnow()},
                    "QueuedAt": {"$exists": False}
                },
                {
                    "_id": True,
                    "SynchronizationHostRestriction": True
                }
            ))

    scheduled_ids = [x["_id"] for x in users]
    print("[Sync_scheduler]--- Found %d users at %s" % (len(scheduled_ids), datetime.utcnow()))

    db.users.update_many({"_id": {"$in": scheduled_ids}}, {"$set": {"QueuedAt": queueing_at, "QueuedGeneration": generation}, "$unset": {"NextSynchronization": True}}, upsert=False)
    print("[Sync_scheduler]--- Marked %d users as queued at %s" % (len(scheduled_ids), datetime.utcnow()))

    now = datetime.now()
    messages = []
    for user in users:
        # build user message body
        # user_generation is used to set ID message, ID message is an identifier for a message in a batch, and used to communicate the result
        user_generation = str(uuid.uuid4()) + '-' + str(user["_id"])
        body = {
            'user_id': str(user["_id"]),
            'datetime': now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            'message_generator': 'sync_scheduler',
            'generation': generation
        }

        # If not empty, add synchronization host restriction
        if "SynchronizationHostRestriction" in user and user["SynchronizationHostRestriction"]:
            body['routing_key'] = {
                'StringValue': user["SynchronizationHostRestriction"],
                'DataType': 'String'
            }
        # transform body into JSON format
        parsed_body = json.dumps(body)

        user_message = {
            'Id': user_generation,
            'MessageBody': parsed_body
        }

        # append user message into list (it will be send as a batch into queue)
        messages.append(user_message)

    # publish all message
    sqsManager.send_messages(messages)
    print("[Sync_scheduler]--- Scheduled %d users at %s" % (len(scheduled_ids), datetime.utcnow()))

    time.sleep(1)
