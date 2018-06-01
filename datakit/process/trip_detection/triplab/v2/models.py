#!/usr/bin/env python
# Kyle Fitzsimmons, 2015-2018
# - Algorithm data structures
# Uses slots to achieve best performance (comparable to dictionary)
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

    @property
    def start(self):
        if self.points:
            return self.points[0]

    @property
    def end(self):
        if self.points:
            return self.points[-1]


class Trip:
    __slots__ = ['num', 'segments']

    def __init__(self, *args, **kwargs):
        self.num = kwargs['num']
        self.segments = kwargs['segments']