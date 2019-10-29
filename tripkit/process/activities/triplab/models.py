#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from datetime import timedelta
import pytz

from tripkit.utils.datetime import localize, split_at_midnight


class UserActivity(object):
    def __init__(self, uuid):
        self.uuid = uuid
        # durations
        self._commutes = []  # (start_utc, end_utc, label)
        self._dwells = []  # (start_utc, end_utc, label)
        # distances
        self._distances = []  # (timestamp_utc, distance from prior point)
        # user's active date range
        self.first_seen_UTC = None
        self.last_seen_UTC = None

    @property
    def commute_times(self):
        return sorted(self._commutes, key=lambda c: c[0])

    @property
    def dwell_times(self):
        return sorted(self._dwells, key=lambda d: d[0])

    @property
    def distances(self):
        return sorted(self._distances, key=lambda d: d[0])

    def add_commute_time(self, start_UTC, end_UTC, label):
        self._commutes.append((start_UTC, end_UTC, label))

    def add_dwell_time(self, start_UTC, end_UTC, label):
        self._dwells.append((start_UTC, end_UTC, label))

    def add_trip(self, trip):
        # add distance timeseries
        for p in trip.points:
            self._distances.append((p.timestamp_UTC, p.distance_before))

        # track first and last trip starts for date range
        if not self.first_seen_UTC or self.first_seen_UTC > trip.start_UTC:
            self.first_seen_UTC = trip.start_UTC
        if not self.last_seen_UTC or self.last_seen_UTC < trip.end_UTC:
            self.last_seen_UTC = trip.end_UTC

    @staticmethod
    def _init_values(d, date):
        if not date in d:
            d[date] = {'commutes': {}, 'dwells': {}, 'distance': 0}

    def group_by_date(self, timezone):
        start_date = localize(self.first_seen_UTC, timezone).date()
        end_date = localize(self.last_seen_UTC, timezone).date()
        last_trip_start_UTC, last_trip_end_UTC, _ = self.commute_times[-1]
        last_trip_start = localize(last_trip_start_UTC, timezone)
        last_trip_end = localize(last_trip_end_UTC, timezone)
        if len(split_at_midnight(last_trip_start, last_trip_end)) == 2:
            end_date += timedelta(days=1)

        date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        by_date = {}
        for d in date_range:
            by_date[d] = {
                'commutes': {},
                'dwells': {},
                'distance': 0,
                'num_trips': 0,
                'num_points': 0,
                'start_UTC': None,
                'end_UTC': None,
            }

        for start_UTC, end_UTC, label in self.commute_times:
            start = localize(start_UTC, timezone)
            end = localize(end_UTC, timezone)
            for date, duration in split_at_midnight(start, end):
                by_date[date]['commutes'].setdefault(label, []).append(duration)
                by_date[date]['num_trips'] += 1
            if not by_date[date]['start_UTC']:
                by_date[date]['start_UTC'] = start_UTC
            by_date[date]['end_UTC'] = end_UTC

        for start_UTC, end_UTC, label in self.dwell_times:
            start = localize(start_UTC, timezone)
            end = localize(end_UTC, timezone)
            for date, duration in split_at_midnight(start, end):
                by_date[date]['dwells'].setdefault(label, []).append(duration)

        for timestamp_UTC, distance in self.distances:
            date = localize(timestamp_UTC, timezone).date()
            by_date[date]['distance'] += distance
            by_date[date]['num_points'] += 1
        return by_date

    def __repr__(self):
        return f"<tripkit.process.activities.triplab.models.UserActivity uuid={self.uuid}>"
