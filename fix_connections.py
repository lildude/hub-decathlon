from tapiriik.database import db
from tapiriik.settings import _GLOBAL_LOGGER
from bson.objectid import ObjectId

users = db.users.find()
#user = db.users.find_one({"_id": ObjectId(user_id)})


for user in users :

    #print(user)
    try : 
        conns = user['ConnectedServices']
        usr_connected_services = [x['Service'] for x in user['ConnectedServices']] 
        usr_connections = [x['Service'] for x in db.connections.find({"_id": {"$in": [x["ID"] for x in conns]}})]
        usr_lost_svc = [service_name for service_name in list(set(usr_connected_services) ^ set(usr_connections))]

        if len(usr_lost_svc) > 0 :
            _GLOBAL_LOGGER.info("USER : "+str(user))
            _GLOBAL_LOGGER.info("User connected services : \t"+str(usr_connected_services))
            _GLOBAL_LOGGER.info("User connections : \t\t"+str(usr_connections))
            _GLOBAL_LOGGER.info("User lost service : \t\t"+str(usr_lost_svc))

            _GLOBAL_LOGGER.info(str("\n\n-----------------SEPARATOR-----------------\n\n"))

            new_usr_connected_services = [{"Service":x['Service'], "ID":x["_id"]} for x in db.connections.find({"_id": {"$in": [x["ID"] for x in conns]}})]

            _GLOBAL_LOGGER.info("Actual user connected service in db : \t"+str([x for x in user['ConnectedServices']]))
            _GLOBAL_LOGGER.info("The new one shall look like this : \t"+str(new_usr_connected_services))

            _GLOBAL_LOGGER.info(str("\n\n-----------------RIPPING USER-----------------\n\n"))
            user['ConnectedServices'] = new_usr_connected_services
            _GLOBAL_LOGGER.info("User with new connected services : "+str(user))

            db.users.update_one({"_id": user["_id"]},{"$set":user})
    except :
        print("oops!")