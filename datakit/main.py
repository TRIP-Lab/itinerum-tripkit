#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import datetime
import logging

from . import io
from . import models
from . import process
from .csvparser import CSVParser
from .database import Database, UserSurveyResponse
from .database import (Coordinate, PromptResponse, CancelledPromptResponse,
                       DetectedTripCoordinate, SubwayStationEntrance)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Itinerum(object):
    def __init__(self, config):
        self.config = config
        self.database = Database()
        self.database.db.init(config.DATABASE_FN)
        self.csv = CSVParser(self.database)

        # attach I/O functions and extensions as objects
        self.io = io
        self.process = process
        self.process.map_match.osrm(self.config)

    def setup(self, force=False):
        if force:
            self.database.drop()

        if not UserSurveyResponse.table_exists():
            self.database.create()
            self.csv.load_subway_stations(self.config.SUBWAY_STATIONS_FP)
            self.csv.load_exports(self.config.INPUT_DATA_DIR)

    # {uuid0: User0(), uuid1: User1(), ...}
    def load_all_users(self):
        all_uuids = [u.uuid for u in UserSurveyResponse.select(UserSurveyResponse.uuid)]
        users = []
        for idx, uuid in enumerate(all_uuids, start=1):
            logger.info('Loading user from database: {}/{}...'.format(idx, len(all_uuids)))
            users.append(self.database.load_user(uuid))
        return users

    def run_process(self, algorithm, users, parameters):
        output = {}
        for idx, user in enumerate(users, start=1):
            logger.info('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
            coordinates = user.coordinates.dicts()
            results = algorithm.run(coordinates, parameters=parameters)
            output[user] = results
        return output 


