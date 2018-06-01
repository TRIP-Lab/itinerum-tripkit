#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from geopy import distance


class Trip(object):
    def __init__(self, num, trip_code):
        self.num = int(num)
        self.trip_code = int(trip_code)
        self.points = []

    @property
    def distance(self):
        if len(self.points) > 1:
            cumulative = 0.
            last_point = None
            for p in self.points:
                if not last_point:
                    last_point = (p.latitude, p.longitude)
                    continue
                cumulative += distance.distance(last_point, (p.latitude, p.longitude)).meters
                last_point = (p.latitude, p.longitude)
            return cumulative
        return 0.

    @property
    def start_UTC(self):
        if self.points:
            return self.points[0].timestamp_UTC

    @property
    def end_UTC(self):
        if self.points:
            return self.points[-1].timestamp_UTC

    @property
    def geojson_coordinates(self):
        return [(p.longitude, p.latitude) for p in self.points]

    def __repr__(self):
        return '<Trip num={} code={}>'.format(self.num, self.trip_code)

