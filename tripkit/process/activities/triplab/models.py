#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import pytz

from .utils import localize, split_at_midnight


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

    # def group_by_date(self, timezone):
    #     commutes_by_date = {}
    #     for start_UTC, end_UTC, label in self.commute_times():
    #         start = localize(start_UTC, timezone)
    #         end = localize(end_UTC, timezone)
    #         for date, duration in split_at_midnight(start, end):
    #             day_commutes = commutes_by_date.setdefault(date, {})
    #             day_commutes.setdefault(label, []).append(duration)
        
    #     dwells_by_date = {}
    #     for start_UTC, end_UTC, label in self.dwell_times():
    #         start = localize(start_UTC, timezone)
    #         end = localize(end_UTC, timezone)
    #         for date, duration in split_at_midnight(start, end):
    #             day_dwells = dwells_by_date.setdefault(date, {})
    #             day_dwells.setdefault(label, []).append(duration)

    #     distances_by_date = {}
    #     for timestamp_UTC, distance in self.distances():
    #         date = localize(timestamp_UTC, timezone).date()
    #         distances_by_date.setdefault(date, []).append(distance)

    #     by_date = {}
    #     for date, commutes in commutes_by_date.items():
    #         by_date.setdefault(date, {})
    #         for label, durations in commutes.items():
    #             by_date[date][label] = sum(durations)
    #     for date, dwells in dwells_by_date.items():
    #         by_date.setdefault(date, {})
    #         for label, durations in dwells.items():
    #             by_date[date][label] = sum(durations)
    #     for date, distances in distances_by_date.items():
    #         by_date.setdefault(date, {})
    #         by_date[date]['distance'] = sum(distances)
    #     return by_date

    def __repr__(self):
        return f"<activities.UserActivity uuid={self.uuid}>"
