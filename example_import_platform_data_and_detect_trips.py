#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datakit import Itinerum

import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)


# -- Stage 1: load platform data to cache if surveys responses table does not exist
# itinerum.setup(force=False)

# -- Stage 2: perform trip detection via library algorithms
users = itinerum.load_users()

parameters = {
    'subway_stations': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS    
}

results = {}
for idx, user in enumerate(users, start=1):
    print('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
    results[user] = itinerum.process.trip_detection.triplab.algorithm.run(user.coordinates.dicts(),
                                                                          parameters=parameters)

# -- Stage 3: save output in database as cache
# format trips into a SQL-friendly flat list of labelled coordinates
print('Writing detected trip data to the database...')
detected_trip_points = []
for user, (trips, summaries) in results.items():
    if trips:
        for trip_num, trip in trips.items():
            for c in trip:
                c['uuid'] = user.uuid
                detected_trip_points.append(c)
itinerum.database.save_trips(detected_trip_points)
