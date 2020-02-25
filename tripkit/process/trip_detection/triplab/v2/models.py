#!/usr/bin/env python
# Kyle Fitzsimmons, 2015-2018
#
# Uses slots to achieve best performance (comparable to dictionary)
# and provide immutability against add or removing attributes
from datetime import datetime
import math

MODES = ['walking', 'subway']


class GPSPoint:
    __slots__ = [
        'database_id',
        'latitude',
        'longitude',
        'northing',
        'easting',
        'speed',
        'h_accuracy',
        'timestamp_UTC',
        'period_before_seconds',
        'distance_before_meters',
    ]

    def __init__(self, *args, **kwargs):
        # input attributes
        self.database_id = kwargs['database_id']
        self.latitude = kwargs['latitude']
        self.longitude = kwargs['longitude']
        self.northing = kwargs['northing']
        self.easting = kwargs['easting']
        self.speed = kwargs['speed']
        self.h_accuracy = kwargs['h_accuracy']
        self.timestamp_UTC = kwargs['timestamp_UTC']

        # trip attributes
        self.period_before_seconds = kwargs.get('period_before_seconds')
        self.distance_before_meters = kwargs.get('distance_before_meters')

    # Calculates the speed at the current point using the duration and distance
    # from the previous point
    @property
    def implied_speed(self):
        if self.distance_before_meters is not None and self.period_before_seconds:
            return self.distance_before_meters / self.period_before_seconds

    @property
    def timestamp_epoch(self):
        return int((self.timestamp_UTC - datetime(1970, 1, 1)).total_seconds())

    def __repr__(self):
        return f"<tripkit.process.trip_detection.triplab.v2.models.GPSPoint database_id={self.database_id}>"


class SubwayEntrance:
    __slots__ = ['latitude', 'longitude', 'northing', 'easting']

    def __init__(self, *args, **kwargs):
        self.latitude = kwargs['latitude']
        self.longitude = kwargs['longitude']
        self.northing = kwargs['northing']
        self.easting = kwargs['easting']

    def __repr__(self):
        return f"<tripkit.process.trip_detection.triplab.v2.models.SubwayEntrance>"


class SubwayRoute:
    __slots__ = ['route_id', 'coordinates', 'coordinates_utm', 'linestring_utm']

    def __init__(self, *args, **kwargs):
        self.route_id = kwargs['route_id']
        self.coordinates = kwargs['coordinates']
        self.coordinates_utm = kwargs['coordinates_utm']
        self.linestring_utm = kwargs['linestring_utm']

    def __repr__(self):
        return f"<tripkit.process.trip_detection.triplab.v2.models.SubwayRoute>"


class TripSegment:
    __slots__ = ['group', 'points', 'period_before_seconds', 'link_to', 'link_type', 'is_cold_start']

    def __init__(self, *args, **kwargs):
        self.group = kwargs['group']
        self.points = kwargs['points']
        self.period_before_seconds = kwargs['period_before_seconds']
        self.link_to = None
        self.link_type = None
        self.is_cold_start = False

    @property
    def start(self):
        if self.points:
            return self.points[0]

    @property
    def end(self):
        if self.points:
            return self.points[-1]

    def prepend(self, point):
        self.points.insert(0, point)

    def __repr__(self):
        return f"<tripkit.process.trip_detection.triplab.v2.models.TripSegment group={self.group}>"


class Trip:
    __slots__ = ['segments', 'labels', 'code']

    def __init__(self, *args, **kwargs):
        self.segments = kwargs['segments']
        self.labels = set()
        self.code = -1

    @property
    def first_segment(self):
        if self.segments:
            return self.segments[0]

    @property
    def last_segment(self):
        if self.segments:
            return self.segments[-1]

    @property
    def start_time(self):
        if self.first_segment:
            return self.first_segment.start.timestamp_UTC

    @property
    def end_time(self):
        if self.last_segment:
            return self.last_segment.end.timestamp_UTC

    @property
    def duration(self):
        return int((self.end_time - self.start_time).total_seconds())

    @property
    def links(self):
        _links = {}
        for idx, segment in enumerate(self.segments):
            if segment.link_to:
                connected = self.segments[idx + 1]
                assert segment.link_to == connected.group
                _links.setdefault(segment.link_type, []).append((segment.group, connected.group))
        return _links

    def link_to(self, linked_trip, link_type):
        self.last_segment.link_to = linked_trip.first_segment.group
        self.last_segment.link_type = link_type
        self.segments.extend(linked_trip.segments)

    def link_from(self):
        # could be added if MissingTrip was made interchangeable with
        # this class to avoid the labels set
        pass

    def add_label(self, label):
        self.labels.add(label)

    def direct_distance(self):
        point1 = self.first_segment.start
        point2 = self.last_segment.end
        a = point2.easting - point1.easting
        b = point2.northing - point1.northing
        return math.sqrt(a ** 2 + b ** 2)

    def cumulative_distance(self):
        seen = False  # skip first point's leading distance
        distance = 0.0
        for segment in self.segments:
            for point in segment.points:
                if not seen:
                    seen = True
                else:
                    distance += point.distance_before_meters
        return distance

    def avg_speed(self):
        return self.duration / self.cumulative_distance

    def __repr__(self):
        return f"<tripkit.process.trip_detection.triplab.v2.models.Trip code={self.code}>"


class MissingTrip:
    __slots__ = ['category', 'last_trip_end', 'next_trip_start', 'distance', 'duration', 'code']

    def __init__(self, *args, **kwargs):
        self.category = kwargs['category']
        self.last_trip_end = kwargs['last_trip_end']
        self.next_trip_start = kwargs['next_trip_start']
        self.distance = kwargs['distance']
        self.duration = kwargs['duration']
        self.code = -1

    @property
    def start(self):
        return self.last_trip_end

    @property
    def end(self):
        return self.next_trip_start

    @property
    def avg_speed(self):
        return self.distance / self.duration

    def __repr__(self):
        return (
            f"<tripkit.process.trip_detection.triplab.v2.models.MissingTrip category={self.category} code={self.code}>"
        )
