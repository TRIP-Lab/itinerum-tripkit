#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


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

    def all_commute_labels(self):
        return list(sorted([label for _, _, label in self._commutes]))

    def all_dwell_labels(self):
        return list(sorted([label for _, _, label in self._dwells]))

    @staticmethod
    def _init_values(d, date):
        if not date in d:
            d[date] = {'commutes': {}, 'dwells': {}, 'distance': 0}

    def __repr__(self):
        return f"<tripkit.process.activities.canue.models.UserActivity uuid={self.uuid}>"
