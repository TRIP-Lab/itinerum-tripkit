#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
# !! NOTE: A tripbreaking script must be run before this example can function. !!
# run from parent directory
import os
import sys
import tripkit_config_itinerum as cfg

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
import logging
from tripkit import TripKit, utils
from tripkit.models import ActivityLocation

logging.basicConfig(level=logging.INFO)
logging.getLogger('itinerum-tripkit').setLevel(level=logging.DEBUG)


# -- main
tripkit = TripKit(config=cfg)
tripkit.setup()
users = tripkit.load_users(limit=1)

# perform activity detection on all user points
daily_activity_summaries = []
for idx, user in enumerate(users, start=1):
    # determine the locations to associate with coordinates as activities
    locations = utils.itinerum.create_activity_locations(user)
    tripkit.io.geojson.write_activity_locations(fn_base=user.uuid, locations=locations)

    complete_day_summaries = tripkit.process.complete_days.triplab.counter.run(user.trips, cfg.TIMEZONE)
    activity = tripkit.process.activities.triplab.detect.run(user, locations, cfg.ACTIVITY_LOCATION_PROXIMITY_METERS)
    summaries = tripkit.process.activities.triplab.summarize.run_full(activity, cfg.TIMEZONE)
    if summaries:
        daily_activity_summaries.extend(summaries)

# write .csv output with itinerum semantic locations
duration_cols = [
    'commute_time_work_s',
    'commute_time_study_s',
    'dwell_time_home_s',
    'dwell_time_work_s',
    'dwell_time_study_s',
]
tripkit.io.csv.write_activities_daily(daily_activity_summaries, extra_cols=duration_cols)
