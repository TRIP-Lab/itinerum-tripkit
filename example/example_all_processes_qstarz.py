#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
# run from parent directory
import os
import sys
import tripkit_config_qstarz as cfg

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
import logging
from tripkit import TripKit

logging.basicConfig(level=logging.INFO)
logging.getLogger('itinerum-tripkit').setLevel(level=logging.DEBUG)


# 1. load itinerum data to database
tripkit = TripKit(config=cfg)
tripkit.setup(force=False)

# 2. write GIS-compatible outputs of input data
user = tripkit.load_user_by_orig_id(orig_id=1)
tripkit.io.shapefile.write_inputs(
    fn_base=user.uuid,
    coordinates=user.coordinates,
    prompts=user.prompt_responses,
    cancelled_prompts=user.cancelled_prompt_responses,
)

# 2.1. clean out junk input data
## about 90% of provided points seem to be junk, many with the exact
## same lat/lon 1-sec apart with 0-values for accelerations. Clean these
## to properly test point-to-point speed
prepared_coordinates = tripkit.process.canue.preprocess.run(user.uuid, user.coordinates)

# 3. detect trips on data and write a GIS-compatible output
# augment CANUE Coordinate objects with labels
kmeans_groups = tripkit.process.clustering.kmeanspp.run(prepared_coordinates)
delta_heading_stdev_groups = tripkit.process.clustering.delta_heading_stdev.run(prepared_coordinates, stdev_cutoff=0.2)
locations = tripkit.process.activities.canue.detect_locations.run(kmeans_groups, delta_heading_stdev_groups)
tripkit.io.shapefile.write_activity_locations(fn_base=user.uuid, locations=locations)

user.trips = tripkit.process.trip_detection.canue.algorithm.run(cfg, prepared_coordinates, locations)
trip_summaries = tripkit.process.trip_detection.canue.summarize.run(user, cfg.TIMEZONE)
tripkit.database.save_trips(user, user.trips)
tripkit.io.shapefile.write_trips(fn_base=user.uuid, trips=user.trips)
tripkit.io.csv.write_trips(fn_base=user.uuid, trips=user.trips)
tripkit.io.csv.write_trip_summaries(fn_base=user.uuid, summaries=trip_summaries)

# 4. map match one of the detected trips and write GIS-compatible output
trip1_coordinates = user.trips[0].points
map_matcher = tripkit.process.map_match.osrm(cfg)
mapmatched_results = map_matcher.match(trip1_coordinates, matcher='WALKING')
tripkit.io.shapefile.write_mapmatch(fn_base=user.uuid, results=mapmatched_results)

# 5. detect complete days and write csv
complete_day_summaries = tripkit.process.complete_days.canue.counter.run(user.trips, cfg.TIMEZONE)
tripkit.database.save_trip_day_summaries(user, complete_day_summaries, cfg.TIMEZONE)
tripkit.io.csv.write_complete_days({user.uuid: complete_day_summaries})

# 6. detect activities and write summaries (compact and full)
activity = tripkit.process.activities.canue.tally_times.run(user, locations, cfg.ACTIVITY_LOCATION_PROXIMITY_METERS)
activity_summaries = tripkit.process.activities.canue.summarize.run_full(activity, cfg.TIMEZONE)
tripkit.io.csv.write_activities_daily(activity_summaries['records'], extra_cols=activity_summaries['duration_keys'])
