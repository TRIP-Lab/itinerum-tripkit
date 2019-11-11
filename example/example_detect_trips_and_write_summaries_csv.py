#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
'''
example_detect_trips_and_write_csv.py

This example script loads the points from the itinerum-tripkit scratch database and outputs
the results of the trip breaker and complete days algorithms to a customized summary .csv file.
'''
# run from parent directory
import os
import sys
import tripkit_config_itinerum as cfg

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
import ciso8601
import csv
import logging
from tripkit import TripKit

logging.basicConfig(level=logging.INFO)
logging.getLogger('itinerum-tripkit').setLevel(level=logging.DEBUG)


# initialize example script global variables
tripkit = TripKit(config=cfg)
tripkit.setup()

users = tripkit.load_users(limit=5, load_trips=False)

# run trip detection days algorithms
all_summaries = []
parameters = {
    'subway_entrances': tripkit.database.load_subway_entrances(),
    'break_interval_seconds': cfg.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': cfg.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': cfg.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': cfg.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
for idx, user in enumerate(users, start=1):
    print('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
    user.trips = tripkit.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
    trip_summaries = tripkit.process.trip_detection.triplab.v2.summarize.run(user, cfg.TIMEZONE)
    all_summaries.extend(trip_summaries)

# open the output trips .csv file for writing
csv_name = f'{cfg.SURVEY_NAME}-trip_summaries.csv'
tripkit.io.csv.write_trip_summaries(csv_name, all_summaries)
