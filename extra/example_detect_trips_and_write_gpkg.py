#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys
sys.path[0] = sys.path[0].replace('/extra', '')
os.chdir(sys.path[0])

# begin
from datakit import Itinerum
from pprint import pprint

import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)

# -- Load user trip from database and write as GIS file
user = itinerum.load_users(uuid='005991eb-3c17-4a7c-ba3d-e66210910bf8', load_trips=False)
# parameters = {
#     'subway_stations': itinerum.database.load_subway_entrances(),
#     'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
#     'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
#     'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
#     'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS    
# }
# user.detected_trip_coordinates = itinerum.process.trip_detection.triplab.v1.algorithm.run(user.coordinates.dicts(), parameters)

parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS    
}
user.detected_trip_coordinates = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters)

itinerum.database.load_trips(user)
print(user.trips)

# pprint(user.survey_response)
# print('num trips:', len(user.trips))
itinerum.io.write_trips_geopackage(datakit_config, fn_base=uuid, trips=user.trips)
