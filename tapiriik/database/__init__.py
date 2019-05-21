from pymongo import MongoClient, MongoReplicaSetClient
from tapiriik.settings import MONGO_HOST_API, MONGO_REPLICA_SET, MONGO_CLIENT_OPTIONS, REDIS_HOST, REDIS_CLIENT_OPTIONS, MONGO_DB_PREFIX

# MongoDB

client_class = MongoClient if not MONGO_REPLICA_SET else MongoReplicaSetClient
if MONGO_REPLICA_SET:
	MONGO_CLIENT_OPTIONS["replicaSet"] = MONGO_REPLICA_SET

_connection = client_class(host=MONGO_HOST_API, **MONGO_CLIENT_OPTIONS)

db = _connection[MONGO_DB_PREFIX+"tapiriik"]
cachedb = _connection[MONGO_DB_PREFIX+"tapiriik_cache"]
tzdb = _connection[MONGO_DB_PREFIX+"tapiriik_tz"]
# The main db currently has an unfortunate lock contention rate
ratelimit = _connection[MONGO_DB_PREFIX+"tapiriik_ratelimit"]

# Redis
if REDIS_HOST:
	import redis as redis_client
	redis = redis_client.Redis(host=REDIS_HOST, **REDIS_CLIENT_OPTIONS)
else:
	redis = None # Must be defined

def close_connections():
	try:
		_connection.close()
	except:
		pass

import atexit
atexit.register(close_connections)
