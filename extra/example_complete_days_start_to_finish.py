#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys
sys.path[0] = sys.path[0].replace('/extra', '')
os.chdir(sys.path[0])

# begin
from datetime import datetime

from datakit import Itinerum
import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)


# -- Stage 1: load platform data to cache if surveys responses table does not exist
itinerum.setup(force=False)

# # -- Stage 2: perform trip detection via library algorithms
users = itinerum.load_users(load_trips=False)

itinerum.database.save_trips([])  # clear existing

parameters = {
    'subway_stations': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS    
}
results = {}
detected_trip_points = []
for idx, user in enumerate(users, start=1):
    print('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
    results[user] = itinerum.process.trip_detection.triplab.v1.algorithm.run(user.coordinates.dicts(),
                                                                             parameters=parameters)

    # -- Stage 2.1: save output in database as cache format trips
    # into a SQL-friendly flat list of labelled coordinates
    if len(results) == 50:
        print('Writing detected trip data to the database...')
        for user, (trips, summaries) in results.items():
            if trips:
                for trip in trips.values():
                    for c in trip:
                        c['uuid'] = user.uuid
                        detected_trip_points.append(c)
        itinerum.database.save_trips(detected_trip_points, overwrite=False)
        results = {}
        detected_trip_points = []

for user, (trips, summaries) in results.items():
    if trips:
        for trip in trips.values():
            for c in trip:
                c['uuid'] = user.uuid
                detected_trip_points.append(c)
itinerum.database.save_trips(detected_trip_points, overwrite=False)


# -- Stage 3: Count complete days without missing trip information
users = itinerum.load_users()
trip_day_summaries = []
for idx, user in enumerate(users, start=1):
    print('Processing user ({}) daily counts: {}/{}...'.format(user.uuid, idx, len(users)))

    geojson_fn = '{}-datakit'.format(user.uuid)
    itinerum.io.write_input_geojson(datakit_config,
                                    fn_base=geojson_fn,
                                    coordinates=user.coordinates,
                                    prompts=user.prompt_responses,
                                    cancelled_prompts=user.cancelled_prompt_responses)

    gpkg_fn = '{}-datakit'.format(user.uuid)
    itinerum.io.write_trips_geopackage(datakit_config,
                                       fn_base=gpkg_fn,
                                       trips=user.trips)

    if user.trips:
        results = itinerum.process.complete_days.triplab.counter.run(user.trips)
        for date, row in results.items():
            row['uuid'] = user.uuid
            row['date_UTC'] = date
            trip_day_summaries.append(row)
    else:
        print('No trips available for: {}'.format(user.uuid))

print('Saving trip day summaries to database...')
itinerum.database.save_trip_day_summaries(trip_day_summaries)


# -- Stage 4: write complete days to .csv
print('Loading complete days from cache...')
trip_day_summaries = {}
for user in users:
    trip_day_summaries[user.uuid] = itinerum.database.load_trip_day_summaries(user)

print('Saving complete day summaries to .csv...')
csv_name = '{}-datakit-complete_days.csv'.format(datakit_config.DATABASE_FN.split('.')[0])
itinerum.io.write_complete_days_csv(datakit_config, csv_name, trip_day_summaries)
