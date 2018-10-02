#!/usr/bin/env python
# Kyle Fitzsimmons, 2015-2018
# - Algorithm data structures
# Uses slots to achieve best performance (comparable to dictionary)
# and provide immutability against add or removing attributes


MODES = ['walking', 'subway']


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

    @property
    def start(self):
        if self.points:
            return self.points[0]

    @property
    def end(self):
        if self.points:
            return self.points[-1]


class Trip:
    __slots__ = ['num', 'segments', 'links', 'subway_links',
                 'walking_links', 'has_cold_start']

    def __init__(self, *args, **kwargs):
        self.num = kwargs['num']
        self.segments = kwargs['segments']
        self.subway_links = set()
        self.walking_links = set()
        self.has_cold_start = False

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

    def link_by_subway(self, next_trip):
        self.subway_links.add(next_trip.num)

    def link_by_walking(self, next_trip):
        self.walking_links.add(next_trip.num)


class MissingTrip:
    __slots__ = ['category', 'last_trip_end', 'next_trip_start',
                 'distance', 'duration']

    def __init__(self, *args, **kwargs):
        self.category = kwargs['category']
        self.last_trip_end = kwargs['last_trip_end']
        self.next_trip_start = kwargs['next_trip_start']
        self.distance = kwargs['distance']
        self.duration = kwargs['duration']

    @property
    def timestamp_UTC(self):
        return self.last_trip_end.timestamp_UTC
    