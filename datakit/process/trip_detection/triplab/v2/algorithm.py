#!/usr/bin/env python
# Kyle Fitzsimmons, 2015-2018
import itertools
import math
import utm


## algorithm data structures
# use slots to achieve best performance (comparable to dictionary)
# and provide immutability against add or removing attributes
class GPSPoint:
    __slots__ = ['latitude', 'longitude', 'northing', 'easting',
                 'speed', 'h_accuracy', 'timestamp_UTC', 'period_before_seconds']

    def __init__(self, *args, **kwargs):
        # input attributes
        self.latitude = kwargs['latitude']
        self.longitude = kwargs['longitude']
        self.northing = kwargs['northing']
        self.easting = kwargs['easting']
        self.speed = kwargs['speed']
        self.h_accuracy = kwargs['h_accuracy']
        self.timestamp_UTC = kwargs['timestamp_UTC']

        # trip attributes
        self.period_before_seconds = kwargs.get('period_before_seconds')


class SubwayEntrance:
    __slots__ = ['latitude', 'longitude', 'northing', 'easting']

    def __init__(self, *args, **kwargs):
        self.latitude = kwargs['latitude']
        self.longitude = kwargs['longitude']
        self.northing = kwargs['northing']
        self.easting = kwargs['easting']        


class TripSegment:
    __slots__ = ['group', 'points', 'period_before_seconds']

    def __init__(self, *args, **kwargs):
        self.group = kwargs['group']
        self.points = kwargs['points']
        self.period_before_seconds = kwargs['period_before_seconds']


class Trip:
    __slots__ = ['num', 'segments']

    def __init__(self, *args, **kwargs):
        self.num = kwargs['num']
        self.segments = kwargs['segments']


## cast input data as objects
def generate_subway_entrances(coordinates):
    '''Find UTM coordinates for subway stations entrances from lat/lon
       and build structs'''
    for c in coordinates:
        northing, easting, _, _ = utm.from_latlon(c.latitude, c.longitude)
        yield SubwayEntrance(latitude=c.latitude,
                             longitude=c.longitude,
                             northing=northing,
                             easting=easting)

def generate_gps_points(coordinates):
    '''Find UTM coordinates for user GPS points from lat/lon
       and build structs'''
    for c in coordinates:
        northing, easting, _, _ = utm.from_latlon(c.latitude, c.longitude)
        yield GPSPoint(latitude=c.latitude,
                       longitude=c.longitude,
                       northing=northing,
                       easting=easting,
                       speed=c.speed,
                       h_accuracy=c.h_accuracy,
                       timestamp_UTC=c.timestamp_UTC)


## perform cleaning on points
def filter_by_accuracy(points, cutoff=30):
    '''Remove points that have worse reported accuracy than the
       cutoff value in meters'''
    for p in points:
        if p.h_accuracy <= cutoff:
            yield p


def filter_erroneous_distance(points, check_speed_kph=60):
    '''Remove points with unreasonably fast speeds where, in a series
       of 3 consecutive points (1, 2, and 3), point 3 is closer to point 1
       than point 2'''
    
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
        distance_from_last_point = euclidean_distance(last_p, p)
        seconds_since_last_point = (p.timestamp_UTC - last_p.timestamp_UTC).total_seconds()

        # drop point if both speed and distance conditions are met
        if distance_from_last_point and seconds_since_last_point:
            kph_since_last_point = (distance_from_last_point / seconds_since_last_point) * 3.6
            distance_between_neighbor_points = euclidean_distance(last_p,  next_p)
            
            if (kph_since_last_point >= check_speed_kph and 
                distance_between_neighbor_points < distance_from_last_point):
                    continue

        last_p = p
        yield p

## break trips into atomic segments
def break_by_collection_pause(points, break_period=360):
    '''Break into trip segments when time recorded between points is
       greater than the specified break period'''
    segments = []
    last_p = None
    for p in points:
        # determine break periods and increment segment groups
        if not last_p:
            period = 0
            group = 1
        else:
            period = (p.timestamp_UTC - last_p.timestamp_UTC).total_seconds()
            if period > break_period:
                group += 1
        last_p = p

        # generate segments from determined groups
        p.period_before_seconds = period
        if segments and segments[-1].group == group:
            segments[-1].points.append(p)
        else:
            new_segment = TripSegment(group=group,
                                      period_before_seconds=period,
                                      points=[p])
            segments.append(new_segment)
    return segments


## helper functions
def euclidean_distance(point1, point2):
    '''Returns the distance between two points in meters'''
    a = point2.easting - point1.easting
    b = point2.northing - point2.northing
    return math.sqrt(a**2 + b**2)


## main
def run(coordinates, parameters):
    # process points as structs and cast position from lat/lng to UTM    
    subway_entrances = generate_subway_entrances(parameters['subway_entrances'])
    gps_points = generate_gps_points(coordinates)

    # clean noisy and duplicate points
    high_accuracy_points = filter_by_accuracy(gps_points, cutoff=parameters['accuracy_cutoff_meters'])
    cleaned_points = filter_erroneous_distance(high_accuracy_points, check_speed_kph=60)

    # break trips into atomic trip segments
    segments = break_by_collection_pause(cleaned_points, break_period=parameters['break_interval_seconds'])
    return segments

