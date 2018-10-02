#!/usr/bin/env python
# Kyle Fitzsimmons, 2015-2018
import itertools
import logging
import math
import utm

from .models import GPSPoint, SubwayEntrance, MissingTrip, TripSegment, Trip

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


## cast input data as objects
def generate_subway_entrances(coordinates):
    """
    Find UTM coordinates for subway stations entrances from lat/lon
    and yield objects.
    """
    entrances = []
    for c in coordinates:
        easting, northing, _, _ = utm.from_latlon(c.latitude, c.longitude)
        entrances.append(SubwayEntrance(latitude=c.latitude,
                                        longitude=c.longitude,
                                        northing=northing,
                                        easting=easting))
    return entrances

def generate_gps_points(coordinates):
    """
    Find UTM coordinates for user GPS points from lat/lon
    and yield objects.
    """
    for c in coordinates:
        easting, northing, _, _ = utm.from_latlon(c.latitude, c.longitude)
        yield GPSPoint(latitude=c.latitude,
                       longitude=c.longitude,
                       northing=northing,
                       easting=easting,
                       speed=c.speed,
                       h_accuracy=c.h_accuracy,
                       timestamp_UTC=c.timestamp_UTC)


## perform cleaning on points
def filter_by_accuracy(points, cutoff=30):
    """
    Remove points that have worse reported accuracy than the cutoff value
    in meters.
    """
    for p in points:
        if p.h_accuracy <= cutoff:
            yield p


def filter_erroneous_distance(points, check_speed_kph=60):
    """
    Remove points with unreasonably fast speeds where, in a series
    of 3 consecutive points (1, 2, and 3), point 3 is closer to point 1
    than point 2.
    """
    
    # create two copies of the points generator to compare against
    # and advance the copy ahead one point
    points, points_copy = itertools.tee(points)
    next(points_copy)

    last_p = None
    for p in points:
        next_p = next(points_copy)

        # always yield first point without filtering
        if not last_p:
            last_p = p
            yield p

        # find the distance and time passed since previous point was collected
        distance_from_last_point = distance_m(last_p, p)
        seconds_since_last_point = (p.timestamp_UTC - last_p.timestamp_UTC).total_seconds()

        # drop point if both speed and distance conditions are met
        if distance_from_last_point and seconds_since_last_point:
            kph_since_last_point = (distance_from_last_point / seconds_since_last_point) * 3.6
            distance_between_neighbor_points = distance_m(last_p,  next_p)
            
            if (kph_since_last_point >= check_speed_kph and 
                distance_between_neighbor_points < distance_from_last_point):
                    continue

        last_p = p
        yield p


def break_points_by_collection_pause(points, max_break_period=360):
    """
    Break into trip segments when time recorded between points is
    greater than the specified break period.
    """
    segments = []
    last_p = None
    for p in points:
        # determine break periods and increment segment groups
        if not last_p:
            break_period, group = 0, 0
        else:
            break_period = (p.timestamp_UTC - last_p.timestamp_UTC).total_seconds()
            if break_period > max_break_period:
                group += 1
        last_p = p

        # generate segments from determined groups
        p.period_before_seconds = break_period
        if segments and segments[-1].group == group:
            segments[-1].points.append(p)
        else:
            new_segment = TripSegment(group=group,
                                      period_before_seconds=break_period,
                                      points=[p])
            segments.append(new_segment)
    return segments


def initialize_trips(segments):
    """
    Begin trip contruction by creating a new trip for each segment.
    """
    trips = []
    for idx, segment in enumerate(segments):
        trips.append(Trip(num=idx, segments=[segment]))
    return trips


## stitch segments into longer trips if pre-determined conditions are met
def find_subway_connections(trips, subway_entrances, buffer_m=200):
    """
    Look for segments that can be connected by an explained subway trip update
    the related trip objects.
    """
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
        
        if end_entrance and start_entrance:
            interval = start_point.timestamp_UTC - end_point.timestamp_UTC
            subway_distance = distance_m(end_point, start_point)
            segment_speed = subway_distance / interval.total_seconds()
            if interval.total_seconds() < 4800 and segment_speed > 0.1:  # 80 minutes * seconds, m/s
                last_trip.link_to(trip, 'subway')
            else:
                connected_trips.append(trip)
        else:
            connected_trips.append(trip)
        last_trip = trip
    return connected_trips


