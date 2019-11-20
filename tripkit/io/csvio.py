#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from collections import namedtuple
import csv
import os

from .. import utils


# determine how newlines should be written dependent on OS
NEWLINE_MODE = '' if utils.misc.os_is_windows() else None


class CSVIO(object):
    def __init__(self, cfg):
        self.config = cfg


    # Efficiently return a value from the last row of a csv file
    # https://stackoverflow.com/a/54278929
    @staticmethod
    def _last_row_value(filepath, headers, key):
        with open(filepath, 'rb') as csv_f:
            csv_f.seek(-2, os.SEEK_END)
            while csv_f.read(1) != b'\n':
                csv_f.seek(-2, os.SEEK_CUR) 
            last_line = csv_f.readline().decode()
            reader = csv.DictReader(last_line, fieldnames=headers)
            return next(reader)[key]


    def write_trips(self, fn_base, trips, extra_fields=None, append=False):
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

        row_idx = None
        if append is True:
            row_idx = int(self._last_row_value(csv_fp, headers, 'id'))
            row_idx += 1
        else:
            with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
                writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
                writer.writeheader()
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
            if not row_idx:
                row_idx = 1
            for t in trips:
                for p in t.points:
                    record = {
                        'id': row_idx,
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
                    row_idx += 1

    def write_trip_summaries(self, fn_base, summaries, extra_fields=None, append=False):
        '''
        Write detected trip summary data to csv consisting of a single record for each trip.

        :param fn_base:      The base filename to prepend to the output csv file.
        :param summaries:    Iterable of trip summaries for row records.
        :param extra_fields: Additional columns to append to csv (must have matching
                             key in `summaries` object).
        :param append:       Append data to an existing .csv file.

        :type fn_base: str
        :type summaries: list of dict
        :type extra_fields: list, optional
        :type append: boolean, optional
        '''
        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{fn_base}-trip_summaries.csv')
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
        file_cleaned = utils.misc.clean_up_old_file(csv_fp)
        if append is False or file_cleaned:
            with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
                writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
                writer.writeheader()
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            if extra_fields:
                headers.extend(extra_fields)
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
            writer.writerows(summaries)

    def write_complete_days(self, trip_day_summaries, append=False):
        '''
        Write complete day summaries to .csv with a record per day per user over
        the duration of their participation in a survey.

        :param trip_day_summaries: Iterable of complete day summaries for each user enumerated by uuid and date.
        :param append:             Toggles whether summaries should be appended to an existing output file.

        :type trip_day_summaries: list of dict
        :type append:             boolean, optional
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
        file_cleaned = utils.misc.clean_up_old_file(csv_fp)
        if append is False or file_cleaned:
            with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
                writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
                writer.writeheader()
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers)
            writer.writerows(csv_rows)

    def write_activity_summaries(self, summaries, append=False):
        '''
        Write the activity summary data consisting of complete days and trips tallies with a record
        per each user for a survey.

        :param summaries: Iterable of user summaries for row records
        :param append:    Toggles whether summaries should be appended to an existing output file.

        :type summaries: list of dict
        :type append:    boolean, optional
        '''
        headers1 = (
            ['Survey timezone:', self.config.TIMEZONE]
            + [None] * 7
            + ['Activity locations (duration, seconds)', None, None, 'Commute times (duration, seconds)']
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
        file_cleaned = utils.misc.clean_up_old_file(csv_fp)
        if append is False or file_cleaned:
            with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
                writer = csv.writer(csv_f, dialect='excel')
                writer.writerow(headers1)
                writer.writerow(headers2)   
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers2)
            writer.writerows(summaries)

    def write_activities_daily(self, daily_summaries, extra_cols=None, append=False):
        '''
        Write the user activity summaries by date with a record for each day that a user
        participated in a survey.

        :param daily_summaries: Iterable of user summaries for row records.
        :param append:          Toggles whether summaries should be appended to an existing output file.

        :type daily_summaries: list of dict
        :type append:          boolean, optional
        '''
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
        
        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{self.config.SURVEY_NAME}-daily_activity_summaries.csv')
        file_cleaned = utils.misc.clean_up_old_file(csv_fp)
        if append is False or file_cleaned:
            with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
                writer = csv.writer(csv_f, dialect='excel')
                writer.writerow(headers1)
                writer.writerow(headers2)
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=headers2)
            writer.writerows(daily_summaries)

    def write_condensed_activity_locations(self, user, append=True):
        '''
        Write or append the provided user's activity locations to file.

        :param locations: Iterable of user summaries for row records.
        :param append:    Toggles whether summaries should be appended to an existing output file.

        :type locations: list of dict
        :type append:    boolean, optional
        '''
        headers = [
            ['Activity Locations'],
            ['UUID', 'Label', 'Latitude', 'Longitude']
        ]
        rows = []
        for loc in user.activity_locations:
            rows.append([user.uuid, loc.label, loc.latitude, loc.longitude])
        
        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{self.config.SURVEY_NAME}-activity_locations_condensed.csv')
        file_cleaned = utils.misc.clean_up_old_file(csv_fp)
        if append is False or file_cleaned:
            with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
                writer = csv.writer(csv_f, dialect='excel')
                writer.writerows(headers)
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            writer = csv.writer(csv_f, dialect='excel')
            writer.writerows(rows)

    def write_condensed_trip_summaries(self, user, trip_summaries, complete_day_summaries, append=False):
        '''
        Write the trip summaries with added columns for labeled trip origins/destinations and
        whether a trip occured on a complete trip day.

        :param daily_summaries: Iterable of user summaries for row records.
        :param append:          Toggles whether summaries should be appended to an existing output file.

        :type daily_summaries: list of dict
        :type append:          boolean, optional
        '''
        def _label_point_location(locations, point, proximity_m):
            for location in locations:
                if utils.geo.haversine_distance_m(point, location) <= proximity_m:
                    return location.label

        date_summaries = {cds.date: cds for cds in complete_day_summaries}
        summary_columns = [
            'uuid',
            'trip_id',
            'start_UTC',
            'start',
            'end_UTC',
            'end',
            'trip_code',
            'trip_type',
            'olat',
            'olon',
            'dlat',
            'dlon',
            'olocation',
            'dlocation',
            'direct_distance',
            'cumulative_distance',
            'complete_day'
        ]
        headers = [['Trip Summaries'], summary_columns]
        Point = namedtuple('Point', ['latitude', 'longitude'])
        rows = []
        for trip_summary in trip_summaries:
            trip_date_local = trip_summary['start'].date()
            trip_summary['trip_type'] = 'complete' if trip_summary['trip_code'] < 100 else 'missing'
            if trip_date_local in date_summaries:
                trip_summary['complete_day'] = date_summaries[trip_date_local].is_complete
            else:
                trip_summary['complete_day'] = False
            orig = Point(latitude=trip_summary['olat'], longitude=trip_summary['olon'])
            dest = Point(latitude=trip_summary['dlat'], longitude=trip_summary['dlon'])
            trip_summary['olocation'] = _label_point_location(user.activity_locations, orig, self.config.ACTIVITY_LOCATION_PROXIMITY_METERS)
            trip_summary['dlocation'] = _label_point_location(user.activity_locations, dest, self.config.ACTIVITY_LOCATION_PROXIMITY_METERS)
            rows.append(trip_summary)

        csv_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{self.config.SURVEY_NAME}-trip_summaries_condensed.csv')
        file_cleaned = utils.misc.clean_up_old_file(csv_fp)
        if append is False or file_cleaned:
            with open(csv_fp, 'w', newline=NEWLINE_MODE) as csv_f:
                writer = csv.writer(csv_f, dialect='excel')
                writer.writerows(headers)
        with open(csv_fp, 'a', newline=NEWLINE_MODE) as csv_f:
            writer = csv.DictWriter(csv_f, dialect='excel', fieldnames=summary_columns)
            writer.writerows(rows)
