#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import date, datetime
import uuid


# serialize types not handled by default by JSON library to string
def json_serialize(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    # extremely hacky way to naively serialize peewee objects
    if 'peewee.' in str(type(obj)):
        return str(obj)

    raise TypeError("Object of type %s is not JSON serializable" % type(obj))



class UserNotFoundError(Exception):
    pass