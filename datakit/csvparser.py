#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
import csv
import logging
import os


from .database import (UserSurveyResponse, Coordinate, PromptResponse, CancelledPromptResponse,
                       DetectedTripCoordinate, SubwayStationEntrance)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVParser(object):

    def __init__(self, database):
        self.db = database.db
        self.cancelled_prompt_responses_csv = 'cancelled_prompts.csv'
        self.coordinates_csv = 'coordinates.csv'
        self.prompt_responses_csv = 'prompt_responses.csv'
        self.survey_responses_csv = 'survey_responses.csv'


    def get(self, row, key, cast_func=None):
        value = row.get(key).strip()
        if value:
            if cast_func:
                return cast_func(value)
            return value


    def load_exports(self, input_dir, **kwargs):
        logger.info('Loading survey responses .csv to db...')
        survey_responses_fp = os.path.join(input_dir, self.survey_responses_csv)
        with open(survey_responses_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                UserSurveyResponse.create(uuid=row['uuid'],
                                          created_at_UTC=row['created_at_UTC'],
                                          modified_at_UTC=row['modified_at_UTC'],
                                          itinerum_version=row['itinerum_version'],
                                          location_home_lat=self.get(row, 'location_home_lat', cast_func=float),
                                          location_home_lon=self.get(row, 'location_home_lon', cast_func=float),
                                          location_study_lat=self.get(row, 'location_study_lat', cast_func=float),
                                          location_study_lon=self.get(row, 'location_study_lon', cast_func=float),
                                          location_work_lat=self.get(row, 'location_work_lat', cast_func=float),
                                          location_work_lon=self.get(row, 'location_work_lon', cast_func=float),
                                          member_type=row['member_type'],
                                          model=row['model'],
                                          os=row['os'],
                                          os_version=row['os_version'],
                                          travel_mode_study_primary=self.get(row, 'travel_mode_study'),
                                          travel_mode_study_secondary=self.get(row, 'travel_mode_alt_study'),
                                          travel_mode_work_primary=self.get(row, 'travel_mode_work'),
                                          travel_mode_work_secondary=self.get(row, 'travel_mode_alt_work'))

        logger.info('Loading coordinates .csv to db...')
        coordinates_fp = os.path.join(input_dir, self.coordinates_csv)
        with open(coordinates_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.DictReader(csv_f)
            
            # wrap in single transaction for faster insert
            # (this can be made faster with a bulk insert: http://docs.peewee-orm.com/en/latest/peewee/querying.html#bulk-inserts)
            with self.db.atomic():
                for row in reader:
                    Coordinate.create(user=row['uuid'],
                                      latitude=float(row['latitude']),
                                      longitude=float(row['longitude']),
                                      altitude=self.get(row, 'altitude', float),
                                      speed=self.get(row, 'speed', float),
                                      h_accuracy=float(row['h_accuracy']),
                                      v_accuracy=self.get(row, 'v_accuracy', float),
                                      acceleration_x=self.get(row, 'acceleration_x', float),
                                      acceleration_y=self.get(row, 'acceleration_y', float),
                                      acceleration_z=self.get(row, 'acceleration_z', float),
                                      mode_detected=self.get(row, 'mode_detected', int),
                                      timestamp_UTC=row['timestamp_UTC'])

        logger.info('Loading prompt responses .csv to db...')
        prompt_responses_fp = os.path.join(input_dir, self.prompt_responses_csv)
        with open(prompt_responses_fp, 'r', encoding='utf-8-sig') as csv_f:
            reader = csv.DictReader(csv_f)

            for row in reader:
                PromptResponse.create(user=row['uuid'],
                                      prompt_uuid=row['prompt_uuid'],
                                      prompt_num=int(row['prompt_num']),
                                      response=row['response'],
                                      latitude=float(row['latitude']),
                                      longitude=float(row['longitude']),
                                      displayed_at_UTC=row['displayed_at_UTC'],
                                      recorded_at_UTC=row['recorded_at_UTC'],
                                      edited_at_UTC=row['edited_at_UTC'])

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
                                               cancelled_at_UTC=self.get(row, 'cancelled_at_UTC'),
                                               is_travelling=self.get(row, 'is_travelling'))


    def load_trips(self, trips_csv_fp):
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
                                              timestamp_UTC=row['timestamp'],
                                              trip_code=int(row['trip_code']))


    def load_subway_stations(self, subway_stations_csv_fp):
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
