#!/usr/bin/env python
# Kyle Fitzsimmons, 2015-2019
import copy
import itertools
import logging
import math
from shapely.geometry import Point, LineString
import utm

from tripkit.models import Trip as LibraryTrip, TripPoint as LibraryTripPoint
from .models import GPSPoint, SubwayEntrance, SubwayRoute, MissingTrip, TripSegment, Trip
from .trip_codes import TRIP_CODES


logger = logging.getLogger('itinerum-tripkit.process.trip_detection.triplab.v2')


# cast input data as objects
def generate_subway_entrances(coordinates, feature_cache=None):
    '''
    Find UTM coordinates for subway stations entrances from lat/lon and yield objects.
    '''
    if feature_cache:
        entrances = feature_cache.get(['subway_entrances', 'algo.v2'])
        if entrances:
            return entrances
    entrances = []
    for c in coordinates:
        easting, northing, _, _ = utm.from_latlon(c.latitude, c.longitude)
        entrances.append(SubwayEntrance(latitude=c.latitude, longitude=c.longitude, northing=northing, easting=easting))
    feature_cache.set(['subway_entrances', 'algo.v2'], entrances)
    return entrances


def generate_subway_routes(route_coordinates, feature_cache=None):
    ''' 
    Find UTM coordinates for subway routes from lat/lon and yield LineString shape objects.
    '''
    if feature_cache:
        routes = feature_cache.get(['subway_routes', 'algo.v2'])
        if routes:
            return routes
    routes = []
    for r in route_coordinates:
        coordinates_utm = []
        for c in r.coordinates:
            easting, northing, _, _ = utm.from_latlon(c.latitude, c.longitude)
            coordinates_utm.append((easting, northing))
        routes.append(
            SubwayRoute(route_id=r.route_id,
                        coordinates=r.coordinates,
                        coordinates_utm=coordinates_utm,
                        linestring_utm=LineString(coordinates_utm)))
    feature_cache.set(['subway_routes', 'algo.v2'], routes)
    return routes


def generate_gps_points(coordinates):
    '''
    Find UTM coordinates for user GPS points from lat/lon and yield objects.
    '''
    for c in coordinates:
        easting, northing, _, _ = utm.from_latlon(c.latitude, c.longitude)
        yield GPSPoint(
            database_id=c.id,
            latitude=c.latitude,
            longitude=c.longitude,
            northing=northing,
            easting=easting,
            speed=c.speed,
            h_accuracy=c.h_accuracy,
            timestamp_UTC=c.timestamp_UTC,
        )


# perform cleaning on points
def filter_by_accuracy(points, cutoff=30):
    '''
    Remove points that have worse reported accuracy than the cutoff value in meters.
    '''
    for p in points:
        if p.h_accuracy <= cutoff:
            yield p


def filter_erroneous_distance(points, check_speed_kph=60):
    '''
    Remove points with unreasonably fast speeds where, in a series of 3 consecutive points (1, 2, and 3),
    point 3 is closer to point 1 than point 2.
    '''

    # create two copies of the points generator to compare against
    # and advance the copy ahead one point
    points, points_copy = itertools.tee(points)
    next(points_copy)

    last_p = None
    for p in points:
        try:
            next_p = next(points_copy)
        except StopIteration:
            yield p
            return

        # always yield first point without filtering
        if not last_p:
            last_p = p
            yield p
            continue

        # find the distance and time passed since previous point was collected
        distance_from_last_point = distance_m(last_p, p)
        seconds_since_last_point = (p.timestamp_UTC - last_p.timestamp_UTC).total_seconds()

        # drop point if both speed and distance conditions are met
        if distance_from_last_point and seconds_since_last_point:
            kph_since_last_point = (distance_from_last_point / seconds_since_last_point) * 3.6
            distance_between_neighbor_points = distance_m(last_p, next_p)

            if kph_since_last_point >= check_speed_kph and distance_between_neighbor_points < distance_from_last_point:
                continue

        last_p = p
        yield p


def break_points_by_collection_pause(points, max_break_period=360):
    '''
    Break into trip segments when time recorded between points is greater than the specified break period.
    '''
    def _break_points(points, max_break_period):
        segments = []
        last_p = None
        for p in points:
            # determine break period & distance and increment segment groups
            if not last_p:
                break_period, break_distance, group = 0, 0.0, 0
            else:
                break_period = (p.timestamp_UTC - last_p.timestamp_UTC).total_seconds()
                break_distance = distance_m(last_p, p)
                if break_period > max_break_period:
                    group += 1
            last_p = p
            p.period_before_seconds = break_period
            p.distance_before_meters = break_distance

            # generate segments from determined groups
            if segments and segments[-1].group == group:
                segments[-1].points.append(p)
            else:
                new_segment = TripSegment(group=group, period_before_seconds=break_period, points=[p])
                segments.append(new_segment)
        return segments
    
    # gracefully handle pre-processers filtering all points
    try:
        return _break_points(points, max_break_period)
    except RuntimeError:
        return []


