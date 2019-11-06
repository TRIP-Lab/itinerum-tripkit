#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
import csv
from datetime import datetime
import logging
import os
from playhouse.migrate import migrate, SqliteMigrator

from .common import _generate_null_survey, _load_subway_stations
from ..database import (
    UserSurveyResponse,
    Coordinate,
    PromptResponse,
    CancelledPromptResponse,
    DetectedTripCoordinate,
    SubwayStationEntrance,
)

logger = logging.getLogger('itinerum-tripkit.csvparser.itinerum')


# .csv row filters for parsing Itinerum exports to database models
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
    # reject invalid rows
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
    row['timestamp_UTC'] = row.pop('timestamp')
    return row


# .csv parsing
class ItinerumCSVParser(object):
    '''
    Parses Itinerum platform csv files and loads to them to a cache database.

    :param database: Open Peewee connection the cache database
    '''

    def __init__(self, database):
        self.db = database
        self._migrator = SqliteMigrator(database.db)
        self.cancelled_prompt_responses_csv = 'cancelled_prompts.csv'
        self.coordinates_csv = 'coordinates.csv'
        self.prompt_responses_csv = 'prompt_responses.csv'
        self.survey_responses_csv = 'survey_responses.csv'
        # attach common functions
        self.load_subway_stations = _load_subway_stations

    def _get(self, row, key, cast_func=None):
        value = row.get(key)
        if value:
            value = value.strip()
            if cast_func:
                return cast_func(value)
            return value

    # read .csv file, apply filter and yield row
    @staticmethod
    def _row_generator(csv_fp, filter_func=None):
        with open(csv_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.reader(csv_f)  # use zip() below instead of DictReader for speed
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
        _generate_null_survey(input_dir, self.coordinates_csv)

    def load_export_survey_responses(self, input_dir):
        '''
        Loads Itinerum survey responses data to the cache database.

        :param input_dir: The directory containing the `self.survey_responses_csv` data file.
        '''
        survey_responses_fp = os.path.join(input_dir, self.survey_responses_csv)
        survey_responses_rows = self._row_generator(survey_responses_fp, _survey_response_row_filter)
        self.db.bulk_insert(UserSurveyResponse, survey_responses_rows)

    def load_export_coordinates(self, input_dir):
        '''
        Loads Itinerum coordinates data to the cache database.

        :param input_dir: The directory containing the `self.coordinates_csv` data file.
        '''
        logger.info("Loading coordinates .csv to db...")
        migrate(self._migrator.drop_index(Coordinate, 'coordinate_user_id'))
        coordinates_fp = os.path.join(input_dir, self.coordinates_csv)
        coordinates_rows = self._row_generator(coordinates_fp, _coordinates_row_filter)
        self.db.bulk_insert(Coordinate, coordinates_rows)
        migrate(self._migrator.add_index('coordinates', ('user_id',), False))

    def load_export_prompt_responses(self, input_dir):
        '''
        Loads Itinerum prompt responses data to the cache database. For each .csv row, the data 
        is fetched by column name if it exists and cast to appropriate types as set in the database.

        :param input_dir: The directory containing the `self.prompt_responses.csv` data file.
        '''
        logger.info("Loading prompt responses .csv to db...")
        migrate(self._migrator.drop_index(PromptResponse, 'promptresponse_user_id'))
        prompt_responses_fp = os.path.join(input_dir, self.prompt_responses_csv)
        prompt_responses_rows = self._row_generator(prompt_responses_fp, _prompts_row_filter)
        self.db.bulk_insert(PromptResponse, prompt_responses_rows)
        migrate(self._migrator.add_index('prompt_responses', ('user_id',), False))

    def load_export_cancelled_prompt_responses(self, input_dir):
        '''
        Loads Itinerum cancelled prompt responses data to the cache database. For each .csv row, the data
        is fetched by column name if it exists and cast to appropriate types as set in the database.

        :param input_dir: The directory containing the `self.cancelled_prompt_responses.csv` data file.
        '''
        logger.info("Loading cancelled prompt responses .csv to db...")
        cancelled_prompt_responses_fp = os.path.join(input_dir, self.cancelled_prompt_responses_csv)
        cancelled_prompt_responses_rows = self._row_generator(
            cancelled_prompt_responses_fp, _cancelled_prompts_row_filter
        )
        self.db.bulk_insert(CancelledPromptResponse, cancelled_prompt_responses_rows)

    def load_trips(self, trips_csv_fp):
        '''
        Loads trips processed by the web platform itself. This is mostly useful for comparing current algorithm
        results against the deployed platform's version.

        :param trips_csv_fp: The full filepath of the downloaded trips `.csv` file for a survey.
        '''
        logger.info("Loading detected trips .csv to db...")
        DetectedTripCoordinate.drop_table()
        DetectedTripCoordinate.create_table()
        self.db.bulk_insert(DetectedTripCoordinate, trips_csv_fp, _trips_row_filter)
