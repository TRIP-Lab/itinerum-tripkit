#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
# run from parent directory
import os
import sys
import tripkit_config_itinerum as cfg

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
### begin
from collections import namedtuple
import logging
from tripkit import TripKit, utils

logging.basicConfig(level=logging.INFO)
logging.getLogger('itinerum-tripkit').setLevel(level=logging.DEBUG)


# 1. load itinerum data to database
tripkit = TripKit(config=cfg)
tripkit.setup(force=False)

# 2. write GIS-compatible outputs of input data
user = tripkit.load_users(uuid='bcb6958f-7b86-43ce-b8f8-8794e4cb18b6')
tripkit.io.shapefile.write_inputs(
    fn_base=user.uuid,
    coordinates=user.coordinates,
    prompts=user.prompt_responses,
    cancelled_prompts=user.cancelled_prompt_responses,
)

# 3. detect trips on data and write a GIS-compatible output
parameters = {
    'subway_entrances': tripkit.database.load_subway_entrances(),
    'break_interval_seconds': cfg.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': cfg.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': cfg.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': cfg.TRIP_DETECTION_ACCURACY_CUTOFF_METERS,
}
user.trips = tripkit.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
trip_summaries = tripkit.process.trip_detection.triplab.v2.summarize.run(user, cfg.TIMEZONE)

tripkit.database.save_trips(user, user.trips)
tripkit.io.shapefile.write_trips(fn_base=user.uuid, trips=user.trips)
tripkit.io.csv.write_trips(fn_base=user.uuid, trips=user.trips)
tripkit.io.csv.write_trip_summaries(fn_base=user.uuid, summaries=trip_summaries)

# 4. map match one of the detected trips and write GIS-compatible output
trip1_coordinates = user.trips[0].points
map_matcher = tripkit.process.map_match.osrm(cfg)
mapmatched_results = map_matcher.match(trip1_coordinates, matcher='DRIVING')
tripkit.io.shapefile.write_mapmatch(fn_base=user.uuid, results=mapmatched_results)

# 5. detect complete days and write csv
complete_day_summaries = tripkit.process.complete_days.triplab.counter.run(user.trips, cfg.TIMEZONE)
tripkit.database.save_trip_day_summaries(user, complete_day_summaries, cfg.TIMEZONE)
tripkit.io.csv.write_complete_days({user.uuid: complete_day_summaries})

# 6. detect activities and write summaries (compact and full)
# This is stopgap approach to create a standardized semantic locations input, this one reads
# locations from an Itinerum survey
locations = utils.itinerum.create_activity_locations(user)
activity = tripkit.process.activities.triplab.detect.run(user, locations, cfg.ACTIVITY_LOCATION_PROXIMITY_METERS)
activity_summaries_full = tripkit.process.activities.triplab.summarize.run_full(activity, cfg.TIMEZONE)
duration_cols = [
    'commute_time_work_s',
    'commute_time_study_s',
    'dwell_time_home_s',
    'dwell_time_work_s',
    'dwell_time_study_s',
]
tripkit.io.csv.write_activities_daily(activity_summaries_full, extra_cols=duration_cols)
