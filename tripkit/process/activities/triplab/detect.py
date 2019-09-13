#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import itertools
import logging

from geopy.distance import distance
import pytz

from .models import UserActivity


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


def tally_stay_times(locations, trip):
    '''
    Count the time spent at known locations by tallying the intervals between labeled points.

    :param dict locations:       Dictionary of semantic locations with name and list of [lat, lon]
    :param `py:class:Trip` trip: An itinerum-tripkit trip object
    '''
    stay_times = {}
    last_p = None
    for p in trip.points:
        if not last_p:
            last_p = p
        if p.label:
            stay_times.setdefault(p.label, 0)
            stay_times[p.label] += (p.timestamp_UTC - last_p.timestamp_UTC).total_seconds()
    return stay_times


def tally_commute(trip):
    '''
    Count the time spent commuting between either home and work or home and study.

    :param `py:class:Trip` trip: An itinerum-tripkit trip object
    '''
    commute_times = {'work': 0.0, 'study': 0.0}
    if trip.start.label == 'home':
        if trip.end.label == 'work':
            commute_times['work'] += (trip.end.timestamp_UTC - trip.start.timestamp_UTC).total_seconds()
        elif trip.end.label == 'study':
            commute_times['study'] += (trip.end.timestamp_UTC - trip.start.timestamp_UTC).total_seconds()
    elif trip.start.label == 'work' and trip.end.label == 'home':
        commute_times['work'] += (trip.end.timestamp_UTC - trip.start.timestamp_UTC).total_seconds()
    elif trip.start.label == 'study' and trip.end.label == 'home':
        commute_times['study'] += (trip.end.timestamp_UTC - trip.start.timestamp_UTC).total_seconds()
    return commute_times


def run(user, locations=None, proximity_m=50, timezone=None):
    logger.info(f"Tallying semantic location dwell times for {user.uuid}...")
    if not user.trips:
        logger.info(f"No trips available.")
        return

    if not locations:
        logger.info("No activity locations provided.")
        return
    detect_semantic_location_overlap(user.uuid, locations, proximity_m)

    activity = UserActivity(user.uuid, start_time=user.trips[0].start_UTC, end_time=user.trips[-1].end_UTC)

    # tally distances and durations for semantic locations and as an aggregate of all trips
    for t in user.trips:
        label_trip_points(locations, t, proximity_m)
        stay_times = tally_stay_times(locations, t)
        for name, duration in stay_times.items():
            activity.stay_times.setdefault(name, 0)
            activity.stay_times[name] += duration
        commute_times = tally_commute(t)
        for name, duration in commute_times.items():
            activity.commute_times.setdefault(name, 0)
            activity.commute_times[name] += duration
        if t.trip_code < 100:
            activity.num_trips += 1
            activity.total_trips_distance += t.distance
            activity.total_trips_duration += (t.end_UTC - t.start_UTC).total_seconds()
    # gather complete days statistics
    for day_summary in user.detected_trip_day_summaries:
        if day_summary.has_trips:
            if day_summary.is_complete:
                activity.complete_days += 1
            else:
                activity.incomplete_days += 1
        else:
            activity.inactive_days += 1

    activity_record = activity.as_dict()
    if timezone:
        tz = pytz.timezone(timezone)
        activity_record['start_timestamp'] = pytz.utc.localize(activity.start_time).astimezone(tz).isoformat()
        activity_record['end_timestamp'] = pytz.utc.localize(activity.end_time).astimezone(tz).isoformat()
    return activity_record
