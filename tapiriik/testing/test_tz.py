from datetime import datetime, timedelta
import pytz
from dateutil.parser import parse


def _parseDate(self, date):
    #model '2017-12-01T12:00:00+00:00'
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+%Z").replace(tzinfo=pytz.utc)

print(pytz.timezone("UTC"))

startdate = "2018-06-21T09:36:03+02:00"
print(parse(startdate))