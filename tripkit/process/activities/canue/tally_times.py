#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import itertools
import logging

from .models import UserActivity

from tripkit.utils import geo

logger = logging.getLogger('itinerum-tripkit.process.activities.canue.tally_times')


# check whether two activity locations could be detected for the same coordinates
def detect_activity_location_overlap(uuid, locations, activity_proximity_m):
    for loc1, loc2 in itertools.combinations(locations, 2):
        distance_between_m = geo.distance_m(loc1, loc2)
        if distance_between_m <= (activity_proximity_m * 2):
            logger.warn(
                f"possible overlap in activity locations: {uuid} {loc1.label}-->{loc2.label} ({distance_between_m} m)"
            )


def label_trip_points(locations, trip, proximity_m):
    for p in trip.points:
        p.label = None
        for location in locations:
            if geo.haversine_distance_m(p, location) <= proximity_m:
                p.label = location.label
                continue


def classify_dwell(last_trip, trip):
    '''
    Count the time spent at known locations by tallying the intervals between labeled points.

    :param `py:class:Trip` last_trip: An itinerum-tripkit trip object for the trip immediately prior to the provided `trip`
    :param `py:class:Trip` trip:      An itinerum-tripkit trip object
    '''
    # test for activity location in last 5 points of previous trip and first 5 points of next trip
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
    return 'uncategorized'


def classify_commute(trip):
    if trip.start.label and trip.end.label:
        commute_label = '-'.join(sorted([trip.start.label, trip.end.label]))
        return commute_label
    else:
        return 'uncategorized'


def run(user, locations, proximity_m=50):
    logger.info(f"Tallying activity location dwell times for {user.uuid}...")
    if not user.trips:
        logger.info(f"No trips available.")
        return
    if not locations:
        logger.info("No activity locations provided.")
        return
    detect_activity_location_overlap(user.uuid, locations, proximity_m)

    activity = UserActivity(user.uuid)
    last_t = None
    for t in user.trips:
        label_trip_points(locations, t, proximity_m)

        # classify commute times for trips occuring between activity locations
        commute_label = classify_commute(t)
        activity.add_commute_time(t.start_UTC, t.end_UTC, commute_label)

        # classify dwell times for stays at the same activity location between two consecutive trips
        if last_t:
            dwell_label = classify_dwell(last_t, t)
            activity.add_dwell_time(last_t.end_UTC, t.start_UTC, dwell_label)
        last_t = t

        activity.add_trip(t)
    return activity
