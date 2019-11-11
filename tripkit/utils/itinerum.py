#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
#
# Contains helpers only related to hardcoded aspects of Itinerum platform
from ..models import ActivityLocation


# returns a list of ActivityLocations from an Itinerum-type user
def create_activity_locations(user):
    '''
    Create locations from survey answers to create activity centroids to match with a given user's coordinates.
    '''
    locations = [
        ActivityLocation('home', user.survey_response['location_home_lat'], longitude=user.survey_response['location_home_lon'])
    ]
    work_lat = user.survey_response.get('location_work_lat')
    work_lon = user.survey_response.get('location_work_lon')
    if work_lat and work_lon:
        locations.append(ActivityLocation('work', work_lat, work_lon))
    study_lat = user.survey_response.get('location_study_lat')
    study_lon = user.survey_response.get('location_study_lon')
    if study_lat and study_lon:
        locations.append(ActivityLocation('study', study_lat, study_lon))
    return locations
