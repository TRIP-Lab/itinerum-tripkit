#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import csv
import os

from .. import utils


# determine how newlines should be written dependent on OS
NEWLINE_MODE = '' if utils.misc.os_is_windows() else None


class CSVIO(object):
    def __init__(self, cfg):
        self.config = cfg

    def write_trips(self, fn_base, trips, extra_fields=None):
        '''
        Write detected trips data to a csv file.

        :param fn_base: The base filename to prepend to the output csv file
        :param trips:   Iterable of database trips to write to csv file

        :type fn_base: str
        :param trips: list of :py:class:`tripkit.models.Trip`
        '''
        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{fn_base}_trips.csv')
        headers = [
            'id',
            'uuid',
            'trip',
            'latitude',
            'longitude',
            'h_accuracy',
            # 'v_accuracy',
            'timestamp_UTC',
            'timestamp_epoch',
            'trip_distance',
            'distance',
            'break_period',
            'trip_code',
        ]
        if extra_fields:
            headers.extend(extra_fields)
        with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
            writer.writeheader()
            idx = 1
            for t in trips:
                for p in t.points:
                    record = {
                        'id': idx,
                        'uuid': None,
                        'trip': t.num,
                        'latitude': p.latitude,
                        'longitude': p.longitude,
                        'h_accuracy': p.h_accuracy,
                        # 'v_accuracy': p.v_accuracy,
                        'timestamp_UTC': p.timestamp_UTC,
                        'timestamp_epoch': p.timestamp_epoch,
                        'trip_distance': p.trip_distance,
                        'distance': p.distance_before,
                        'break_period': p.period_before,
                        'trip_code': t.trip_code,
                    }
                    if extra_fields:
                        for field in extra_fields:
                            record[field] = getattr(p, field)
                    writer.writerow(record)
                    idx += 1

    def write_trip_summaries(self, fn_base, summaries, extra_fields=None):
        '''
        Write detected trip summary data to csv consisting of a single record for each trip.

        :param fn_base:      The base filename to prepend to the output csv file
        :param summaries:    Iterable of trip summaries for row records
        :param extra_fields: Additional columns to append to csv (must have matching
                            key in `summaries` object)

        :type fn_base: str
        :type summaries: list of dict
        :type extra_fields: list, optional
        '''
        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{fn_base}-trip_summaries.csv')
        with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
            headers = [
                'uuid',
                'trip_id',
                'start_UTC',
                'start',
                'end_UTC',
                'end',
                'trip_code',
                'olat',
                'olon',
                'dlat',
                'dlon',
                'merge_codes',
                'direct_distance',
                'cumulative_distance',
            ]
            if extra_fields:
                headers.extend(extra_fields)
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
            writer.writeheader()
            writer.writerows(summaries)

    def write_complete_days(self, trip_day_summaries):
        '''
        Write complete day summaries to .csv with a record per day per user over
        the duration of their participation in a survey.

        :param trip_day_summaries: Iterable of complete day summaries for each user
                                enumerated by uuid and date.

        :type trip_day_summaries: list of dict
        '''
        csv_rows = []
        for uuid, daily_summaries in trip_day_summaries.items():
            for s in daily_summaries:
                start_lat = s.start_point.latitude if s.start_point else None
                start_lon = s.start_point.longitude if s.start_point else None
                end_lat = s.start_point.latitude if s.end_point else None
                end_lon = s.start_point.longitude if s.end_point else None
                record = {
                    'uuid': uuid,
                    'date': s.date,
                    'has_trips': 1 if s.has_trips else 0,
                    'is_complete': 1 if s.is_complete else 0,
                    'start_latitude': start_lat,
                    'start_longitude': start_lon,
                    'end_latitude': end_lat,
                    'end_longitude': end_lon,
                    'consecutive_inactive_days': s.consecutive_inactive_days,
                    'inactivity_streak': s.inactivity_streak,
                }
                csv_rows.append(record)
        headers = [
            'uuid',
            'date',
            'has_trips',
            'is_complete',
            'start_latitude',
            'start_longitude',
            'end_latitude',
            'end_longitude',
            'consecutive_inactive_days',
            'inactivity_streak',
        ]
        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{self.config.SURVEY_NAME}-complete_days.csv')
        with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
            writer.writeheader()
            writer.writerows(csv_rows)

    def write_activity_summaries(self, summaries):
        '''
        Write the activity summary data consisting of complete days and trips tallies with a record
        per each user for a survey.

        :param summaries: Iterable of user summaries for row records

        :type summaries: list of dict
        '''
        headers1 = (
            ['Survey timezone:', self.config.TIMEZONE]
            + [None] * 7
            + ['Semantic locations (duration, seconds)', None, None, 'Commute times (duration, seconds)']
        )
        headers2 = [
            'uuid',
            'start_timestamp',
            'end_timestamp',
            'complete_days',
            'incomplete_days',
            'inactive_days',
            'num_trips',
            'avg_trips_per_day',
            'total_trips_distance_m',
            'avg_trip_distance_m',
            'total_trips_duration_s',
            'dwell_time_home_s',
            'dwell_time_work_s',
            'dwell_time_study_s',
            'commute_time_study_s',
            'commute_time_work_s',
        ]
        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{self.config.SURVEY_NAME}-activity_summaries.csv')
        with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
            writer = csv.writer(csv_f, dialect='excel')
            writer.writerow(headers1)
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers2)
            writer.writeheader()
            writer.writerows(summaries)

    def write_activities_daily(self, daily_summaries, extra_cols=None):
        '''
        Write the user activity summaries by date with a record for each day that a user
        participated in a survey.

        :param daily_summaries: Iterable of user summaries for row records

        :type daily_summaries: list of dict
        '''
        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{self.config.SURVEY_NAME}-daily_activity_summaries.csv')
        headers1 = ['Survey timezone:', self.config.TIMEZONE]
        headers2 = [
            'uuid',
            'date',
            'start_time',
            'end_time',
            'num_trips',
            'num_points',
            'trips_distance_m',
            'trips_duration_s',
        ]
        if extra_cols:
            headers2 += extra_cols
        with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
            writer = csv.writer(csv_f, dialect='excel')
            writer.writerow(headers1)
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers2)
            writer.writeheader()
            writer.writerows(daily_summaries)
