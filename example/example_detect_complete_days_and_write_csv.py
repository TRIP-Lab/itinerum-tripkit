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
from datetime import datetime
from tripkit import TripKit

logging.basicConfig(level=logging.INFO)
logging.getLogger('itinerum-tripkit').setLevel(level=logging.DEBUG)


# Edit ./tripkit_config.py first!
tripkit = TripKit(config=cfg)


# -- Stage 1: load platform data to cache if surveys responses table does not exist
tripkit.setup(force=False)
users = tripkit.load_users(limit=10, load_trips=False)

# -- Stage 2: perform trip detection via library algorithms
parameters = {
    'subway_entrances': tripkit.database.load_subway_entrances(),
    'break_interval_seconds': cfg.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': cfg.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': cfg.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': cfg.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
for idx, user in enumerate(users, start=1):
    print("Processing user ({}) trips: {}/{}...".format(user.uuid, idx, len(users)))
    user.trips = tripkit.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
    tripkit.database.save_trips(user, user.trips, overwrite=True)

# -- Stage 3: Count complete days without missing trip information
trip_day_summaries = {}
for idx, user in enumerate(users, start=1):
    print("Processing user ({}) daily counts: {}/{}...".format(user.uuid, idx, len(users)))

    if user.trips:
        print(f"Running complete days process on {user.uuid}...")
        summaries = tripkit.process.complete_days.triplab.counter.run(user.trips, cfg.TIMEZONE)
        tripkit.database.save_trip_day_summaries(user, summaries, cfg.TIMEZONE)
        trip_day_summaries[user.uuid] = summaries
    else:
        print('No trips available for: {}'.format(user.uuid))

# -- Stage 4: write complete days to .csv
print("Saving complete day summaries to .csv...")
tripkit.io.csv.write_complete_days(trip_day_summaries)
