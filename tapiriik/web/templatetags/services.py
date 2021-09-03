from django import template
from tapiriik.services import Service, ServiceRecord
from tapiriik.database import db
register = template.Library()

@register.filter(name="svc_by_id")
def ID(values, id):
    svc_id_array = [value for value in values if value.ID == id]
    if len(svc_id_array) == 1:
        return svc_id_array[0]
    else:
        return None


@register.filter(name="svc_ids")
def IDs(value):
    return [x["Service"] for x in value]


@register.filter(name="svc_providers_except")
def exceptSvc(value):
    connections = [y["Service"] for y in value]
    return [x for x in Service.List() if x.ID not in connections]

@register.filter(name="svc_populate_conns")
def fullRecords(conns):
    return [ServiceRecord(x) for x in db.connections.find({"_id": {"$in": [x["ID"] for x in conns]}})]
