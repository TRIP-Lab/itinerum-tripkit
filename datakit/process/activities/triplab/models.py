#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


class UserActivity(object):
    def __init__(self, uuid, start=None, end=None):
        self.uuid = uuid
        self.start_time = start
        self.end_time = end
        self.commute_times = {}
        self.stay_times = {}
        self.complete_days = 0
        self.incomplete_days = 0
        self.inactive_days = 0
        self.num_trips = 0
        self.total_trips_duration = 0
        self.total_trips_distance = 0

    def as_dict(self):
        return {
            'uuid': str(self.uuid),
            'start_timestamp_UTC': self.start_time.isoformat() if self.start_time else None,
            'end_timestamp_UTC': self.end_time.isoformat() if self.end_time else None,
            'commute_time_work': self.commute_times.get('work'),
            'commute_time_study': self.commute_times.get('study'),
            'stay_time_home': self.stay_times.get('home'),
            'stay_time_work': self.stay_times.get('work'),
            'stay_time_study': self.stay_times.get('study'),
            'complete_days': self.complete_days,
            'incomplete_days': self.incomplete_days,
            'inactive_days': self.inactive_days,
            'num_trips': self.num_trips,
            'total_trips_duration': self.total_trips_duration,
            'total_trips_distance': self.total_trips_distance,
        }

    def __repr__(self):
        s = self.start_time.replace(microsecond=0).isoformat()
        e = self.end_time.replace(microsecond=0).isoformat()
        return f"<activities.UserActivity uuid={self.uuid} start={s} end={e}>"
