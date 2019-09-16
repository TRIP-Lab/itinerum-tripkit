#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
from collections import namedtuple
from tripkit import Itinerum

import tripkit_config


def create_activity_locations(user):
    '''
    Create locations known from survey answers to create activity centroids to match
    with a given user's coordinates.
    '''
    Coordinate = namedtuple('Coordinate', ['latitude', 'longitude'])
    locations = {
        'home': Coordinate(
            latitude=user.survey_response['location_home_lat'], longitude=user.survey_response['location_home_lon']
        )
    }
    work = Coordinate(
        latitude=user.survey_response.get('location_work_lat'), longitude=user.survey_response.get('location_work_lon')
    )
    if work.latitude and work.longitude:
        locations['work'] = work
    study = Coordinate(
        latitude=user.survey_response.get('location_study_lat'),
        longitude=user.survey_response.get('location_study_lon'),
    )
    if study.latitude and study.longitude:
        locations['study'] = study
    return locations


# -- main
# NOTE: the ./example_detect_complete_days_and_write_csv.py can pre-populate all
# data in cache needed to run this example

itinerum = Itinerum(config=tripkit_config)
users = itinerum.load_users(limit=50)

# perform activity detection on all user points
dwell_time_summaries = []
for idx, user in enumerate(users, start=1):
    # determine the locations to associate with coordinates as activities
    locations = create_activity_locations(user)
    itinerum.io.write_semantic_locations_geojson(tripkit_config, fn_base=user.uuid, locations=locations)

    summary = itinerum.process.activities.triplab.detect.run(
        user, locations, proximity_m=tripkit_config.SEMANTIC_LOCATION_PROXIMITY_METERS, timezone=tripkit_config.TIMEZONE
    )
    if summary:
        dwell_time_summaries.append(summary)
# write .csv output
itinerum.io.write_user_summaries_csv(tripkit_config, dwell_time_summaries)
