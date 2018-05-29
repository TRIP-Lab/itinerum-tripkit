#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import datetime


class TripPoint(object):
    def __init__(self, latitude, longitude, h_accuracy, timestamp_UTC):
        assert isinstance(timestamp_UTC, datetime)

        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.h_accuracy = float(h_accuracy)
        self.timestamp_UTC = timestamp_UTC
        self.timestamp_epoch = (timestamp_UTC - datetime(1970, 1, 1)).total_seconds()
