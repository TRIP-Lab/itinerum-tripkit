#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import itertools
import logging

from geopy.distance import distance

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def generate_locations(location_columns, survey_response):
    """
    Generates the dictionary object for passing to `activities.triplab.detect.run` with
    the labeled location as the key and list of [latitude, longitude] as the value.

    :param dict columns:         A dictionary object with the location label as the key and
                                 and a list of the survey response column names for latitude
                                 and longitude.
    :param dict survey_response: A dictionary object with a user's survey response information
                                 including semantic location coordinates.
    """
    locations = {}
    for label, columns in location_columns.items():
        lat_col, lon_col = columns
        lat, lon = survey_response[lat_col], survey_response[lon_col]
        if lat and lon:
            locations[label] = [survey_response[lat_col], survey_response[lon_col]]
    return locations


def detect_semantic_location_overlap(locations, activity_proximity_m):
    for loc1, loc2 in itertools.combinations(locations, 2):
        distance_between_m = distance(locations[loc1], locations[loc2]).meters
        if distance_between_m <= (activity_proximity_m * 2):
            logger.warn(f"possible overlap in semantic locations: {loc1}-->{loc2} ({distance_between_m} m)")


def label_by_proximity(locations, c, activity_proximity_m):
    for name, location in locations.items():
        delta_m = distance((c.latitude, c.longitude), (location.latitude, location.longitude)).meters
        if delta_m <= activity_proximity_m:
            c.semantic_location = name


def label_trip_points(locations, trip, proximity_m):
    for p in trip.points:
        for label, location in locations.items():
            if distance([p.latitude, p.longitude], location).meters <= proximity_m:
                p.label = label
                continue
            p.label = None
    print(trip.start.label, trip.end.label)


def run(trips, locations=None, proximity_m=30):
    if not locations:
        print("No activity locations to detect.")
        return
    detect_semantic_location_overlap(locations, proximity_m)

    for t in trips:
        label_trip_points(locations, t, proximity_m)

    # start_time = coordinates[0].timestamp_UTC
    # end_time = coordinates[-1].timestamp_UTC

    # print(start_time, end_time)
    # # last_c = None
    # for c in coordinates:
    #     # if not last_c:
    #     #     last_c = c
    #     # delta_m = distance((c.latitude, c.longitude),
    #     #                    (last_c.latitude, last_c.longitude)).meters
    #     label_by_proximity(locations, c)
    #     # last_c = c
    #     assert abs(c.latitude) > 0.01 and abs(c.longitude) > 0.01

    # total_labeled = 0
    # for key, values in labeled_coordinates.items():
    #     total_labeled += len(values)
    # print(total_labeled)
    # print(len(coordinates))
