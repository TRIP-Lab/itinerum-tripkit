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

# 2.1. clean out junk input data
## about 90% of provided points seem to be junk, many with the exact
## same lat/lon 1-sec apart with 0-values for accelerations. Clean these
## to properly test point-to-point speed
prepared_coordinates = tripkit.process.canue.preprocess.run(user.uuid, user.coordinates)

# 3. detect trips on data and write a GIS-compatible output
user.trips = tripkit.process.trip_detection.canue.algorithm.run(cfg, prepared_coordinates, user.activity_locations)
trip_summaries = tripkit.process.trip_detection.canue.summarize.run(user, cfg.TIMEZONE)

# 5. detect complete days and write csv
complete_day_summaries = tripkit.process.complete_days.canue.counter.run(user.trips, cfg.TIMEZONE)

# 6. write condensed outputs to file
tripkit.io.csv.write_condensed_activity_locations(user)
tripkit.io.csv.write_condensed_trip_summaries(user, trip_summaries, complete_day_summaries)
