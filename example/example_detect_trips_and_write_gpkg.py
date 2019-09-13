#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
from datakit import Itinerum

import datakit_config


# Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)

# -- Load user trip from database and write as GIS-compatible file
users = itinerum.load_users(load_trips=False)

parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
for user in users:
    user.trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters)
    itinerum.database.save_trips(user, user.trips)
    itinerum.io.write_trips_geopackage(datakit_config, fn_base=user.uuid, trips=user.trips)
