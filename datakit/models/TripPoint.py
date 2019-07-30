#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import datetime


class TripPoint(object):
    """
    :param integer database_id:    The GPS point's original database coordinates record id.
    :param float latitude:         The GPS point's latitude.
    :param float longitude:        The GPS point's longitude.
    :param float h_accuracy:       The reported horizontal accuracy of a GPS point.
    :param datetime timestamp_UTC: The point's naive datetime localized to UTC.

    :ivar timestamp_epoch:         The point's datetime within the UNIX epoch format.
    :vartype timestamp_epoch:      int

    """

    def __init__(self, database_id, latitude, longitude, h_accuracy, timestamp_UTC):
        assert isinstance(timestamp_UTC, datetime)

        self.database_id = database_id
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.h_accuracy = float(h_accuracy)
        self.timestamp_UTC = timestamp_UTC
        self.timestamp_epoch = (timestamp_UTC - datetime(1970, 1, 1)).total_seconds()

    def __repr__(self):
        return f"<TripPoint ({self.latitude}, {self.longitude}) {self.timestamp_UTC}>"
