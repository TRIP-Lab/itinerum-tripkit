#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
''' example_detect_trips_and_write_csv.py
    This example script loads the points from the itinerum-datakit scratch database
    and outputs the results of the trip breaker and complete days algorithms to a
    summary .csv file.
'''

# run from parent directory
import os
import sys
sys.path[0] = sys.path[0].replace('/extra', '')
os.chdir(sys.path[0])
# begin
import ciso8601
import csv
from datakit import Itinerum
from datakit.models.Trip import Trip
from datakit.models.TripPoint import TripPoint
import pytz

import datakit_config


# initialize example script global variables
itinerum = Itinerum(config=datakit_config)
users = itinerum.load_users(load_trips=False)
tz = pytz.timezone('America/Montreal')

# open the output trips .csv file for writing
csv_name = '{}-trips.csv'.format(datakit_config.DATABASE_FN.split('.')[0])
export_csv = os.path.join(datakit_config.OUTPUT_DATA_DIR, csv_name)
with open(export_csv, 'w') as csv_f:
    headers = ['uuid', 'trip_id', 'start', 'end', 'trip_code',
               'olat', 'olon', 'dlat', 'dlon', 'merge_codes',
               'direct_distance', 'cumulative_distance', 'complete_day',
               'first_day', 'last_day']
    writer = csv.DictWriter(csv_f, fieldnames=headers)
    writer.writeheader()


# run trip detection and complete days algorithms
all_summaries = []
parameters = {
    'subway_stations': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
}
for idx, user in enumerate(users, start=1):
    print('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
    trips, summaries = itinerum.process.trip_detection.triplab.v1.algorithm.run(user.coordinates.dicts(),
                                                                                parameters=parameters)

    trip_objs = {}
    for trip_num, trip in trips.items():
        for c in trip:
            point = TripPoint(latitude=c['latitude'],
                              longitude=c['longitude'],
                              h_accuracy=c['h_accuracy'],
                              timestamp_UTC=c['timestamp_UTC'],
                              database_id=c['id'])

            trip_num = c['trip']
            if trip_num not in trip_objs:
                trip_objs[trip_num] = Trip(num=trip_num, trip_code=c['trip_code'])
            trip_objs[trip_num].points.append(point)
    user.trips = [value for key, value in sorted(trip_objs.items())]

    if user.trips:
        complete_days = itinerum.process.complete_days.triplab.counter.run(user.trips, tz)
        sorted_complete_days = list(sorted(complete_days.keys()))

    if summaries:
        for summary in summaries.values():
            summary['uuid'] = user.uuid

            trip_date = tz.localize(summary['start']).date()
            if trip_date in complete_days:
                summary['complete_day'] = complete_days[trip_date]['is_complete']
            else:
                summary['complete_day'] = ''
            if trip_date == sorted_complete_days[0]:
                summary['first_day'] = True
            if trip_date == sorted_complete_days[-1]:
                summary['last_day'] = True

            for key, value in summary.items():
                if isinstance(value, bool):
                    summary[key] = int(value)
            all_summaries.append(summary)

    # append batches of 50 rows to .csv
    if idx % 50 == 0:
        with open(export_csv, 'a') as csv_f:
            writer = csv.DictWriter(csv_f, fieldnames=headers)
            writer.writerows(all_summaries)
        all_summaries = []
# append any remaining rows to .csv
with open(export_csv, 'a') as csv_f:
    writer = csv.DictWriter(csv_f, fieldnames=headers)
    writer.writerows(all_summaries)
