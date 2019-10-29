#!/usr/bin/env python
# Based upon GERT 1.2 (2016-06-03): GIS-based Episode Reconstruction Toolkit
# Ported to itinerum-tripkit by Kyle Fitzsimmons, 2019
import math
import utm


class Centroid(object):
    def __init__(self, easting, northing, zone_num, zone_letter):
        self.easting = easting
        self.northing = northing
        self.zone_num = zone_num
        self.zone_letter = zone_letter

        self._latlon = None

    def _update_latlon(self):
        if not self._latlon:
            self._latlon = utm.to_latlon(self.easting, self.northing, self.zone_num, self.zone_letter)

    @property
    def lat(self):
        self._update_latlon()
        return self._latlon[0]

    @property
    def lon(self):
        self._update_latlon()
        return self._latlon[1]


def duration_s(coordinate1, coordinate2):
    '''
    Return the duration in seconds between two coordinate records.
    '''
    return int((coordinate2.timestamp_UTC - coordinate1.timestamp_UTC).total_seconds())


def haversine_distance_m(coordinate1, coordinate2):
    '''
    Return the Haversine distance between two coordinates.
    '''
    dlat = math.radians(coordinate2.latitude - coordinate1.latitude)
    dlon = math.radians(coordinate2.longitude - coordinate1.longitude)
    lat1 = math.radians(coordinate1.latitude)
    lat2 = math.radians(coordinate2.latitude)
    a1 = math.sin(dlat / 2) * math.sin(dlat / 2) + math.sin(dlon / 2) * math.sin(dlon / 2)
    a2 = math.cos(lat1) * math.cos(lat2)
    a = a1 * a2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371 * c * 1000


def distance_m(coordinate1, coordinate2):
    '''
    Return the cartesian distance between two coordinates in meters.
    '''
    a = coordinate2.easting - coordinate1.easting
    b = coordinate2.northing - coordinate1.northing
    return math.sqrt(a ** 2 + b ** 2)


def bearing(coordinate1, coordinate2):
    '''
    Return the trajectory bearing between two coordinates.
    '''
    lat1 = math.radians(coordinate1.latitude)
    lat2 = math.radians(coordinate2.latitude)
    dlon = math.radians(coordinate2.longitude - coordinate1.longitude)
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360


def delta_heading(coordinate1, coordinate2):
    '''
    Return the change in user heading between two coordinate bearings.
    '''
    delta1 = abs(coordinate1.bearing - coordinate2.bearing)
    delta2 = 360 - delta1
    return min([delta1, delta2])


# return the centroid from a group of points with easting and northing attributes.
def centroid(coordinates):
    '''
    Return the centroid from a group of points with easting and northing attributes.
    '''
    x, y = [], []
    zone_nums, zone_letters = set(), set()
    for c in coordinates:
        x.append(c.easting)
        y.append(c.northing)
        zone_nums.add(c.zone_num)
        zone_letters.add(c.zone_letter)
    centroid_x = sum(x) / len(x)
    centroid_y = sum(y) / len(y)
    assert len(zone_nums) == 1  # asserts all points are from the same UTM zone
    assert len(zone_letters) == 1
    num, letter = list(zone_nums)[0], list(zone_letters)[0]
    return Centroid(easting=centroid_x, northing=centroid_y, zone_num=num, zone_letter=letter)
