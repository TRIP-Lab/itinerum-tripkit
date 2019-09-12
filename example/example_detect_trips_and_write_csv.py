#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
'''
example_detect_trips_and_write_csv.py

This example script loads the points from the itinerum-datakit scratch database and outputs
the results of the trip breaker and complete days algorithms to a customized summary .csv file.
'''
# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)

# begin
import ciso8601
import csv
from datakit import Itinerum
import pytz

import datakit_config


# initialize example script global variables
itinerum = Itinerum(config=datakit_config)
users = itinerum.load_users(limit=5, load_trips=False)
tz = pytz.timezone('America/Montreal')

# run trip detection days algorithms
all_summaries = []
parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
for idx, user in enumerate(users, start=1):
    print('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
    user.trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
    trip_summaries = itinerum.process.trip_detection.triplab.v2.summarize.run(user, tz)
    all_summaries.extend(trip_summaries)


# open the output trips .csv file for writing
csv_name = '{}-trip_summaries.csv'.format(datakit_config.DATABASE_FN.split('.')[0])
export_csv = os.path.join(datakit_config.OUTPUT_DATA_DIR, csv_name)
with open(export_csv, 'w') as csv_f:
    headers = [
        'uuid',
        'trip_id',
        'start_UTC',
        'start',
        'end_UTC',
        'end',
        'trip_code',
        'olat',
        'olon',
        'dlat',
        'dlon',
        # 'merge_codes',
        'direct_distance',
        'cumulative_distance',
        # 'complete_day',
        # 'first_day',
        # 'last_day',
    ]
    writer = csv.DictWriter(csv_f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(all_summaries)
