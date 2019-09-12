#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
from datetime import datetime

from datakit import Itinerum
import datakit_config


# Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)


# -- Stage 1: load platform data to cache if surveys responses table does not exist
itinerum.setup(force=False)
users = itinerum.load_users(limit=10, load_trips=False)

# -- Stage 2: perform trip detection via library algorithms
parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}

for idx, user in enumerate(users, start=1):
    print("Processing user ({}) trips: {}/{}...".format(user.uuid, idx, len(users)))
    user.trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
    itinerum.database.save_trips(user, user.trips, overwrite=True)

# -- Stage 3: Count complete days without missing trip information
trip_day_summaries = {}
for idx, user in enumerate(users, start=1):
    print("Processing user ({}) daily counts: {}/{}...".format(user.uuid, idx, len(users)))

    if user.trips:
        print(f"Running complete days process on {user.uuid}...")
        summaries = itinerum.process.complete_days.triplab.counter.run(user.trips, datakit_config.TIMEZONE)
        itinerum.database.save_trip_day_summaries(user, summaries, datakit_config.TIMEZONE)
        trip_day_summaries[user.uuid] = summaries
    else:
        print('No trips available for: {}'.format(user.uuid))

# -- Stage 4: write complete days to .csv
print("Saving complete day summaries to .csv...")
csv_name = '{}-datakit-complete_days.csv'.format(datakit_config.DATABASE_FN.split('.')[0])
itinerum.io.write_complete_days_csv(datakit_config, csv_name, trip_day_summaries)
