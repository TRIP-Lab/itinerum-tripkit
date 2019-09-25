#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import pytz


# class DwellActivity(object):
#     def __init__(self, start_time_UTC, label, duration):
#         self.start_time_UTC = start_time_UTC
#         self.label = label
#         self.duration = duration
#         # self.distance = distance

#     # @property
#     # def duration(self):
#     #     return (self.end_time_UTC - self.start_time_UTC).total_seconds()

#     def __repr__(self):
#         print(self.start_time_UTC, self.end_time_UTC)
#         return "<Activity start={s} end={e} duration={d}>".format(
#             s=self.start_time_UTC.isoformat(), e=self.end_time_UTC.isoformat(), d=self.duration)



class UserActivity(object):
    def __init__(self, uuid, timezone):
        self.uuid = uuid
        # durations by date (localized)
        self._commutes = {}
        self._dwells = {}
        # aggregate trip information by date (localized)
        self._trip_distances = {}
        self._trip_durations = {}

        # aggregate survey tallies
        self.complete_days = 0
        self.incomplete_days = 0
        self.inactive_days = 0
        self.num_trips = 0

    @property
    def commutes(self):
        return sorted(self._commutes.items(), key=lambda kv: kv[0])

    def add_commute_time(self, date, label, duration):
        # date = self._localize(trip.start_UTC).date()
        commute = self._commutes.setdefault(date, {'work': 0.0, 'study': 0.0})
        commute.setdefault(label, 0)
        commute[label] += duration

    def add_dwell_time(self, date, label, duration):
        # date = self._localize(trip.start_UTC).date()
        dwell = self._dwells.setdefault(date, {})

    # func to add trip information to 


    def add_trip(self, trip):
        '''
        Tally the daily trip distance and durations.

        :param `py:class:Trip` trip: An itinerum-tripkit trip object
        '''
        date = trip.start_UTC.date()
        distance = self._trip_distances.setdefault(date, 0.)
        duration = self._trip_durations.setdefault(date, 0.)
        if trip.trip_code < 100:
            distance += trip.distance
            duration += (trip.end_UTC - trip.start_UTC).total_seconds()

    def as_dict_condensed(self):
        print(self._commutes)
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
    # def start_time(self):
    #     if self._commutes and self._dwells:
    #         first_seen = min(self._commutes[0].start_time_UTC, self._dwells[0].start_time_UTC)
    #         return self._localize(first_seen)

    # @property
    # def end_time(self):
    #     if self._commutes and self._dwells:
    #         last_seen = min(self._commutes[-1].end_time_UTC, self._dwells[-1].end_time_UTC)
    #         return self._localize(last_seen)

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

    # def add_dwell_time(self, start_time_UTC, end_time_UTC, label=None):
    #     d = Activity(start_time_UTC, end_time_UTC, label=label)
    #     self._dwells.append(d)

    # def add_commute_time(self, start_time_UTC, end_time_UTC, distance, label=None):
    #     c = Activity(start_time_UTC, end_time_UTC, label=label, distance=distance)
    #     self._commutes.append(c)

    # def __repr__(self):
    #     s = self.start_time.replace(microsecond=0).isoformat()
    #     e = self.end_time.replace(microsecond=0).isoformat()
    #     return f"<activities.UserActivity uuid={self.uuid} start={s} end={e}>"