def find_velocity_connections(trips):
    def _is_gte_walking_speed(p1, p2, period):
        minimum_walking_speed = 15. * 1000 / 3600  # 15 kph * 1000m / 1hr = m/s
        interpolated_speed = (distance_m(p1, p2) / period)
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
        else:
            connected_trips.append(trip)
        last_trip = trip
    return connected_trips


def filter_single_points(trips):
    """
    Remove any isolated GPS points that are not within 20 minutes
    or 150 meters of the previous end point or next trip start point.
    """
    max_break_period = 20 * 60  # minutes * seconds
    max_distance_m = 150

    filtered_trips = []
    for idx, trip in enumerate(trips):
        if len(trip.segments) == 1 and len(trip.segments[0].points) == 1:
            segment = trip.segments[0]
            point = segment.points[0]
            prev_trip_exists = idx - 1 >= 0
            next_trip_exists = idx + 1 < len(trips)

            is_prev_trip_candidate, is_next_trip_candidate = False, False
            if prev_trip_exists:
                prev_trip = trips[idx - 1]
                interval_prev_trip = (point.timestamp_UTC - prev_trip.last_segment.end.timestamp_UTC).total_seconds()
                distance_prev_trip = distance_m(prev_trip.last_segment.end, point)
                is_prev_trip_candidate = all([interval_prev_trip <= max_break_period,
                                              distance_prev_trip <= max_distance_m])
            if next_trip_exists:
                next_trip = trips[idx + 1]
                interval_next_trip = (next_trip.first_segment.start.timestamp_UTC - point.timestamp_UTC).total_seconds()
                distance_next_trip = distance_m(point, next_trip.first_segment.start)
                is_next_trip_candidate = all([interval_next_trip <= max_break_period,
                                              distance_next_trip <= max_distance_m])
            
            append_to_prev_trip = all([is_prev_trip_candidate,
                                       is_next_trip_candidate,
                                       distance_prev_trip <= distance_next_trip])
            append_to_prev_trip = append_to_prev_trip is False and is_prev_trip_candidate
            if append_to_prev_trip:
                point.timestamp_UTC = prev_trip.last_segment.end.timestamp_UTC
                filtered_trips[-1].segments.append(segment)
            elif is_next_trip_candidate:
                point.timestamp_UTC = next_trip.first_segment.start.timestamp_UTC
                next_trip.segments.insert(0, segment)
            else:
                pass  # assume point is noise and do nothing
        else:
            filtered_trips.append(trip)
    return filtered_trips


def infer_missing_trips(trips, subway_entrances, min_trip_m=250, subway_buffer_m=200, cold_start_m=750):
    """
    Determines where the gap between known trips is unexplained and missing
    trip information in the source data can be assumed.
    """
    missing_trips = []

    last_trip = None
    for trip in trips:
        if not last_trip:
            last_trip = trip
            continue

        last_end_point = last_trip.last_segment.end
        start_point = trip.first_segment.start
        distance_prev_trip = distance_m(last_end_point, start_point)
        interval_prev_trip = (start_point.timestamp_UTC - last_end_point.timestamp_UTC).total_seconds()

        if not distance_prev_trip:
            continue

        # 1. label any non-zero distance less than min trip lenghth as missing but too short
        if distance_prev_trip and distance_prev_trip < min_trip_m:
            m = MissingTrip(category='lt_min_trip_length',
                            last_trip_end=last_end_point,
                            next_trip_start=start_point,
                            distance=distance_prev_trip,
                            duration=interval_prev_trip)
            missing_trips.append(m)
        else:
            # 2. check for missing trips that can be explained by a subway trip with loss of signal
            end_entrance = points_intersect(subway_entrances, last_end_point, subway_buffer_m)
            start_entrance = points_intersect(subway_entrances, start_point, subway_buffer_m)
            if end_entrance and start_entrance and end_entrance != start_entrance:
                m = MissingTrip(category='subway',
                                last_trip_end=last_end_point,
                                last_trip_start=start_point,
                                distance=distance_prev_trip,
                                duration=interval_prev_trip)
                missing_trips.append(m)
            # 3. check for missing trips that are explained by the GPS warm-up time and
            #    prepend the last point of previous trip to start of current trip. This new
            #    point will have the same timestamp as the original first (now second) point
            elif distance_prev_trip <= cold_start_m:
                print('test this copy that attributes are not changed simultaneously')
                cold_start_point = last_end_point.copy()
                trip.first_segment.is_cold_start = True
                trip.first_segment.insert(0, cold_start_point)
            # 4. all other gaps in the data marked as a general missing trip
            else:
                m = MissingTrip(category='general',
                                next_trip_end=last_end_point,
                                next_trip_start=start_point,
                                distance=distance_prev_trip,
                                duration=interval_prev_trip)
                missing_trips.append(m)
            last_trip = trip
        return missing_trips

