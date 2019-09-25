#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import pytz


# return a naive UTC datetime to a localized datetime with offset tzinfo
def _localize(naive_utc, tz):
    return pytz.utc.localize(naive_utc).astimezone()

# get the durations for the trip as either a 1-member (no split at midnight) or a 
# 2-member (split at midnight) list of tuples --> [(date, duration_s), ...]
def _split_at_midnight(start, end):
    if start.day != end.day:
        midnight = end.replace(hour=0, minute=0, second=0, microsecond=0)
        return [
            (start.date(), (midnight - start).total_seconds()),
            (end.date(), (end - midnight).total_seconds())
        ]
    return [(start.date(), (end - start).total_seconds())]

class UserActivity(object):
    def __init__(self, uuid):
        self.uuid = uuid
        # durations
        self._commutes = []  # (start_utc, end_utc, label)
        self._dwells = []  # (start_utc, end_utc, label)
        # distances
        self._distances = []  # (timestamp_utc, distance from prior point)

        # aggregate survey tallies
        self.complete_days = 0
        self.incomplete_days = 0
        self.inactive_days = 0
        self.num_trips = 0

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

        # add complete trip timeseries
        pass
        
    def group_by_date(self, timezone):
        tz = pytz.timezone(timezone)

        commutes_by_date = {}
        for start_UTC, end_UTC, label in self.commute_times():
            start = _localize(start_UTC, tz)
            end = _localize(end_UTC, tz)
            for date, duration in _split_at_midnight(start, end):
                day_commutes = commutes_by_date.setdefault(date, {})
                day_commutes.setdefault(label, []).append(duration)
        
        dwells_by_date = {}
        for start_UTC, end_UTC, label in self.dwell_times():
            start = _localize(start_UTC, tz)
            end = _localize(end_UTC, tz)
            for date, duration in _split_at_midnight(start, end):
                day_dwells = dwells_by_date.setdefault(date, {})
                day_dwells.setdefault(label, []).append(duration)

        trips_by_date = {}
        for timestamp_UTC, distance in self.distances():
            date = _localize(timestamp_UTC, tz).date()
            trips_by_date.setdefault(date, {'distances': [], 'complete_trips': [], 'incomplete_trips': [], 'inactive_days': []})
            trips_by_date[date]['distances'].append(distance)




    def as_dict_condensed(self):
        return {
            'uuid': str(self.uuid),
            # 'start_timestamp_UTC': self.start_time.isoformat() if self.start_time else None,
            # 'end_timestamp_UTC': self.end_time.isoformat() if self.end_time else None,
            # 'commute_time_work_s': self.commute_times.get('work'),
            # 'commute_time_study_s': self.commute_times.get('study'),
            # 'stay_time_home_s': self.stay_times.get('home'),
            # 'stay_time_work_s': self.stay_times.get('work'),
            # 'stay_time_study_s': self.stay_times.get('study'),
            'complete_days': self.complete_days,
            'incomplete_days': self.incomplete_days,
            'inactive_days': self.inactive_days,
            'num_trips': self.num_trips,
            # 'trips_per_day': self.trips_per_day,
            # 'total_trips_duration_s': self.total_trips_duration,
            # 'total_trips_distance_m': self.total_trips_distance,
            # 'avg_trip_distance_m': self.avg_trip_distance,
        }

    # def as_dicts_daily(self):
    #     print(self._dwells)
    #     print(self._commutes)
    #     print(self._distances)

    #     # create series of consecutive dates that a user existed within a survey
    #     start_date = self.start_time.date()
    #     end_date = self.end_time.date()
        
    #     days = end_date - start_date
    #     print(days)
    #     # sort duration objects within each day
    #     for date, durations in by_day.items():
    #         # by_day[date] = sorted(durations, key=lambda d: d.start_time_UTC)
    #         dwells = {}
    #         commutes = {}
    #         for d in durations:

    # @property
    # def trips_per_day(self):
    #     active_days = self.complete_days + self.incomplete_days
    #     if active_days:
    #         return float(self.num_trips) / active_days
    #     return 0.0

    # @property
    # def total_trips_distance(self):
    #     return sum([c.distance for c in self._commutes])

    # @property
    # def avg_trip_distance(self):
    #     return float(self.total_trips_distance) / self.num_trips

    def __repr__(self):
        return f"<activities.UserActivity uuid={self.uuid}>"
