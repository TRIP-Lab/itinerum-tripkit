#!/usr/bin/env python
# Based upon GERT 1.2 (2016-06-03): GIS-based Episode Reconstruction Toolkit
# Ported to itinerum-datakit by Kyle Fitzsimmons, 2019
from datetime import datetime


class GertCoordinate(object):
    """
    GERT processing library object to act like itinerum-datakit Coordinate object with additional properties.

    :param c: A Py:Class:`datakit.database.Coordinate` object to wrap
    """

    # explicitly state slots to control against adding unknown attributes to the object
    __slots__ = ['uuid', 'latitude', 'longitude', 'timestamp_UTC', 'duration_s', 'distance_m', 'bearing',
                 'delta_heading']

    def __init__(self, c):
        self.uuid = c.user
        self.latitude = c.latitude
        self.longitude = c.longitude
        self.timestamp_UTC = datetime.fromisoformat(c.timestamp_UTC)
        # attributes to be later calculated based upon previous point
        self.duration_s = 0
        self.distance_m = 0.
        self.bearing = 0
        self.delta_heading = 0

    @property
    def speed_ms(self):
        if self.distance_m:
            return self.distance_m / self.duration_s