def initialize_trips(segments):
    '''
    Begin trip contruction by creating a new trip for each segment.
    '''
    trips = []
    for idx, segment in enumerate(segments):
        trips.append(Trip(num=idx, segments=[segment]))
    return trips


# stitch segments into longer trips if pre-determined conditions are met
def find_subway_connections(trips, subway_entrances, subway_routes, buffer_m=200):
    '''
    Look for segments that can be connected by an explained subway trip update the related trip objects.
    '''
    connected_trips = []
    last_trip = None
    for trip in trips:
        if not last_trip:
            connected_trips.append(trip)
            last_trip = trip
            continue

        # Test whether the last point of the last segment and the first point
        # of the current segment intersect two different subway station entrances.
        end_point = last_trip.last_segment.end
        start_point = trip.first_segment.start
        end_entrance = points_intersect(subway_entrances, end_point, buffer_m)
        start_entrance = points_intersect(subway_entrances, start_point, buffer_m)

        # Test whether subway trip is a similar match to subway network
        # if end_entrance and start_entrance:
        #     error = 0
        #     candidates = {}
        #     for r in subway_routes:
        #         candidates[r.route_id] = 0
        #         for s in trip.segments:
        #             for p in s.points:
        #                 candidates[r.route_id] += Point(p.easting, p.northing).distance(r.linestring_utm)
        #     print(candidates)
        #     print(trip.segments)
        #     for p in trip.points:
        #         print(p)
        #     print('hello')

        if end_entrance and start_entrance:
            interval = start_point.timestamp_UTC - end_point.timestamp_UTC
            subway_distance = distance_m(end_point, start_point)
            segment_speed = subway_distance / interval.total_seconds()
            if interval.total_seconds() < 4800 and segment_speed > 0.1:  # 80 minutes * seconds, m/s
                last_trip.link_to(trip, 'subway')
                # NOTE: adjust this to `last_trip = last_trip` to connect more
                # possible subway segments consecutively, however, this can
                # lead to long transfers being lumped as part of a trip where
                # it is probably clearer to keep these as two different trips.
                last_trip = None
                continue
            else:
                connected_trips.append(trip)
        else:
            connected_trips.append(trip)
        last_trip = trip
    return connected_trips


def find_velocity_connections(trips):
    def _is_gte_walking_speed(p1, p2, period):
        minimum_walking_speed = 15.0 * 1000 / 3600  # 15 kph * 1000m / 1hr = m/s
        interpolated_speed = distance_m(p1, p2) / period
        return interpolated_speed >= minimum_walking_speed

    connected_trips = []
    last_trip = None
    for trip in trips:
        if not last_trip:
            connected_trips.append(trip)
            last_trip = trip
            continue

        end_point = last_trip.last_segment.end
        start_point = trip.first_segment.start
        interval = start_point.timestamp_UTC - end_point.timestamp_UTC
        period = int(interval.total_seconds())
        if _is_gte_walking_speed(end_point, start_point, period):
            last_trip.link_to(trip, 'walking')
            last_trip = None
        else:
            connected_trips.append(trip)
            last_trip = trip
    return connected_trips


