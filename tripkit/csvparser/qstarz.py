#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import csv
from datetime import datetime
import json
import logging
import os
from playhouse.migrate import migrate, SqliteMigrator
import pytz
import uuid

from .common import _generate_null_survey, _load_subway_stations, _load_user_locations
from ..database import Coordinate
from ..utils.misc import temp_path

logger = logging.getLogger('itinerum-tripkit.csvparser.qstarz')


# .csv parsing
class QstarzCSVParser(object):
    '''
    Parses Qstarz csv files and loads to them to a cache database.

    :param config:
    :param database:      Open Peewee connection the cache database
    :param csv_input_dir: Path to the directory containing the input coordinates .csv data
    '''

    def __init__(self, config, database):
        self.config = config
        self.db = database
        self._migrator = SqliteMigrator(database.db)
        self.coordinates_csv = 'coordinates.csv'
        self.locations_csv = 'locations.csv'
        self.headers = [
            'INDEX',
            'UTC_DATE',
            'UTC_TIME',
            'LOCAL_DATE',
            'LOCAL_TIME',
            'LATITUDE',
            'N/S',
            'LONGITUDE',
            'E/W',
            'ALTITUDE',
            'SPEED',
            'USER',
        ]
        self.uuid_lookup = None

        # attach common functions
        self.load_subway_stations = _load_subway_stations
        # intialize survey timezone offset
        self.tz = pytz.timezone(self.config.TIMEZONE)

    @staticmethod
    def _value_or_none(row, key):
        '''
        Helper function to return the value stripped of whitespace or `None` for a 0-length string
        from a .csv cell value.
        '''
        v = row.get(key)
        if v and isinstance(v, str):
            return v.strip()

    def _coordinates_row_filter(self, row):
        lat, lon = self._value_or_none(row, 'LATITUDE'), self._value_or_none(row, 'LONGITUDE')
        if not lat or not lon:
            return
        lat, lon = float(lat), float(lon)
        if int(lat) == 0 and int(lon) == 0:
            return
        # add sign to negative lat/lons depending on hemisphere
        if row.get('N/S') == 'S' and lat > 0:
            lat *= -1
        if row.get('E/W') == 'W' and lon > 0:
            lon *= -1

        # format date and time columns into Python datetime (NOTE: QStarz data returns a 2-digit year)
        year, month, day = row['UTC_DATE'].split('/')
        if len(year) == 2:
            year = int('20' + year)
        year, month, day = int(year), int(month), int(day)
        hour, minute, second = [int(i) for i in row['UTC_TIME'].split(':')]
        timestamp_UTC = datetime(year, month, day, hour, minute, second, tzinfo=pytz.utc)
        timestamp_epoch = int(timestamp_UTC.timestamp())
        db_row = {
            'user': self.uuid_lookup[row['USER']],
            'latitude': lat,
            'longitude': lon,
            'altitude': self._value_or_none(row, 'ALTITUDE'),
            'speed': self._value_or_none(row, 'SPEED'),
            'direction': self._value_or_none(row, 'HEADING'),
            'h_accuracy': None,
            'v_accuracy': None,
            'acceleration_x': self._value_or_none(row, 'G-X'),
            'acceleration_y': self._value_or_none(row, 'G-Y'),
            'acceleration_z': self._value_or_none(row, 'G-Z'),
            'point_type': None,
            'mode_detected': None,
            'timestamp_UTC': timestamp_UTC,
            'timestamp_epoch': timestamp_epoch,
        }
        return db_row

    # read .csv file, apply filter and yield row
    def _row_generator(self, csv_fp, filter_func=None):
        with open(csv_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.reader(csv_f)  # use zip() below instead of DictReader for speed
            if not self.headers:
                self.headers = next(reader)
            else:
                next(reader)

            # generate dictionaries to insert and apply row filter if exists
            for row in reader:
                dict_row = dict(zip(self.headers, row))
                yield filter_func(dict_row) if filter_func else dict_row

    def _generate_uuids(self, input_dir):
        self.uuid_lookup = {}
        logger.info("Generating UUIDs for non-standard user ids...")
        lookup_fp = temp_path(f'{self.config.SURVEY_NAME}.json')
        if os.path.exists(lookup_fp):
            with open(lookup_fp, 'r') as json_f:
                self.uuid_lookup = json.load(json_f)
        else:
            coordinates_fp = os.path.join(input_dir, self.coordinates_csv)
            with open(coordinates_fp, 'r', encoding='utf-8-sig') as csv_f:
                reader = csv.reader(csv_f)
                user_id_idx = self.headers.index('USER')
                for r in reader:
                    # skip first row if header
                    if 'USER' in r:
                        continue

                    user_id = r[user_id_idx]
                    if not user_id in self.uuid_lookup:
                        self.uuid_lookup[user_id] = str(uuid.uuid4())
            with open(lookup_fp, 'w') as json_f:
                json.dump(self.uuid_lookup, json_f)

    def generate_null_survey(self, input_dir):
        '''
        Wrapper function to generate null survey responses for each user in coordinates.

        :param input_dir: Directory containing input .csv data
        '''
        self._generate_uuids(input_dir)
        _generate_null_survey(
            input_dir, self.coordinates_csv, id_column='user', uuid_lookup=self.uuid_lookup, headers=self.headers
        )

    def load_export_coordinates(self, input_dir):
        '''
        Loads QStarz coordinates data to the cache database.

        :param input_dir: The directory containing the `self.coordinates_csv` data file.
        '''
        logger.info("Loading coordinates .csv to db...")
        migrate(self._migrator.drop_index(Coordinate, 'coordinate_user_id'))
        coordinates_fp = os.path.join(input_dir, self.coordinates_csv)
        coordinates_rows = self._row_generator(coordinates_fp, self._coordinates_row_filter)
        self.db.bulk_insert(Coordinate, coordinates_rows)
        migrate(self._migrator.add_index('coordinates', ('user_id',), False))


    def load_user_locations(self, input_dir):
        '''
        Loads QStarz user locations data to the cache database.

        :param input_dir: The directory containing the `self.locations_csv` data file.        
        '''
        if not self.uuid_lookup:
            raise Exception('QStarz cannot load user locations before null survey has been initialized.')
        locations_fp = os.path.join(input_dir, self.locations_csv)
        if os.path.exists(locations_fp):
            _load_user_locations(locations_fp, uuid_lookup=self.uuid_lookup)
