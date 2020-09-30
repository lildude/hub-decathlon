from tapiriik.database import db
from tapiriik.services import Service
from datetime import datetime, timedelta
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "tapiriik.settings"

# Renewal emails
now = datetime.utcnow()


external_ID = ''

connections = db.connections.find({ "ExternalID": {"$eq": external_ID}})

for con in connections:
	print("=====================")
	print(con["_id"])
	print(con["Service"])

	users = db.users.find({ "ConnectedServices.ID": con["_id"]})
	for user in users:
		print("=USER")
		print(user)