def filter_single_points(trips, user_locations=None):
    '''
    Remove any isolated GPS points that are not within 20 minutes or 150 meters of the previous end point
    or next trip start point. Otherwise, attach them to the soonest trip end.
    '''
    max_break_period = 20 * 60  # minutes * seconds
    max_distance_m = 150

    filtered_trips = []
    for idx, trip in enumerate(trips):
        if len(trip.segments) == 1 and len(trip.segments[0].points) == 1:
            segment = trip.segments[0]
            point = segment.points[0]
            prev_trip_exists = idx > 0
            next_trip_exists = idx + 1 < len(trips)

            is_prev_trip_candidate, is_next_trip_candidate = False, False
            if prev_trip_exists:
                prev_trip = trips[idx - 1]
                interval_prev_trip = (point.timestamp_UTC - prev_trip.last_segment.end.timestamp_UTC).total_seconds()
                distance_prev_trip = distance_m(prev_trip.last_segment.end, point)
                is_prev_trip_candidate = any(
                    [interval_prev_trip <= max_break_period, distance_prev_trip <= max_distance_m]
                )
            if next_trip_exists:
                next_trip = trips[idx + 1]
                interval_next_trip = (next_trip.first_segment.start.timestamp_UTC - point.timestamp_UTC).total_seconds()
                distance_next_trip = distance_m(point, next_trip.first_segment.start)
                is_next_trip_candidate = any(
                    [interval_next_trip <= max_break_period, distance_next_trip <= max_distance_m]
                )

            # group conditions for appending to previous trip in one boolen value
            append_to_prev_trip = (
                is_prev_trip_candidate and is_next_trip_candidate and interval_prev_trip <= interval_next_trip
            )
            if is_prev_trip_candidate and not is_next_trip_candidate:
                append_to_prev_trip = True

            # test whether single point is ping from a user location
            # e.g., battery dies, wakes up when charging, has an exceptionally long cold-start
            is_known_location_ping = False
            if user_locations:
                at_home = False
                if user_locations.home:
                    at_home = distance_m(user_locations.home, point) <= 150
                at_work = False
                if user_locations.work:
                    at_work = distance_m(user_locations.work, point) <= 150
                at_study = False
                if user_locations.study:                
                    at_study = distance_m(user_locations.study, point) <= 150
                is_known_location_ping = any([at_home, at_work, at_study])

            # connect point to previous or next trip, or keep individual as ping
            if append_to_prev_trip:
                point.timestamp_UTC = prev_trip.last_segment.end.timestamp_UTC
                filtered_trips[-1].segments.append(segment)
            elif is_next_trip_candidate:
                point.timestamp_UTC = next_trip.first_segment.start.timestamp_UTC
                next_trip.segments.insert(0, segment)
            elif is_known_location_ping:
                filtered_trips.append(trip)  # keep ping point for splitting into two missing trips
            else:
                pass  # assume point is noise and do nothing
        else:
            filtered_trips.append(trip)
    return filtered_trips


def infer_missing_trips(trips, subway_entrances, min_trip_m=250, subway_buffer_m=200, cold_start_m=750):
    '''
    Determines where the gap between known trips is unexplained and missing trip information
    in the source data can be assumed.
    '''
    missing_trips = []
    last_trip = None
    for idx, trip in enumerate(trips):
        if not last_trip:
            last_trip = trip
            continue

        last_end_point = last_trip.last_segment.end
        start_point = trip.first_segment.start
        distance_prev_trip = distance_m(last_end_point, start_point)
        interval_prev_trip = (start_point.timestamp_UTC - last_end_point.timestamp_UTC).total_seconds()

        if not distance_prev_trip:
            continue

        known_location_ping = all([len(trip.segments) == 1,
                                   len(trip.first_segment.points) == 1,
                                   len(trips) > idx + 1])

        # 1. label any non-zero distance less than min trip lenghth as missing but too short
        if distance_prev_trip and distance_prev_trip < min_trip_m:
            m = MissingTrip(
                category='lt_min_trip_length',
                last_trip_end=last_end_point,
                next_trip_start=start_point,
                distance=distance_prev_trip,
                duration=interval_prev_trip,
            )
            missing_trips.append(m)
        elif known_location_ping:
            

            next_start_point = trips[idx+1].first_segment.start
            m1 = MissingTrip(
                category='ping_known_location',
                last_trip_end=last_end_point,
                next_trip_start=start_point,
                distance=distance_prev_trip,
                duration=interval_prev_trip
            )
            m2 = MissingTrip(
                category='ping_known_location',
                last_trip_end=start_point,
                next_trip_start=next_start_point,
                distance=0,
                duration=0
            )
            missing_trips.append(m1)
            missing_trips.append(m2)
        else:
            # 2. check for missing trips that can be explained by a subway trip with loss of signal
            end_entrance = points_intersect(subway_entrances, last_end_point, subway_buffer_m)
            start_entrance = points_intersect(subway_entrances, start_point, subway_buffer_m)
            if end_entrance and start_entrance and end_entrance != start_entrance:
                m = MissingTrip(
                    category='subway',
                    last_trip_end=last_end_point,
                    next_trip_start=start_point,
                    distance=distance_prev_trip,
                    duration=interval_prev_trip,
                )
                missing_trips.append(m)
            # 3. check for missing trips that are explained by the GPS warm-up time and
            #    prepend the last point of previous trip to start of current trip. This new
            #    point will have the same timestamp as the original first (now second) point
            elif distance_prev_trip <= cold_start_m:
                # TODO: test that this copy's attributes are not changed simultaneously (shared with original)
                cold_start_point = copy.copy(last_end_point)
                trip.first_segment.is_cold_start = True
                trip.first_segment.prepend(cold_start_point)
            # 4. all other gaps in the data marked as a general missing trip
            else:
                m = MissingTrip(
                    category='general',
                    last_trip_end=last_end_point,
                    next_trip_start=start_point,
                    distance=distance_prev_trip,
                    duration=interval_prev_trip,
                )
                missing_trips.append(m)
        last_trip = trip
    return missing_trips


