#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


class ActivityLocation(object):
    '''
    Library object for recurring locations where dwell times are calculated.

    :param label:       Semantic name for the location.
    :param latitude:    Activity location centroid's latitude.
    :param longitude:   Activity location centroid's longitude.
    :param easting:     UTM meter representation of the activity location's longitude.
    :param northing:    UTM meter representation of the latitude.
    :param zone_num:    Corresponding UTM zone number.
    :param zone_letter: Corresponding UTM zone letter (if present).

    :type label:       str
    :type latitude:     float
    :type longitude:   float
    :type easting:     float, optional
    :type northing:    float, optional
    :type zone_num:    int, optional
    :type zone_letter: str, optional
    '''

    def __init__(self, label, latitude, longitude, easting=None, northing=None, zone_num=None, zone_letter=None):
        self.label = label
        self.latitude = latitude
        self.longitude = longitude
        self.easting = easting
        self.northing = northing
        self.zone_num = zone_num
        self.zone_letter = zone_letter

    def __repr__(self):
        return f"<tripkit.models.ActivityLocation label={self.label} lat={self.latitude} lon={self.longitude}>"
