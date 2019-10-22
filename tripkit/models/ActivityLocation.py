#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


class ActivityLocation(object):
    def __init__(self, label, latitude, longitude, easting=None, northing=None, zone_num=None, zone_letter=None):
        self.label = label
        self.latitude = latitude
        self.longitude = longitude
        self.easting = easting
        self.northing = northing
        self.zone_num = zone_num
        self.zone_letter = zone_letter
