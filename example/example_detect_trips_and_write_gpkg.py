#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
# run from parent directory
import os
import sys
import tripkit_config_itinerum as cfg

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
import logging
from tripkit import TripKit

logging.basicConfig(level=logging.INFO)
logging.getLogger('itinerum-tripkit').setLevel(level=logging.DEBUG)


# Edit ./tripkit_config.py first!
tripkit = TripKit(config=cfg)
tripkit.setup()

# -- Load user trip from database and write as GIS-compatible file
users = tripkit.load_users(load_trips=False)

parameters = {
    'subway_entrances': tripkit.database.load_subway_entrances(),
    'break_interval_seconds': cfg.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': cfg.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': cfg.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': cfg.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
for user in users:
    user.trips = tripkit.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters)
    tripkit.database.save_trips(user, user.trips)
    tripkit.io.geopackage.write_trips(fn_base=user.uuid, trips=user.trips)
