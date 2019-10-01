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
itinerum = Itinerum(config=tripkit_config)
itinerum.setup(force=False)

# 2. write GIS-compatible outputs of input data
user = itinerum.load_users(uuid='00807c5b-7542-4868-8462-14b79a9fcc9f')
itinerum.io.write_input_geojson(
    cfg=tripkit_config,
    fn_base=user.uuid,
    coordinates=user.coordinates,
    prompts=user.prompt_responses,
    cancelled_prompts=user.cancelled_prompt_responses,
)

# 3. detect trips on data and write a GIS-compatible output
parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
user.trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
trip_summaries = itinerum.process.trip_detection.triplab.v2.summarize.run(user, tripkit_config.TIMEZONE)

itinerum.database.save_trips(user, user.trips, overwrite=True)
csv_name = '{}-trip_summaries.csv'.format(tripkit_config.DATABASE_FN.split('.')[0])
itinerum.io.write_trip_summaries_csv(tripkit_config, csv_name, trip_summaries)
itinerum.io.write_trips_geojson(cfg=tripkit_config, fn_base=user.uuid, trips=user.trips)

# 4. map match one of the detected trips and write GIS-compatible output
map_matcher = itinerum.process.map_match.osrm(tripkit_config)
mapmatched_results = map_matcher.match(coordinates=user.trips[1].points, matcher='DRIVING')

itinerum.io.write_mapmatched_geojson(cfg=tripkit_config, fn_base=user.uuid, results=mapmatched_results)

# 5. detect complete days and write csv
complete_day_summaries = itinerum.process.complete_days.triplab.counter.run(user.trips, tripkit_config.TIMEZONE)

itinerum.database.save_trip_day_summaries(user, complete_day_summaries, tripkit_config.TIMEZONE)
itinerum.io.write_complete_days_csv(tripkit_config, {user.uuid: complete_day_summaries})

# 6. detect activities and write summaries (compact and full)
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
itinerum.io.write_activities_daily_csv(tripkit_config, activity_summaries_full)
