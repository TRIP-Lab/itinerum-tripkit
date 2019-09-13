#!/usr/bin/env python
# Kyle Fitzsimmons, 2019

# 0: setup - run from parent directory
import os
import sys
sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)

# begin
from tripkit import Itinerum
import tripkit_config

STAGE_1 = True
STAGE_2 = True
STAGE_3 = True
STAGE_4 = True
STAGE_5 = True


# 1: import .csv's from Itinerum or QStarz to scratch database and load user objects
itinerum = Itinerum(config=tripkit_config)
itinerum.setup(force=STAGE_1)

users = itinerum.load_users()
if not isinstance(users, list):
    users = [users]

# 2: run trip detection on user coordinates and save to database
if STAGE_2:
    parameters = {
        'subway_entrances': itinerum.database.load_subway_entrances(),
        'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
        'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
        'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
        'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
    }
    for user in users:
        user.trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
        itinerum.database.save_trips(user, user.trips)

# 3: run complete days on user trips and save metrics to database
if STAGE_3:
    for user in users:
        trip_day_summaries = itinerum.process.complete_days.triplab.counter.run(user.trips, tripkit_config.TIMEZONE)
        if trip_day_summaries:
            itinerum.database.save_trip_day_summaries(user, trip_day_summaries, tripkit_config.TIMEZONE)

# 4: count time spent at semantic locations
users_activity_summaries = []
if STAGE_4:
    for user in users:
        user_locations = itinerum.process.activities.triplab.detect.generate_locations(
            location_columns=tripkit_config.SEMANTIC_LOCATIONS, survey_response=user.survey_response)
        activity_summary = itinerum.process.activities.triplab.detect.run(
            user, locations=user_locations, proximity_m=tripkit_config.SEMANTIC_LOCATION_PROXIMITY_M)
        users_activity_summaries.append(activity_summary)

# 5: generate output data as .csv, .xlsx, pandas dataframe (feather?)
if STAGE_5:
    if users_activity_summaries:
        itinerum.io.write_user_summaries_csv(tripkit_config, users_activity_summaries)
    for user in users:
        user_locations = itinerum.process.activities.triplab.detect.generate_locations(
            location_columns=tripkit_config.SEMANTIC_LOCATIONS, survey_response=user.survey_response)
        itinerum.io.write_semantic_locations_geonjson(
            tripkit_config, fn_base=user.uuid, locations=user_locations)
        itinerum.io.write_trips_csv(tripkit_config, fn_base=user.uuid, trips=user.trips)
        itinerum.io.write_trips_geojson(tripkit_config, fn_base=user.uuid, trips=user.trips)

        # 5.1: run HDBSCAN with timeseries filtering on coordinates to help detect stop locations
        points = [p for t in user.trips for p in t.points]
        cluster_locations = itinerum.process.clustering.hdbscan_ts.run(
            tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS, points)
        itinerum.io.write_semantic_locations_geonjson(tripkit_config,
                                                      fn_base=str(user.uuid) + '-clusters',
                                                      locations=cluster_locations)
