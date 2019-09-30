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

from geopy.distance import distance

from .models import UserActivity
from .utils import localize


# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
        distance_between_m = distance(locations[loc1], locations[loc2]).meters
        if distance_between_m <= (activity_proximity_m * 2):
            logger.warn(f"possible overlap in semantic locations: {uuid} {loc1}-->{loc2} ({distance_between_m} m)")


# label each trip point with its closest semantic location
def label_trip_points(locations, trip, proximity_m):
    for p in trip.points:
        p.label = None
        for label, location in locations.items():
            if distance([p.latitude, p.longitude], location).meters <= proximity_m:
                p.label = label
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


def _tally_commutes_all(activity):
    commutes = {'total': 0}
    for start_UTC, end_UTC, label in activity.commute_times:
        duration = (end_UTC - start_UTC).total_seconds()
        commutes['total'] += duration
        commutes.setdefault(label, 0)
        commutes[label] += duration
    return commutes


def _tally_dwells_all(activity):
    dwells = {'total': 0}
    for start_UTC, end_UTC, label in activity.dwell_times:
        duration = (end_UTC - start_UTC).total_seconds()
        dwells['total'] += duration
        dwells.setdefault(label, 0)
        dwells[label] += duration
    return dwells


# returns rows for a .csv summary of activity and complete days
def summarize_condensed(user_activity, day_summaries, timezone):
    # aggregate survey tallies
    tallies = {
        'uuid': user_activity.uuid,
        'start_timestamp_UTC': user_activity.first_seen_UTC.isoformat(),
        'start_timestamp': localize(user_activity.first_seen_UTC, timezone).isoformat(),
        'end_timestamp_UTC': user_activity.last_seen_UTC.isoformat(),
        'end_timestamp': localize(user_activity.last_seen_UTC, timezone).isoformat(),
        'complete_days': 0,
        'incomplete_days': 0,
        'inactive_days': 0,
        'commute_time_work_s': 0,
        'commute_time_study_s': 0,
        'dwell_time_home_s': 0,
        'dwell_time_work_s': 0,
        'dwell_time_study_s': 0,
        'num_trips': 0,
        'total_trips_duration_s': 0,
        'total_trips_distance_m': 0,        
        'avg_trips_per_day': 0,
        'avg_trip_distance_m': 0
    }

    # tally days by complete or incomplete
    for summary in day_summaries:
        if summary.has_trips:
            if summary.is_complete:
                tallies['complete_days'] += 1
            else:
                tallies['incomplete_days'] += 1
        else:
            tallies['inactive_days'] += 1

    # tally commute durations
    commutes = _tally_commutes_all(user_activity)
    tallies['commute_time_work_s'] = commutes.get('work')
    tallies['commute_time_study_s'] = commutes.get('study')
    # tally dwell durations (time spent staying at a semantic location)
    dwells = _tally_dwells_all(user_activity)
    tallies['dwell_time_home_s'] = dwells.get('home')
    tallies['dwell_time_work_s'] = dwells.get('work')
    tallies['dwell_time_study_s'] = dwells.get('study')
    # sums
    tallies['num_trips'] = len(user_activity.commute_times)
    tallies['total_trips_duration_s'] = commutes['total']
    tallies['total_trips_distance_m'] = sum(dist for _, dist in user_activity.distances)
    # avgs
    active_days = tallies['complete_days'] + tallies['incomplete_days']
    tallies['avg_trips_per_day'] = tallies['num_trips'] / active_days
    tallies['avg_trip_distance_m'] = tallies['total_trips_distance_m'] / tallies['num_trips']
    return tallies


def summarize_full(user_activity, day_summaries, timezone):
    pass


def run(user, locations=None, proximity_m=50):
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