def merge_trips(complete_trips, missing_trips):
    '''
    Returns a zipped list of complete and missing trips in the correct timestamp order. If the missing
    trip previous to a complete trip is labeled as 'too short' (missing category: 'lt_min_trip_length'),
    then join these trips as one.
    '''
    if not missing_trips:
        return complete_trips

    merged = []
    missing_trips_gen = iter(missing_trips)
    next_missing_trip = next(missing_trips_gen)
    for trip in complete_trips:
        # keep track of 'too short' missing trips only if they are the last
        # missing trip before a complete one
        merge_missing_too_short = None
        if next_missing_trip and next_missing_trip.start.timestamp_UTC < trip.first_segment.start.timestamp_UTC:
            while next_missing_trip.start.timestamp_UTC < trip.first_segment.start.timestamp_UTC:
                if next_missing_trip.category == 'lt_min_trip_length':
                    merge_missing_too_short = next_missing_trip
                else:
                    # TODO: Is a 'too short' missing trip before a 'normal' missing trip
                    # a possible scenario? If so, how should this be handled?
                    merge_missing_too_short = None
                    merged.append(next_missing_trip)
                try:
                    next_missing_trip = next(missing_trips_gen)
                except StopIteration:
                    next_missing_trip = None
                    break

        if merge_missing_too_short:
            # merge segment with missing trip's start position but the original trip's starting timestamp
            segment_group = trip.first_segment.group + 0.1
            start_point = copy.copy(merge_missing_too_short.start)
            end_point = copy.copy(merge_missing_too_short.end)
            start_point.timestamp_UTC = end_point.timestamp_UTC

            missing_segment = TripSegment(
                group=segment_group,
                points=[start_point],
                period_before_seconds=trip.first_segment.period_before_seconds,
            )
            trip.segments.insert(0, missing_segment)
            trip.add_label('lt_min_trip_length')
        merged.append(trip)
    return merged


def annotate_trips(trips):
    '''
    Filters the labels attached to trips by the hierarchy of their relevance (e.g., 'missing trips' with
    too short of a length [actually a trip end] joined to a complete trip should be labelled as 'complete'
    instead of missing). Using the most appropriate label, set the integer trip code from the `trip_codes.py`
    lookup table.
    '''
    for trip in trips:
        if isinstance(trip, MissingTrip):
            if trip.category == 'lt_min_trip_length':
                trip.code = TRIP_CODES['missing trip - less than min. trip length']
            elif trip.category == 'subway':
                trip.code = TRIP_CODES['missing trip - subway']
            elif trip.category == 'ping_known_location':
                trip.code = TRIP_CODES['missing trip - known location ping']
            elif trip.category == 'general':
                trip.code = TRIP_CODES['missing trip']
        elif isinstance(trip, Trip):
            # add labels for each link where segments have been linked by rules
            for link_type in trip.links.keys():
                trip.add_label(link_type)

            # label detected trips consisting of one point
            if len(trip.segments) == 1 and len(trip.segments[0].points) == 1:
                trip.add_label('single point')
            elif trip.cumulative_distance == 0:
                trip.add_label('single point')

            # apply labeling hierarchy to determine final trip code
            if trip.cumulative_distance() < 250:
                trip.code = TRIP_CODES['distance too short']
            elif 'lt_min_trip_length' in trip.labels:
                if 'subway' in trip.labels:
                    trip.code = TRIP_CODES['complete trip - subway']
                elif 'single point' in trip.labels:
                    trip.code = TRIP_CODES['single point']
                else:
                    trip.code = TRIP_CODES['complete trip']
            else:
                if 'subway' in trip.labels:
                    trip.code = TRIP_CODES['complete trip - subway']
                elif not trip.labels:
                    trip.code = TRIP_CODES['complete trip']
        yield trip


# helper functions
def distance_m(point1, point2):
    '''
    Returns the distance between two points in meters.
    '''
    a = point2.easting - point1.easting
    b = point2.northing - point1.northing
    return math.sqrt(a ** 2 + b ** 2)


