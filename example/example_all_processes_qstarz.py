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
user = itinerum.load_user_by_orig_id(orig_id=1)
itinerum.io.geojson.write_inputs(
    fn_base=user.uuid,
    coordinates=user.coordinates,
    prompts=user.prompt_responses,
    cancelled_prompts=user.cancelled_prompt_responses,
)

# 2.1. clean out junk input data
## about 90% of provided points seem to be junk, many with the exact
## same lat/lon 1-sec apart with 0-values for accelerations. Clean these
## to properly test point-to-point speed
# prepared_coordinates = itinerum.process.canue.preprocess.run(user.coordinates)

# ## DEBUG: cache above (comment both)
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

# 3. detect trips on data and write a GIS-compatible output
# augment CANUE Coordinate objects with labels
kmeans_groups = itinerum.process.canue.kmeans.run(prepared_coordinates)
delta_heading_stdev_groups = itinerum.process.canue.delta_heading_stdev.run(prepared_coordinates)
locations = itinerum.process.activities.canue.detect_locations.run(kmeans_groups, delta_heading_stdev_groups)
itinerum.io.geojson.write_semantic_locations(fn_base=user.uuid, locations=locations)

user.trips = itinerum.process.trip_detection.canue.algorithm.run(tripkit_config, prepared_coordinates, locations)
itinerum.database.save_trips(user, user.trips)
itinerum.io.geojson.write_trips(fn_base=user.uuid, trips=user.trips)
# itinerum.io.write_trip_summaries_csv(fn_base=user.uuid, summaries=trip_summaries)

# 4. map match one of the detected trips and write GIS-compatible output
trip1_coordinates = user.trips[0].points
map_matcher = itinerum.process.map_match.osrm(tripkit_config)
mapmatched_results = map_matcher.match(trip1_coordinates, matcher='WALKING')
itinerum.io.geojson.write_mapmatch(fn_base=user.uuid, results=mapmatched_results)

# 5. detect complete days and write csv
complete_day_summaries = itinerum.process.complete_days.canue.counter.run(user.trips, tripkit_config.TIMEZONE)
itinerum.database.save_trip_day_summaries(user, complete_day_summaries, tripkit_config.TIMEZONE)
itinerum.io.csv.write_complete_days({user.uuid: complete_day_summaries})

# 6. detect activities and write summaries (compact and full)
activity = itinerum.process.activities.canue.tally_times.run(
    user, locations, tripkit_config.SEMANTIC_LOCATION_PROXIMITY_METERS
)
activity_summaries = itinerum.process.activities.canue.summarize.run_full(activity, tripkit_config.TIMEZONE)
itinerum.io.csv.write_activities_daily(activity_summaries['records'], extra_cols=activity_summaries['duration_keys'])
