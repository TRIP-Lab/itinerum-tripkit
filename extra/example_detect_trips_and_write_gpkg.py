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
user = itinerum.load_users(uuid='01cf0f37-e017-438e-aa71-c56d23166c50', load_trips=False)
print(user.uuid)

parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
user.trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters)
itinerum.io.write_trips_geopackage(datakit_config, fn_base=str(user.uuid), trips=user.trips)