def format_trips_as_point_rows(trips, missing_trips):
    """
    Merge detected and missing trip datas to single set of points as rows.
    """
    rows = []
    missing_trips_gen = iter(missing_trips)
    next_missing_trip = next(missing_trips_gen)
    for trip_num, trip in enumerate(trips, start=1):
        if next_missing_trip.timestamp_UTC < trip.first_segment.start.timestamp_UTC:
            # insert a point to indicate missing trip
            missing_trip_row = {
                'timestamp_UTC': next_missing_trip.timestamp_UTC,
                'duration': next_missing_trip.duration,
                'distance_': next_missing_trip.distance,
                'trip_num': None,
                'segment_num': None,
                'missing': True,
                'missing_category': next_missing_trip.category,
                'has_cold_start': None,
                'latitude': next_missing_trip.last_trip_end.latitude,
                'longitude': next_missing_trip.last_trip_end.longitude
            }
            rows.append(missing_trip_row)
        
        # format trips to rows as normal (first checking whether tr)
        for segment in trip.segments:
            for point in segment.points:
                trip_row = {
                    'timestamp_UTC': point.timestamp_UTC,
                    'duration': None,
                    'distance': None,
                    'trip_num': trip_num,
                    'segment_num': segment.group,
                    'missing': None,
                    'missing_category': None,
                    'has_cold_start': segment.is_cold_start if segment.is_cold_start else None,
                    'latitude': point.latitude,
                    'longitude': point.longitude
                }
                rows.append(trip_row)
    return rows


## helper functions
def distance_m(point1, point2):
    """
    Returns the distance between two points in meters.
    """
    a = point2.easting - point1.easting
    b = point2.northing - point1.northing
    return math.sqrt(a**2 + b**2)

def points_intersect(points, test_point, buffer_m=200):
    """
    Returns the first point that intersects with buffer (m) of a test point.
    """
    for point in points:
        if distance_m(point, test_point) <= buffer_m:
            return point




## main
def run(coordinates, parameters):
    # process points as structs and cast position from lat/lng to UTM    
    subway_entrances = generate_subway_entrances(parameters['subway_entrances'])
    gps_points = generate_gps_points(coordinates)

    # clean noisy and duplicate points
    high_accuracy_points = filter_by_accuracy(gps_points, cutoff=parameters['accuracy_cutoff_meters'])
    cleaned_points = filter_erroneous_distance(high_accuracy_points, check_speed_kph=60)

    # break trips into atomic trip segments
    segments = break_points_by_collection_pause(cleaned_points, max_break_period=parameters['break_interval_seconds'])

    # start by considering every segment a trip
    trips = initialize_trips(segments)

    # apply rules to reconstitute full trips from segments when possible ("stitching")
    subway_linked_trips = find_subway_connections(trips, subway_entrances,
                                                  buffer_m=parameters['subway_buffer_meters'])
    velocity_linked_trips = find_velocity_connections(subway_linked_trips)
    full_length_trips = filter_single_points(velocity_linked_trips)

    # find incidents where data about trips is missing
    missing_trips = infer_missing_trips(trips, subway_entrances,
                                        min_trip_m=250,
                                        subway_buffer_m=parameters['subway_buffer_meters'],
                                        cold_start_m=parameters['cold_start_distance'])

    csv_rows = format_trips_as_point_rows(full_length_trips, missing_trips)

    logger.info('-------------------------------')
    logger.info('V2 - Num. segments: %d', len(segments))
    logger.info('V2 - Num. subway linked trips: %d', len(subway_linked_trips))
    logger.info('V2 - Num. velocity linked trips: %d', len(velocity_linked_trips))
    logger.info('V2 - Num. full-length trips: %d', len(full_length_trips))
    logger.info('V2 - Num. missing trips: %d', len(missing_trips))
    logger.info('V2 - Num. csv rows: %d', len(csv_rows))
    return segments

