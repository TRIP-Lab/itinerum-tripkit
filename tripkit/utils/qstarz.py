#!/usr/bin/env python
# Kyle Fitzsimmons, 2021
#
# Contains helpers only related to QStarz
import utm

from ..models import ActivityLocation


# returns a list of ActivityLocations from an Itinerum-type user
def create_activity_locations(known_locations):
    '''
    Create locations from survey answers to create activity centroids to match with a given user's coordinates.
    '''
    locations = []
    for label, location in known_locations.items():
        lon, lat = location
        easting, northing, zone_num, zone_letter = utm.from_latlon(lat, lon)
        locations.append(ActivityLocation(
            label,
            lat, 
            lon,
            easting,
            northing,
            zone_num,
            zone_letter
        ))
    return locations
