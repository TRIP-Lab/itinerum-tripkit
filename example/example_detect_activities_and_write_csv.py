#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)

# begin
import ciso8601
from collections import namedtuple
import csv
from datakit import Itinerum
from datakit.models.Trip import Trip
from datakit.models.TripPoint import TripPoint
import pytz

import datakit_config


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
itinerum = Itinerum(config=datakit_config)
users = itinerum.load_users(load_trips=False, limit=1)
tz = pytz.timezone('America/Montreal')

# initialize output file
csv_name = '{}-activities.csv'.format(datakit_config.DATABASE_FN.split('.')[0])
export_csv = os.path.join(datakit_config.OUTPUT_DATA_DIR, csv_name)
with open(export_csv, 'w') as csv_f:
    headers = ['uuid', 'lat', 'lon', 'start_timestamp', 'end_timestamp', 'activity_type']
    writer = csv.DictWriter(csv_f, fieldnames=headers)
    writer.writeheader()

# perform activity detection on all user points
for idx, user in enumerate(users, start=1):
    # determine the locations to associate with coordinates as activities
    locations = create_activity_locations(user)
    itinerum.process.activities.triplab.detect.run(user, tz, locations)
