#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys
sys.path[0] = sys.path[0].replace('/extra', '')
os.chdir(sys.path[0])

# begin
from datakit import Itinerum

import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)


# -- Stage 1: load platform data to cache if surveys responses table does not exist
itinerum.setup(force=True)

# -- Stage 2: perform trip detection via library algorithms
users = itinerum.load_users()

parameters = {
    'subway_stations': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS    
}

all_summaries = []
for idx, user in enumerate(users, start=1):
    print('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
    user.trips, summaries = itinerum.process.trip_detection.triplab.algorithm.run(user.coordinates.dicts(),
                                                                                  parameters=parameters)
    if summaries:
        all_summaries.extend(list(summaries.values()))


# -- Stage 3: save output in database as cache
# format trips into a SQL-friendly flat list of labelled coordinates
print('Writing detected trip data to the database...')
detected_trip_points = []
for user in users:
    if user.trips:
        for trip_num, trip in user.trips.items():
            for c in trip:
                c['uuid'] = user.uuid
                detected_trip_points.append(c)
itinerum.database.save_trips(detected_trip_points)


# -- Stage 4: save summaries output to .csv file
print('Writing summaries to .csv...')
csv_filename = '{}-trip_summaries.csv'.format(datakit_config.DATABASE_FN.split('.')[0])
itinerum.io.write_trip_summaries_csv(datakit_config, csv_filename, all_summaries)
