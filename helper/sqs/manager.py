# Synchronization module for decathloncoach.com
# (c) 2019 Anael Jourdain, anael.jourdain.partner@decathlon.com
from tapiriik.settings import AWS_SQS_ZONE, AWS_SQS_QUEUE_NAME
import json
import boto3

class SqsManager():

    AWS_ZONE = AWS_SQS_ZONE
    QUEUE_NAME = AWS_SQS_QUEUE_NAME
    _resource = None
    _queue = None
    _queue_url = None
    _messages = []

    def __init__(self):
        print("-----[ INITIALIZE A NEW SQS QUEUE MANAGER ]-----")
        self.AWS_ZONE = AWS_SQS_ZONE
        # Create SQS client resource
        self._resource = boto3.resource('sqs', region_name=self.AWS_ZONE)
        self._client = boto3.client('sqs', region_name=self.AWS_ZONE)
        print("[Helper SQS]--- Define SQS resource in %s AWS zone" % self.AWS_ZONE)

    # Function use to get a specific queue from AWS SQS, it uses self.QUEUE_NAME as parameter
    # Queue will be available in self._queue
    def get_queue(self, queue_name=None):

        if queue_name:
            self.QUEUE_NAME = queue_name
        print("[Helper SQS]--- Get queue %s in %s resource" % (self.QUEUE_NAME, self.AWS_ZONE))
        self._queue = self._resource.get_queue_by_name(QueueName=self.QUEUE_NAME)
        self._queue_url = self._queue.url

    def send_message(self, entry):
        self._queue.send_message(Entries=entry)
        print('---[ Sending %i messages into queue' % len(entry))

    # Function use to send a list of message.
    # Messages are send to self._queue
    def send_messages(self, entries):
        if len(entries) > 0:
            print('[Helper SQS]--- Trying to send %i users messages into queue' % len(entries))
            response = self._queue.send_messages(Entries=entries)
            #if len(response.get('SuccessFull')):
                #print('---[ Sending %i messages into queue' % len(response.get('SuccessFull')))

            response_json = json.dumps(response)
            # TODO: These lines below are not working
            if 'SuccessFul' in response_json:
                print('[Helper SQS]--- Sending %d messages into queue' % len(response['SuccessFul']))
            if 'Failed' in response_json:
                print('[Helper SQS]--- Fail sending %d messages into queue' % len(response['Failed']))

        else:
            print('[Helper SQS]--- Nothing to send')

    # Function use to get a message from self._queue
    # Message will be available in self._messages
    def get_message(self, attributes_names):
        self._messages = self._queue.receive_messages(AttributeNames=attributes_names, MaxNumberOfMessages=1)
        if self._messages:
            print("[Helper SQS]--- Getting message from queue")
        else:
            print("[Helper SQS]--- No message found. Queue is empty !")


    # Function use to get a list of 1 message (1 by default, 10 max) from self._queue
    # Messages will be available in self._messages
    def get_messages(self, attributes_names):
        self._messages = self._queue.receive_messages(AttributeNames=attributes_names)
        if self._messages :
            print("[Helper SQS]--- Getting some messages from queue")
        else:
            print("[Helper SQS]--- No message found. Queue is empty !")

    # Fonction use to remove a specific message in self._queue
    def delete_message(self, message):
        message.delete()
        print("[Helper SQS]--- Deleting one message")

    # Function use to remove a specific message by receipt_handle, using default queue
    def delete_message_by_receipt_handle(self, receipt_handle, queue_url=None):
        self._client.delete_message(QueueUrl=(queue_url if queue_url is not None else self._queue.url), ReceiptHandle=receipt_handle)
        print("[Helper SQS]--- Deleting one message by receipt handle (%s)" % receipt_handle)

    # Function use to remove all message in queue
    # current_queue determine if we remove ALL message in queue or just current sample of message
    def clear_queue(self, current_queue=True, attributes_names=None):

        print('[Helper SQS]--- Cleaning the queue')
        if attributes_names is None:
            attributes_names = ['all']

        while self._messages:
            for message in self._messages:
                self.delete_message(message)

            if current_queue is False:
                self.get_message(attributes_names)

    def process(self, entries, add=False, delete_message=True):
        self.get_queue()
        if add:
            self.send_messages(entries)
        self.get_message(['all'])

        while self._messages:
            for message in self._messages:
                """
                text = ''
                if message.message_attributes is not None:
                    user_id = message.message_attributes.get('user_id').get('StringValue')
                    if user_id:
                        text = 'User ID : ({0})'.format(user_id)

                    routing_key = message.message_attributes.get('routing_key').get('StringValue')
                    if routing_key:
                        text = text + 'RoutingKey : ({0})'.format(routing_key)
                """
                # Print out the body and author (if set)
                print('Message ID : {0} / {1}'.format(message.message_id ,message.body))

                if delete_message is True:
                    self.delete_message(message)
            self.get_message(['all'])

        if delete_message is not True:
            self.clear_queue()
