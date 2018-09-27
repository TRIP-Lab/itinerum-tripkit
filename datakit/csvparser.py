#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
import csv
import logging
import os
from playhouse.migrate import migrate, SqliteMigrator


from .database import (UserSurveyResponse, Coordinate, PromptResponse, CancelledPromptResponse,
                       DetectedTripCoordinate, SubwayStationEntrance)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


## .csv row filters for parsing Itinerum exports to database models
def _survey_response_row_filter(row):
    # reject invalid rows
    if not row['member_type']:
        return None

    for key, value in row.items():
        if value == '':
            row[key] = None

    row['travel_mode_work_primary'] = row.pop('travel_mode_work', None)
    row['travel_mode_work_secondary'] = row.pop('travel_mode_alt_work', None)
    row['travel_mode_study_primary'] = row.pop('travel_mode_study', None)
    row['travel_mode_study_secondary'] = row.pop('travel_mode_alt_study', None)
    row['travel_mode_study_secondary'] = row.pop('travel_mode_alt_study', None)

    # remove any columns not renamed or found in database model
    trim_columns = set(row.keys()) - set(UserSurveyResponse._meta.sorted_field_names)
    for col in trim_columns:
        del row[col]

    return row

def _coordinates_row_filter(row):
    # invalid rows
    if not row['timestamp_UTC']:
        return None

    row['user'] = row.pop('uuid')
    for key, value in row.items():
        if value == '':
            row[key] = None
    return row

def _prompts_row_filter(row):
    row['user'] = row.pop('uuid')
    trim_columns = ['displayed_at_epoch', 'recorded_at_epoch', 'edited_at_epoch']
    for col in trim_columns:
        del row[col]
    return row

def _cancelled_prompts_row_filter(row):
    row['user'] = row.pop('uuid')
    trim_columns = ['displayed_at_epoch', 'cancelled_at_epoch']
    for col in trim_columns:
        del row[col]
    return row

def _trips_row_filter(row):
    row['user'] = row.pop('uuid')
    row['trip_num'] = row.pop('trip')
    row['timestamp_UTC'] = row.pop(timestamp)
    return row


## .csv parsing
class CSVParser(object):
    """
    Parses Itinerum platform csv files and loads to them to a cache database.

    :param database: Open Peewee connection the cache database
    """

    def __init__(self, database):
        self.db = database
        self._migrator = SqliteMigrator(database.db)
        self.cancelled_prompt_responses_csv = 'cancelled_prompts.csv'
        self.coordinates_csv = 'coordinates.csv'
        self.prompt_responses_csv = 'prompt_responses.csv'
        self.survey_responses_csv = 'survey_responses.csv'


    def _get(self, row, key, cast_func=None):
        value = row.get(key)
        if value:
            value = value.strip()
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

    # read .csv file, apply filter and yield row
    @staticmethod
    def _row_generator(csv_fp, filter_func=None):
        with open(csv_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.reader(csv_f) # use zip() below instead of DictReader for speed
            headers = next(reader)

            # generate dictionaries to insert and apply row filter if exists
            for row in reader:
                dict_row = dict(zip(headers, row))
                yield filter_func(dict_row) if filter_func else dict_row


    def load_export_survey_responses(self, input_dir):
        """
        Loads Itinerum survey responses data to the itinerum-datakit cache database.

        :param input_dir: The directory containing the `self.survey_responses_csv`
                          data file.
        """
        survey_responses_fp = os.path.join(input_dir, self.survey_responses_csv)
        survey_responses_rows = self._row_generator(survey_responses_fp, _survey_response_row_filter)
        self.db.bulk_insert(UserSurveyResponse, survey_responses_rows)


    def load_export_coordinates(self, input_dir):
        """
        Loads Itinerum coordinates data to the itinerum-datakit cache database.

        :param input_dir: The directory containing the `self.coordinates_csv`
                          data file.
        """
        logger.info('Loading coordinates .csv to db...')
        migrate(self._migrator.drop_index(Coordinate, 'coordinate_user_id'))
        coordinates_fp = os.path.join(input_dir, self.coordinates_csv)
        coordinates_rows = self._row_generator(coordinates_fp, _coordinates_row_filter)
        self.db.bulk_insert(Coordinate, coordinates_rows)
        migrate(self._migrator.add_index('coordinates', ('user_id',), False))


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
        prompt_responses_rows = self._row_generator(prompt_responses_fp, _prompts_row_filter)
        self.db.bulk_insert(PromptResponse, prompt_responses_rows)
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
        cancelled_prompt_responses_rows = self._row_generator(cancelled_prompt_responses_fp, _cancelled_prompts_row_filter)
        self.db.bulk_insert(CancelledPromptResponse, cancelled_prompt_responses_rows)

    def load_trips(self, trips_csv_fp):
        """
        Loads trips processed by the web platform itself. This is mostly useful
        for comparing current alogorithm results against the deployed platform's
        version.

        :param trips_csv_fp: The full filepath of the downloaded trips `.csv` file
                             for a survey.
        """
        logger.info('Loading detected trips .csv to db...')
        DetectedTripCoordinate.drop_table()
        DetectedTripCoordinate.create_table()
        self.db.bulk_insert(DetectedTripCoordinate, trips_csv_fp, _trips_row_filter)


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
