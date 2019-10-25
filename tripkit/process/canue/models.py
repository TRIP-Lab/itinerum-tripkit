#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import ciso8601
from datetime import datetime


class Coordinate(object):
    '''
    CANUE processing library object to act like itinerum-tripkit Coordinate object with additional properties.

    :param c: A Py:Class:`tripkit.database.Coordinate` object to wrap
    '''

    # explicitly state slots to control against adding unknown attributes to the object
    __slots__ = [
        'uuid',
        'latitude',
        'longitude',
        'timestamp_UTC',
        'duration_s',
        'distance_m',
        'altitude',
        'speed',
        'bearing',
        'delta_heading',
        'easting',
        'northing',
        'zone_num',
        'zone_letter',
        'timestamp_epoch',
        'avg_distance_m',
        'avg_delta_heading',
        'kmeans',
        'stdev',
        'stop_label'
    ]

    def __init__(self, c):
        self.uuid = c.user
        self.latitude = c.latitude
        self.longitude = c.longitude
        self.timestamp_UTC = ciso8601.parse_datetime_as_naive(c.timestamp_UTC)  # optimization for datetime.fromisoformat()
        # attributes to be later calculated based upon previous point
        self.duration_s = 0
        self.distance_m = 0.0
        self.altitude = c.altitude
        self.speed = c.speed
        self.bearing = 0
        self.delta_heading = 0
        self.easting = None
        self.northing = None
        self.zone_num = None
        self.zone_letter = None
        self.timestamp_epoch = (self.timestamp_UTC - datetime(1970, 1, 1)).total_seconds()
        self.avg_distance_m = None
        self.avg_delta_heading = None
        self.kmeans = None
        self.stdev = None
        self.stop_label = None

    @property
    def speed_ms(self):
        if self.distance_m:
            return self.distance_m / self.duration_s
        return 0.0

    def csv_row(self):
        return [
            self.uuid,
            self.latitude,
            self.longitude,
            self.timestamp_UTC.isoformat(),
            self.duration_s,
            self.distance_m,
            self.bearing,
            self.delta_heading,
            self.avg_distance_m,
            self.avg_delta_heading,
            self.kmeans.label,
            self.kmeans.group_num,
            self.stdev.label,
            self.stdev.group_num
        ]


class ClusterInfo:
    def __init__(self, group_num=None, label=None):
        self.group_num = group_num
        self.label = label

    def __repr__(self):
        return f'<ClusterInfo group_num={self.group_num} label="{self.label}">'
