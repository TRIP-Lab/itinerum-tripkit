#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from datetime import datetime, timedelta


class Group(object):
    def __init__(self):
        self.trip_codes = []
        self.start_points = []
        self.second_points = []
        self.end_points = []

    @property
    def has_trips(self):
        if self.trip_codes:
            return True
        return False

    @property
    def contains_missing_trips(self):
        if [c for c in self.trip_codes if (c >= 100 and c < 200)]:
            return True
        return False

    @property
    def start_point(self):
        if self.start_points:
            return self.start_points[0]

    @property
    def end_point(self):
        if self.end_points:
            return self.end_points[-1]

    @property
    def segment_second_point(self):
        if self.second_points:
            return self.second_points[0]

    def __repr__(self):
        return f"<tripkit.process.complete_days.canue.models.Group>"


class DailyGroups:
    def __init__(self, start_dt_local, end_dt_local):
        self._summaries = {}
        delta = end_dt_local - start_dt_local
        for i in range(delta.days + 1):
            date = start_dt_local + timedelta(days=i)
            self._summaries[date] = Group()

    def add_trip(self, trip):
        date = trip.start_local.date()
        self._summaries[date].start_points.append(trip.start)
        if len(trip.points) > 1:
            self._summaries[date].second_points.append(trip.points[1])
        self._summaries[date].end_points.append(trip.end)
        self._summaries[date].trip_codes.append(trip.trip_code)

    def sorted_by_date(self):
        return sorted(self._summaries.items())

    def get_start_point(self, date):
        return self._summaries[date].start_point

    def get_end_point(self, date):
        return self._summaries[date].end_point

    def get_second_point(self, date):
        return self._summaries[date].segment_second_point

    def __repr__(self):
        return f"<tripkit.process.canue.models.DailyGroups>"
