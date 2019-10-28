#!/usr/bin/env python
# Kyle Fitzsimmons, 2018


class Trip(object):
    '''
    :param int num:       The integer index (starting at 1) of all the detected
                          trip events (completer or incomplete) as user has made
                          over the duration of their survey participation.
    :param int trip_code: The integer code representing the detected trip type.

    :ivar points:         The timestamp-ordered points that comprise this ``Trip``.
    :vartype points:      list of :py:class:`tripkit.models.TripPoint`
    '''

    def __init__(self, num, trip_code):
        self.num = int(num)
        self.trip_code = int(trip_code)
        self.points = []

    @property
    def distance(self):
        if len(self.points) > 1:
            return self.points[-1].trip_distance
        return 0.0

    @property
    def duration(self):
        if len(self.points) > 1:
            return self.points[-1].timestamp_epoch - self.points[0].timestamp_epoch
        return 0

    @property
    def start_UTC(self):
        if self.points:
            return self.points[0].timestamp_UTC

    @property
    def end_UTC(self):
        if self.points:
            return self.points[-1].timestamp_UTC

    @property
    def start(self):
        return self.points[0]

    @property
    def end(self):
        return self.points[-1]

    @property
    def geojson_coordinates(self):
        return [(p.longitude, p.latitude) for p in self.points]

    def __repr__(self):
        return f"<tripkit.models.Trip num={self.num} code={self.trip_code}>"