def points_intersect(points, test_point, buffer_m=200):
    '''
    Returns the first point that intersects with buffer (m) of a test point.
    '''
    for point in points:
        if distance_m(point, test_point) <= buffer_m:
            return point


def wrap_for_tripkit(detected_trips, include_segments=False):
    '''
    Return result as the same type of object (list of TripPoints) as returned by `tripkit.database`.
    '''
    tripkit_trips = []
    for trip_num, detected_trip in enumerate(detected_trips, start=1):
        if isinstance(detected_trip, Trip):
            trip = LibraryTrip(num=trip_num, trip_code=detected_trip.code)
            trip_distance = 0.0
            for segment in detected_trip.segments:
                for point in segment.points:
                    trip_distance += point.distance_before_meters
                    p = LibraryTripPoint(
                        database_id=point.database_id,
                        latitude=point.latitude,
                        longitude=point.longitude,
                        h_accuracy=point.h_accuracy,
                        distance_before=point.distance_before_meters,
                        trip_distance=trip_distance,
                        period_before=point.period_before_seconds,
                        timestamp_UTC=point.timestamp_UTC,
                    )
                    trip.points.append(p)
            if include_segments:
                trip.segments = detected_trip.segments
            tripkit_trips.append(trip)
        elif isinstance(detected_trip, MissingTrip):
            trip = LibraryTrip(num=trip_num, trip_code=detected_trip.code)
            p1 = LibraryTripPoint(
                database_id=None,
                latitude=detected_trip.start.latitude,
                longitude=detected_trip.start.longitude,
                h_accuracy=-1.0,
                distance_before=0.0,
                trip_distance=0.0,
                period_before=0.0,
                timestamp_UTC=detected_trip.start.timestamp_UTC,
            )
            p2 = LibraryTripPoint(
                database_id=None,
                latitude=detected_trip.end.latitude,
                longitude=detected_trip.end.longitude,
                h_accuracy=-1.0,
                distance_before=detected_trip.distance,
                trip_distance=detected_trip.distance,
                period_before=detected_trip.duration,
                timestamp_UTC=detected_trip.end.timestamp_UTC,
            )
            trip.points = [p1, p2]
            if include_segments:
                trip.segments = []
            tripkit_trips.append(trip)
    return tripkit_trips


# main
# @profile
def run(coordinates, parameters, user_locations=None, include_segments=False, feature_cache=None):
    if not coordinates or len(coordinates) < 2:
        return []

    # process points as structs and cast position from lat/lng to UTM
    subway_entrances = generate_subway_entrances(parameters['subway_entrances'], feature_cache)
    subway_routes = generate_subway_routes(parameters['subway_routes'], feature_cache)
    gps_points = generate_gps_points(coordinates)

    # clean noisy and duplicate points
    high_accuracy_points = filter_by_accuracy(gps_points, cutoff=parameters['accuracy_cutoff_meters'])
    cleaned_points = filter_erroneous_distance(high_accuracy_points, check_speed_kph=100)

    # break trips into atomic trip segments
    segments = break_points_by_collection_pause(cleaned_points, max_break_period=parameters['break_interval_seconds'])

    # start by considering every segment a trip
    initial_trips = initialize_trips(segments)

    # apply rules to reconstitute full trips from segments when possible ('stitching')
    subway_linked_trips = find_subway_connections(
        initial_trips, subway_entrances, subway_routes, buffer_m=parameters['subway_buffer_meters']
    )
    velocity_linked_trips = find_velocity_connections(subway_linked_trips)
    full_length_trips = filter_single_points(velocity_linked_trips, user_locations=user_locations)

    # find incidents where data about trips is missing
    missing_trips = infer_missing_trips(
        full_length_trips,
        subway_entrances,
        min_trip_m=250,
        subway_buffer_m=parameters['subway_buffer_meters'],
        cold_start_m=parameters['cold_start_distance']
    )

    trips = merge_trips(full_length_trips, missing_trips)
    tripkit_trips = wrap_for_tripkit(annotate_trips(trips), include_segments)

    logger.info("-------------------------------")
    logger.info("Num. segments: %d", len(segments))
    logger.info("Num. trips (w/ subway links): %d", len(subway_linked_trips))
    logger.info("Num. trips (w/ velocity links): %d", len(velocity_linked_trips))
    logger.info("Num. full-length trips: %d", len(full_length_trips))
    logger.info("Num. missing trips: %d", len(missing_trips))
    logger.info("Num. point rows: %d", sum([len(t.points) for t in tripkit_trips]))
    return tripkit_trips
