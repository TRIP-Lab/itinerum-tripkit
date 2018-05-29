#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import datetime
import logging

from . import config
from . import controllers
from . import geo
from . import models
from . import processing
from .api import MapMatcherAPI
from .database import (db, UserSurveyResponse, Coordinate, PromptResponse, CancelledPromptResponse,
                       DetectedTripCoordinate, SubwayStationEntrance)
from .parser import CSVParser


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# static utility class for simple organization of Itinerum helper functions
class Itinerum(object):
    def __init__(self):
        self.db = db
        self.db.connect()
        self.csv_parser = CSVParser(self.db)
        self.osrm = MapMatcherAPI

    def setup(self, force=False):
        if not UserSurveyResponse.table_exists() or force:
            self.db.create_tables([UserSurveyResponse, Coordinate, PromptResponse,
                                   CancelledPromptResponse, DetectedTripCoordinate,
                                   SubwayStationEntrance])
            self.csv_parser.load_data(config.INPUT_DATA_DIR)
            self.csv_parser.load_subway_stations(config.SUBWAY_STATIONS_FP)


    def load_user(self, uuid, start=None, end=None):
        return controllers.load_user_from_db(uuid, start=start, end=end)

    # {uuid0: User0(), uuid1: User1(), ...}
    def load_all_users(self):
        all_uuids = [u.uuid for u in UserSurveyResponse.select(UserSurveyResponse.uuid)]
        users = []
        for idx, uuid in enumerate(all_uuids, start=1):
            logger.info('Loading user from database: {}/{}...'.format(idx, len(all_uuids)))
            users.append(self.load_user(uuid))
        return users

    def run_trip_detection(self, algorithm, users):
        parameters = {
            'break_interval_seconds': config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
            'subway_buffer_meters': config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
            'cold_start_distance': config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
            'accuracy_cutoff_meters': config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
        }
        subway_stations = list(SubwayStationEntrance.select())
        detected_trips = []
        for idx, user in enumerate(users, start=1):
            logger.info('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
            user_coordinates = user.coordinates.dicts()
            trips, summaries = algorithm.run(parameters, subway_stations, user_coordinates)
            for trip_num, trip in trips.items():
                for c in trip:
                    c['uuid'] = user.uuid
                    detected_trips.append(c)
        return detected_trips

    def save_trips(self, detected_trips):
        controllers.save_trips(detected_trips)

