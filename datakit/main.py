#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
#
# This module implements the core Itinerum object
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
    """
    The Itinerum object provides a interface for working with
    data exported from the Itinerum platform as .csv. The object
    is passed a `config` object which should be an imported Python
    file of global variables or class with the same attributes as
    expected here.

    The Itinerum object is the entry API for loading .csv data to
    an SQLite database (used as cache), testing and running algorithms
    on the GPS data, and visualizing and exporting the results to 
    GIS-friendly formats.

    The Itinerum instannce is usually created in your main module
    like this::

        from datakit import Itinerum
        import datakit_config

        itinerum = Itinerum(config=datakit_config)
        itinerum.setup()

    :param config: An imported Python file of global variables or
                   a bare config class with the same attributes,
                   see :ref:`ConfigAnchor` for more information.

    """

    def __init__(self, config):
        self.config = config

        self._database = Database()
        self._database.db.init(config.DATABASE_FN)
        self._csv = CSVParser(self._database)

        # attach I/O functions and extensions as objects
        self._io = io
        self._process = process
        self._process.map_match.osrm = self.process.map_match.osrm(self.config)

    @property
    def csv(self):
        """
        Gives access to the :py:class:`datakit.csvparser.CSVParser` object initialized with Itinerum object.
        """
        return self._csv
    
    @property  
    def database(self):
        """
        Gives access to the cache :py:class:`datakit.database.Database` object initialized with Itinerum object.
        """
        return self._database()

    @property
    def io(self):
        """
        Gives access to the file reading and writing functions.
        """
        return self._io

    @property
    def process(self):
        """
        Gives access to the GPS point and trip processing submodules.
        """
        return self._process
    

    def setup(self, force=False):
        """
        Create the cache database tables if the UserSurveyResponse table does not exist.

        :param force: optionally supply True to force creation of a new cache database
        :type force: boolean
        """
        if force:
            self.database.drop()

        if not UserSurveyResponse.table_exists():
            self.database.create()
            self.csv.load_subway_stations(self.config.SUBWAY_STATIONS_FP)
            self.csv.load_exports(self.config.INPUT_DATA_DIR)

    def load_all_users(self):
        """
        Returns all available users as ``<User>`` objects from the database
        :rtype: list of ``<User>`` objects
        """
        all_uuids = [u.uuid for u in UserSurveyResponse.select(UserSurveyResponse.uuid)]
        users = []
        for idx, uuid in enumerate(all_uuids, start=1):
            logger.info('Loading user from database: {}/{}...'.format(idx, len(all_uuids)))
            users.append(self.database.load_user(uuid))
        return users

    # Deprecated: we can just call the algorithms directly
    def run_process(self, algorithm, users, parameters):
        output = {}
        for idx, user in enumerate(users, start=1):
            logger.info('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
            coordinates = user.coordinates.dicts()
            results = algorithm.run(coordinates, parameters=parameters)
            output[user] = results
        return output 
