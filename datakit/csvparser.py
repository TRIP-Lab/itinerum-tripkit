#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
import csv
from datetime import datetime
import logging
import os
from playhouse.migrate import migrate, SqliteMigrator


from .database import (UserSurveyResponse, Coordinate, PromptResponse, CancelledPromptResponse,
                       DetectedTripCoordinate, SubwayStationEntrance)


SQLITE_MAX_STATEMENT_VARIABLES = 999
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVParser(object):
    """
    Parses Itinerum platform csv files and loads to them to a cache database.

    :param database: Open Peewee connection the cache database
    """

    def __init__(self, database):
        self.db = database.db
        self._migrator = SqliteMigrator(self.db)
        self.cancelled_prompt_responses_csv = 'cancelled_prompts.csv'
        self.coordinates_csv = 'coordinates.csv'
        self.prompt_responses_csv = 'prompt_responses.csv'
        self.survey_responses_csv = 'survey_responses.csv'


    def _get(self, row, key, cast_func=None):
        value = row.get(key, '').strip()
        if value:
            if cast_func:
                return cast_func(value)
            return value

    def generate_null_survey(self, input_dir):
        """
        Generates an empty survey responses table for surveys with only coordinate
        data. Needed to populate the foreign keys on related child tables.
        """
        logger.info('Loading coordinates .csv and populating survey responses with null data in db...')
        coordinates_fp = os.path.join(input_dir, self.coordinates_csv)
        uuids = None
        with open(coordinates_fp, 'r', encoding='utf-8-sig') as csv_f:
            # much faster than csv.DictReader
            reader = csv.reader(csv_f)
            uuid_idx = next(reader).index('uuid')
            uuids = {r[uuid_idx] for r in reader}
        
        for uuid in uuids:
            UserSurveyResponse.create(uuid=uuid,
                                      created_at_UTC=datetime(2000, 1, 1),
                                      modified_at_UTC=datetime(2000, 1, 1),
                                      itinerum_version=-1,
                                      location_home_lat=0.,
                                      location_home_lon=0.,
                                      member_type='',
                                      model='',
                                      os='',
                                      os_version='')


    def load_export_survey_responses(self, input_dir):
        """
        Loads Itinerum survey responses data to the itinerum-datakit cache
        database. For each .csv row, the data is fetched by column name if
        it exists and cast to appropriate types as set in the database.

        :param input_dir: The directory containing the `self.survey_responses_csv`
                          data file.
        """
        logger.info('Loading survey responses .csv to db...')
        survey_responses_fp = os.path.join(input_dir, self.survey_responses_csv)
        with open(survey_responses_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                UserSurveyResponse.create(uuid=row['uuid'],
                                          created_at_UTC=row['created_at_UTC'],
                                          modified_at_UTC=row['modified_at_UTC'],
                                          itinerum_version=row['itinerum_version'],
                                          location_home_lat=self._get(row, 'location_home_lat', cast_func=float),
                                          location_home_lon=self._get(row, 'location_home_lon', cast_func=float),
                                          location_study_lat=self._get(row, 'location_study_lat', cast_func=float),
                                          location_study_lon=self._get(row, 'location_study_lon', cast_func=float),
                                          location_work_lat=self._get(row, 'location_work_lat', cast_func=float),
                                          location_work_lon=self._get(row, 'location_work_lon', cast_func=float),
                                          member_type=row['member_type'],
                                          model=row['model'],
                                          os=row['os'],
                                          os_version=row['os_version'],
                                          travel_mode_study_primary=self._get(row, 'travel_mode_study'),
                                          travel_mode_study_secondary=self._get(row, 'travel_mode_alt_study'),
                                          travel_mode_work_primary=self._get(row, 'travel_mode_work'),
                                          travel_mode_work_secondary=self._get(row, 'travel_mode_alt_work'))

    def load_export_coordinates(self, input_dir):
        """
        Loads Itinerum coordinates data to the itinerum-datakit cache
        database. For each .csv row, the data is fetched by column name if
        it exists and cast to appropriate types as set in the database.

        :param input_dir: The directory containing the `self.coordinates_csv`
                          data file.
        """
        logger.info('Loading coordinates .csv to db...')
        migrate(self._migrator.drop_index(Coordinate, 'coordinate_user_id'))
        coordinates_fp = os.path.join(input_dir, self.coordinates_csv)
        with open(coordinates_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.reader(csv_f)

            # find the row index for each expected values derived
            # from the first header row
            expected_keys = [('user', 'uuid'),
                             ('latitude', 'latitude'),
                             ('longitude', 'longitude'),
                             ('altitude', 'altitude'),
                             ('speed', 'speed'),
                             ('h_accuracy', 'h_accuracy'),
                             ('v_accuracy', 'v_accuracy'),
                             ('acceleration_x', 'acceleration_x'),
                             ('acceleration_y', 'acceleration_y'),
                             ('acceleration_z', 'acceleration_z'),
                             ('mode_detected', 'mode_detected'),
                             ('timestamp_UTC', 'timestamp_UTC')]
            headers = next(reader)
            key_map = { keys[0]: headers.index(keys[1])
                        for keys in expected_keys
                        if keys[1] in headers }

            datasource = []
            for row in reader:
                data = { keys[0]: row[keys[1]] for keys in key_map.items() }
                datasource.append(data)

            # wrap in single transaction for faster insert
            slice_size = SQLITE_MAX_STATEMENT_VARIABLES // len(data)
            with self.db.atomic():
                for idx in range(0, len(datasource), slice_size):
                    Coordinate.insert_many(datasource[idx:idx+slice_size]).execute()
        migrate(self._migrator.add_index('coordinates', ('user_id',), False))

    # profiled with mobilité
    # ---
    # 25.3s - single loop, created directly via model
    # 23.4s - dropped index, single loop
    #  7.1s - collect from csv to list and bulk write in 80 slice batches to db
    #  6.72s - dropped index, collect from csv to list and bulk write in 80 slice batches to db (below)
    #  7.15s - dropped index, single loop, bulk insert within loop determined by sqlite max slice size
    def load_export_prompt_responses(self, input_dir):
        """
        Loads Itinerum prompt responses data to the itinerum-datakit cache
        database. For each .csv row, the data is fetched by column name if
        it exists and cast to appropriate types as set in the database.

        :param input_dir: The directory containing the `self.prompt_responses.csv`
                          data file.
        """
        logger.info('Loading prompt responses .csv to db...')
        migrate(self._migrator.drop_index(PromptResponse, 'promptresponse_user_id'))
        prompt_responses_fp = os.path.join(input_dir, self.prompt_responses_csv)
        with open(prompt_responses_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.DictReader(csv_f)
            datasource = []
            for row in reader:
                data = {
                    'user': row['uuid'],
                    'prompt_uuid': row['prompt_uuid'],
                    'prompt_num': row['prompt_num'],
                    'response': row['response'],
                    'latitude': (row['latitude']),
                    'longitude': float(row['longitude']),
                    'displayed_at_UTC': row['displayed_at_UTC'],
                    'recorded_at_UTC': row['recorded_at_UTC'],
                    'edited_at_UTC': row['edited_at_UTC']
                }
                datasource.append(data)

            # wrap in single transaction for faster insert
            slice_size = SQLITE_MAX_STATEMENT_VARIABLES // len(data)
            with self.db.atomic():
                for idx in range(0, len(datasource), slice_size):
                    PromptResponse.insert_many(datasource[idx:idx+slice_size]).execute()
        migrate(self._migrator.add_index('prompt_responses', ('user_id',), False))


    def load_export_cancelled_prompt_responses(self, input_dir):
        """
        Loads Itinerum cancelled prompt responses data to the itinerum-datakit cache
        database. For each .csv row, the data is fetched by column name if
        it exists and cast to appropriate types as set in the database.

        :param input_dir: The directory containing the `self.cancelled_prompt_responses.csv`
                          data file.
        """
        logger.info('Loading cancelled prompt responses .csv to db...')
        cancelled_prompt_responses_fp = os.path.join(input_dir, self.cancelled_prompt_responses_csv)
        with open(cancelled_prompt_responses_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.DictReader(csv_f)

            for row in reader:
                CancelledPromptResponse.create(user=row['uuid'],
                                               prompt_uuid=row['prompt_uuid'],
                                               latitude=float(row['latitude']),
                                               longitude=float(row['longitude']),
                                               displayed_at_UTC=row['displayed_at_UTC'],
                                               cancelled_at_UTC=self._get(row, 'cancelled_at_UTC'),
                                               is_travelling=self._get(row, 'is_travelling'))


    def load_trips(self, trips_csv_fp):
        """
        Loads trips processed by the web platform itself. This is mostly useful
        for comparing current alogorithm results against the deployed platform's
        version.

        :param trips_csv_fp: The full filepath of the downloaded trips `.csv` file
                             for a survey.
        """
        logger.info('Loading detected trips .csv to db...')
        with open(trips_csv_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.DictReader(csv_f)
            DetectedTripCoordinate.drop_table()
            DetectedTripCoordinate.create_table()

            for row in reader:
                DetectedTripCoordinate.create(user=row['uuid'],
                                              trip_num=int(row['trip']),
                                              latitude=float(row['latitude']),
                                              longitude=float(row['longitude']),
                                              h_accuracy=float(row['h_accuracy']),
                                              timestamp_UTC=row['timestamp'],
                                              trip_code=int(row['trip_code']))


    def load_subway_stations(self, subway_stations_csv_fp):
        """
        Loads a subway station entraces .csv the database for use by trip
        detection algorithms. Each .csv row should represent a station entrance
        with the column names of 'x' (or 'longitude') and 'y' (or 'latitude').

        :param subway_stations_csv_fp: The full filepath of subway station entrances
                                       `.csv` for the survey study region.
        """
        # change selected column keys to latitude and longitude
        def _rename_columns(location_columns, rows):
            lat_label, lng_label = location_columns
            for row in rows:
                row['latitude'] = row.pop(lat_label)
                row['longitude'] = row.pop(lng_label)
                yield row

        logger.info('Loading subway stations .csv to db...')
        with open(subway_stations_csv_fp, 'r') as csv_f:
            # detect whether commas or semicolon is used a separator (english/french)
            dialect = csv.Sniffer().sniff(csv_f.read(), delimiters=';,')
            csv_f.seek(0)

            reader = csv.DictReader(csv_f, dialect=dialect)
            reader.fieldnames = [name.lower() for name in reader.fieldnames]

            # determine the exsting keys out of the options for the lat/lng columns
            location_columns = None
            location_columns_options = [('latitude', 'longitude'),
                                        ('lat', 'lng'),
                                        ('lat', 'lon'),
                                        ('y', 'x')]

            for columns in location_columns_options:
                if set(columns).issubset(set(reader.fieldnames)):
                    location_columns = columns

            # rename columns if latitude/longitude are not already found
            rename = ('latitude' and 'longitude') not in location_columns
            if rename:
                reader = _rename_columns(location_columns, reader)

            for row in reader:
                SubwayStationEntrance.create(latitude=float(row['latitude']),
                                             longitude=float(row['longitude']))
