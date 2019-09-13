#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


class UserActivity(object):
    def __init__(self, uuid, start_time=None, end_time=None):
        self.uuid = uuid
        self.start_time = start_time
        self.end_time = end_time
        self.commute_times = {}
        self.stay_times = {}
        self.complete_days = 0
        self.incomplete_days = 0
        self.inactive_days = 0
        self.num_trips = 0
        self.total_trips_duration = 0
        self.total_trips_distance = 0

    @property
    def trips_per_day(self):
        active_days = self.complete_days + self.incomplete_days
        if active_days:
            return float(self.num_trips) / active_days
        return 0.0

    @property
    def avg_trip_distance(self):
        return float(self.total_trips_distance) / self.num_trips

    def as_dict(self):
        return {
            'uuid': str(self.uuid),
            'start_timestamp_UTC': self.start_time.isoformat() if self.start_time else None,
            'end_timestamp_UTC': self.end_time.isoformat() if self.end_time else None,
            'commute_time_work_s': self.commute_times.get('work'),
            'commute_time_study_s': self.commute_times.get('study'),
            'stay_time_home_s': self.stay_times.get('home'),
            'stay_time_work_s': self.stay_times.get('work'),
            'stay_time_study_s': self.stay_times.get('study'),
            'complete_days': self.complete_days,
            'incomplete_days': self.incomplete_days,
            'inactive_days': self.inactive_days,
            'num_trips': self.num_trips,
            'trips_per_day': self.trips_per_day,
            'total_trips_duration_s': self.total_trips_duration,
            'total_trips_distance_m': self.total_trips_distance,
            'avg_trip_distance_m': self.avg_trip_distance,
        }

    def __repr__(self):
        s = self.start_time.replace(microsecond=0).isoformat()
        e = self.end_time.replace(microsecond=0).isoformat()
        return f"<activities.UserActivity uuid={self.uuid} start={s} end={e}>"
