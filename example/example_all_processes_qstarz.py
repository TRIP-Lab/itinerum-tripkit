#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
from collections import namedtuple

from tripkit import Itinerum
import tripkit_config


# 1. load itinerum data to database
itinerum = Itinerum()
itinerum.setup(force=False)

# 2. write GIS-compatible outputs of input data
user = itinerum.load_user_by_orig_id(orig_id=17001)
# itinerum.io.write_input_geojson(
#     fn_base=user.uuid,
#     coordinates=user.coordinates,
#     prompts=user.prompt_responses,
#     cancelled_prompts=user.cancelled_prompt_responses,
# )

# 3. detect trips on data and write a GIS-compatible output

# about 90% of provided points seem to be junk, many with the exact
# same lat/lon 1-sec apart with 0-values for accelerations. Clean these
# to properly test point-to-point speed
import csv
import os
import pickle
pickle_fp = f'{user.uuid}.pickle'
if not os.path.exists(pickle_fp):
    prepared_coordinates = itinerum.process.canue.preprocess.run(user.coordinates)
    with open(pickle_fp, 'wb') as pickle_f:
        pickle.dump(prepared_coordinates, pickle_f)
with open(pickle_fp, 'rb') as pickle_f:
    prepared_coordinates = pickle.load(pickle_f)


# augment CANUE Coordinate objects with labels
kmeans_groups = itinerum.process.canue.kmeans.run(prepared_coordinates)
# dbscan_groups = itinerum.process.clustering.hdbscan_ts.run(300, prepared_coordinates)
delta_heading_stdev_groups = itinerum.process.canue.delta_heading_stdev.run(prepared_coordinates)

with open(f'{user.uuid}-prepared_coordinates.csv', 'w', newline='') as csv_f:
    writer = csv.writer(csv_f)
    writer.writerow(['uuid', 'latitude', 'longitude', 'timestamp_UTC', 'duration_s',
                    'distance_m', 'bearing', 'delta_heading', 'avg_distance_m', 'avg_delta_heading',
                    'kmeans_label', 'kmeans_group', 'stdev_label', 'stdev_group'])
    writer.writerows([c.csv_row() for c in prepared_coordinates])
locations = itinerum.process.canue.activity_locations.run(kmeans_groups, delta_heading_stdev_groups)
itinerum.io.write_semantic_locations_geojson(fn_base=user.uuid, locations=locations)

trips = itinerum.process.canue.trip_detection.run(prepared_coordinates, locations)
# itinerum.io.write_trips_geojson(fn_base=user.uuid, trips=trips)
import sys; sys.exit()

parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
user.trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
trip_summaries = itinerum.process.trip_detection.triplab.v2.summarize.run(user, tripkit_config.TIMEZONE)

itinerum.database.save_trips(user, user.trips)
itinerum.io.write_trips_geojson(fn_base=user.uuid, trips=user.trips)
itinerum.io.write_trip_summaries_csv(fn_base=user.uuid, summaries=trip_summaries)

# 4. map match one of the detected trips and write GIS-compatible output
trip1_coordinates = user.trips[0].points
map_matcher = itinerum.process.map_match.osrm(tripkit_config)
# mapmatched_results = map_matcher.match(trip1_coordinates, matcher='DRIVING')

# itinerum.io.write_mapmatched_geojson(fn_base=user.uuid, results=mapmatched_results)

# 5. detect complete days and write csv
complete_day_summaries = itinerum.process.complete_days.triplab.counter.run(user.trips, tripkit_config.TIMEZONE)

itinerum.database.save_trip_day_summaries(user, complete_day_summaries, tripkit_config.TIMEZONE)
itinerum.io.write_complete_days_csv({user.uuid: complete_day_summaries})

# 6. detect activities and write summaries (compact and full)

# This is stopgap approach to create a standardized semantic locations input, this one reads
# locations from an Itinerum survey
def create_activity_locations(user):
    Coordinate = namedtuple('Coordinate', ['latitude', 'longitude'])
    locations = {
        'home': Coordinate(latitude=user.survey_response['location_home_lat'],
                           longitude=user.survey_response['location_home_lon'])
    }
    work = Coordinate(latitude=user.survey_response.get('location_work_lat'),
                      longitude=user.survey_response.get('location_work_lon'))
    if work.latitude and work.longitude:
        locations['work'] = work
    study = Coordinate(latitude=user.survey_response.get('location_study_lat'),
                       longitude=user.survey_response.get('location_study_lon'))
    if study.latitude and study.longitude:
        locations['study'] = study
    return locations

locations = create_activity_locations(user)
activity = itinerum.process.activities.triplab.detect.run(user, locations, tripkit_config.SEMANTIC_LOCATION_PROXIMITY_METERS)
activity_summaries_full = itinerum.process.activities.triplab.detect.summarize_full(activity, tripkit_config.TIMEZONE)
itinerum.io.write_activities_daily_csv(activity_summaries_full)
