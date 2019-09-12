#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import csv
from datetime import datetime
import logging
import os
from playhouse.migrate import migrate, SqliteMigrator
import pytz

from .common import _generate_null_survey, _load_subway_stations
from ..database import Coordinate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _coordinates_row_filter(row):
    timestamp_UTC = datetime.fromisoformat(f'{row["date"]}T{row["time"]}').replace(tzinfo=pytz.UTC)
    timestamp_epoch = int(timestamp_UTC.timestamp())
    db_row = {
        'user': row['uuid'],
        'latitude': row['lat'],
        'longitude': row['lon'],
        'altitude': None,
        'speed': None,
        'direction': None,
        'h_accuracy': None,
        'v_accuracy': None,
        'acceleration_x': None,
        'acceleration_y': None,
        'acceleration_z': None,
        'point_type': None,
        'mode_detected': None,
        'timestamp_UTC': timestamp_UTC,
        'timestamp_epoch': timestamp_epoch,
    }
    return db_row


# .csv parsing
class QstarzCSVParser(object):
    '''
    Parses Qstarz csv files and loads to them to a cache database.

    :param database:      Open Peewee connection the cache database
    :param csv_input_dir: Path to the directory containing the input coordinates .csv data
    '''

    def __init__(self, database, csv_input_dir):
        self.db = database
        self._migrator = SqliteMigrator(database.db)
        self.coordinates_csv = self._fetch_csv_fn(csv_input_dir, not_contains='_summary.csv')
        self.headers = [
            'point_id',
            'id',
            'route_id',
            'lon',
            'lat',
            'object_id',
            'uuid',
            'type',
            'lat_direction',
            'lon_direction',
            'uuid',
            'date',
            'start_time',
            'sec_point',
            'route_id_2',
            'uuid_2',
            'order',
            'time',
        ]
        # attach common functions
        self.load_subway_stations = _load_subway_stations

    def _fetch_csv_fn(self, input_dir, contains=None, not_contains=None):
        '''
        Helper function to return the .csv file in the given input data directory which uniquely matches the given
        **contains** parameter.
        '''
        if contains and not_contains:
            raise Exception("csv_fn should only contain either a `contains` or `not_contains` search string, not both")

        for fn in os.listdir(input_dir):
            if contains and contains in fn:
                return fn
            elif not_contains:
                if '._' in fn:
                    continue
                if not_contains not in fn:
                    return fn

    # read .csv file, apply filter and yield row
    @staticmethod
    def _row_generator(csv_fp, filter_func=None, headers=None):
        with open(csv_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.reader(csv_f)  # use zip() below instead of DictReader for speed
            if not headers:
                headers = next(reader)

            # generate dictionaries to insert and apply row filter if exists
            for row in reader:
                dict_row = dict(zip(headers, row))
                yield filter_func(dict_row) if filter_func else dict_row

    def generate_null_survey(self, input_dir):
        '''
        Wrapper function to generate null survey responses for each user in coordinates.

        :param input_dir: Directory containing input .csv data
        '''
        _generate_null_survey(input_dir, self.coordinates_csv, headers=self.headers)

    def load_export_coordinates(self, input_dir):
        '''
        Loads Qstarz coordinates data to the cache database.

        :param input_dir: The directory containing the `self.coordinates_csv`
                          data file.
        '''
        logger.info("Loading coordinates .csv to db...")
        migrate(self._migrator.drop_index(Coordinate, 'coordinate_user_id'))
        coordinates_fp = os.path.join(input_dir, self.coordinates_csv)
        # note: duplicate `uuid` is intentional
        coordinates_rows = self._row_generator(coordinates_fp, _coordinates_row_filter, self.headers)
        self.db.bulk_insert(Coordinate, coordinates_rows)
        migrate(self._migrator.add_index('coordinates', ('user_id',), False))
