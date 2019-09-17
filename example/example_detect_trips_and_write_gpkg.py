#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
from tripkit import Itinerum

import tripkit_config


# Edit ./tripkit_config.py first!
itinerum = Itinerum(config=tripkit_config)
itinerum.setup()

# -- Load user trip from database and write as GIS-compatible file
users = itinerum.load_users(load_trips=False)

parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
for user in users:
    user.trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters)
    itinerum.database.save_trips(user, user.trips)
    itinerum.io.write_trips_geopackage(tripkit_config, fn_base=user.uuid, trips=user.trips)
