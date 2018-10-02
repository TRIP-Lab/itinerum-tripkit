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
    __slots__ = ['group', 'points', 'period_before_seconds', 'link_to',
                 'link_type', 'is_cold_start']

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


class Trip:
    __slots__ = ['segments']

    def __init__(self, *args, **kwargs):
        self.segments = kwargs['segments']

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
    def links(self):
        _links = {}
        for idx, segment in enumerate(self.segments):
            if segment.link_to:
                connected = self.segments[idx + 1]
                assert segment.link_to == connected.group
                _links.setdefault(s.link_type, []).append((segment.group, connected.group))
        return _links

    def link_to(self, linked_trip, link_type):
        self.last_segment.link_to = linked_trip.first_segment.group
        self.last_segment.link_type = link_type
        self.segments.extend(linked_trip.segments)


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
    