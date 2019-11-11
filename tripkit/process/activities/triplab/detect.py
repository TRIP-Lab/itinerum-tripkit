#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
#
# This module tallies the commute and dwell times for a user over the course of
# a survey and reports this output by date and aggregate for the survey period.
# There are 2 categories for dwell times: those during the course of a detected trip
# (`dwell_times`) and those occuring between trips (`stay_times`). For the sake
# of concise reporting, these are combined in the final output.
import itertools
import logging
from tripkit.utils import geo

from .models import UserActivity

logger = logging.getLogger('itinerum-tripkit.process.activites.triplab.detect')


def generate_locations(location_columns, survey_response):
    '''
    Generates the dictionary object for passing to `activities.triplab.detect.run` with
    the labeled location as the key and list of [latitude, longitude] as the value.

    :param dict columns:         A dictionary object with the location label as the key and
                                 and a list of the survey response column names for latitude
                                 and longitude.
    :param dict survey_response: A dictionary object with a user's survey response information
                                 including semantic location coordinates.
    '''
    locations = {}
    for label, columns in location_columns.items():
        lat_col, lon_col = columns
        lat, lon = survey_response[lat_col], survey_response[lon_col]
        if lat and lon:
            locations[label] = [survey_response[lat_col], survey_response[lon_col]]
    return locations


# check whether two semantic locations could be detected for the same coordinates
def detect_semantic_location_overlap(uuid, locations, activity_proximity_m):
    for loc1, loc2 in itertools.combinations(locations, 2):
        distance_between_m = geo.haversine_distance_m(loc1, loc2)
        if distance_between_m <= (activity_proximity_m * 2):
            logger.warn(f"possible overlap in semantic locations: {uuid} {loc1}-->{loc2} ({distance_between_m} m)")


def label_trip_points(locations, trip, proximity_m):
    '''
    Labels each trip point with its closest semantic location.

    :param locations:   List of activity locations with semantic labels.
    :param trip:        Detected trip from user coordinates.
    :param proximity_m: The buffer distance (meters) from the activity location centroid to label trip points.

    :type locations:   list of :py:class:`tripkit.models.ActivityLocation`
    :type trip:        :py:class:`tripkit.models.Trip`
    :type proximity_m: int
    '''
    for p in trip.points:
        p.label = None
        for location in locations:
            if geo.haversine_distance_m(p, location) <= proximity_m:
                p.label = location.label
                continue


def classify_commute(trip):
    '''
    Count the time spent commuting between either home and work or home and study.

    :param `py:class:Trip` trip: An itinerum-tripkit trip object
    '''
    commute_label = None
    if trip.start.label == 'home':
        if trip.end.label == 'work':
            commute_label = 'work'
        elif trip.end.label == 'study':
            commute_label = 'study'
    elif trip.start.label == 'work' and trip.end.label == 'home':
        commute_label = 'work'
    elif trip.start.label == 'study' and trip.end.label == 'home':
        commute_label = 'study'
    return commute_label


def classify_dwell(last_trip, trip):
    '''
    Count the time spent at known locations by tallying the intervals between labeled points.

    :param `py:class:Trip` last_trip: An itinerum-tripkit trip object for the trip immediately prior to the provided `trip`
    :param `py:class:Trip` trip:      An itinerum-tripkit trip object
    '''
    # test for semantic location in last 5 points of previous trip and first 5 points of next trip
    end_location = None
    for p in last_trip.points[-5:]:
        if p.label:
            end_location = p.label
            break
    start_location = None
    for p in trip.points[:5]:
        if p.label:
            start_location = p.label
            break
    if end_location and end_location == start_location:
        return end_location


def run(user, locations, proximity_m=50):
    logger.info(f"Tallying semantic location dwell times for {user.uuid}...")
    if not user.trips:
        logger.info(f"No trips available.")
        return
    if not locations:
        logger.info("No activity locations provided.")
        return
    detect_semantic_location_overlap(user.uuid, locations, proximity_m)

    # tally distances and durations for semantic locations by date and as aggregate totals for all trips
    activity = UserActivity(user.uuid)
    last_t = None
    for t in user.trips:
        label_trip_points(locations, t, proximity_m)

        # classify commute times for trips occuring between semantic locations
        commute_label = classify_commute(t)
        activity.add_commute_time(t.start_UTC, t.end_UTC, commute_label)

        # classify dwell times for stays at the same semantic location between two consecutive trips
        if last_t:
            dwell_label = classify_dwell(last_t, t)
            activity.add_dwell_time(last_t.end_UTC, t.start_UTC, dwell_label)
        last_t = t

        activity.add_trip(t)
    return activity
