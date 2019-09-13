#!/usr/bin/env python
# Based upon GERT 1.2 (2016-06-03): GIS-based Episode Reconstruction Toolkit
# Ported to itinerum-tripkit by Kyle Fitzsimmons, 2019
import math


# return the duration in seconds between 2 points
def calculate_duration(coordinate1, coordinate2):
    return int((coordinate2.timestamp_UTC - coordinate1.timestamp_UTC).total_seconds())


# return the distance in meters between 2 points based upon Haversine formula
def calculate_distance(coordinate1, coordinate2):
    dlat = math.radians(coordinate2.latitude - coordinate1.latitude)
    dlon = math.radians(coordinate2.longitude - coordinate1.longitude)
    lat1 = math.radians(coordinate1.latitude)
    lat2 = math.radians(coordinate2.latitude)
    a1 = math.sin(dlat / 2) * math.sin(dlat / 2) + math.sin(dlon / 2) * math.sin(dlon / 2)
    a2 = math.cos(lat1) * math.cos(lat2)
    a = a1 * a2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371 * c * 1000


# return the trajectory bearing between 2 points
def calculate_bearing(coordinate1, coordinate2):
    lat1 = math.radians(coordinate1.latitude)
    lat2 = math.radians(coordinate2.latitude)
    dlon = math.radians(coordinate2.longitude - coordinate1.longitude)
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360


# return the change in user heading between 2 point bearings
def calculate_delta_heading(coordinate1, coordinate2):
    delta1 = abs(coordinate1.bearing - coordinate2.bearing)
    delta2 = 360 - delta1
    return min([delta1, delta2])
