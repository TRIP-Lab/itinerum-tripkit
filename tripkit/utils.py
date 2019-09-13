#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import date, datetime
import platform
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

    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def os_is_windows():
    return platform.system() == 'Windows'


class UserNotFoundError(Exception):
    pass
