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


logging.basicConfig(level=logging.DEBUG)
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
        self._process.map_match.osrm(self.config)

    @property
    def csv(self):
        """
        Gives access to the :py:class:`datakit.csvparser.CSVParser` object
        initialized with Itinerum object.
        """
        return self._csv

    @property
    def database(self):
        """
        Gives access to the cache :py:class:`datakit.database.Database` object
        initialized with Itinerum object.
        """
        return self._database

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

    def setup(self, force=False, generate_null_survey=False):
        """
        Create the cache database tables if the UserSurveyResponse table does not exist.

        :param force:                optionally supply True to force creation
                                     of a new  cache database
        :param generate_null_survey: optionally supply True to generate an empty
                                     survey responses table for coordinates-only data

        :type force:                 boolean
        :type generate_null_survey:  boolean
        """
        if force:
            self.database.drop()

        if not UserSurveyResponse.table_exists():
            self.database.create()
            self.csv.load_subway_stations(self.config.SUBWAY_STATIONS_FP)
            if generate_null_survey is False:
                self.csv.load_export_survey_responses(self.config.INPUT_DATA_DIR)
            else:
                self.csv.generate_null_survey(self.config.INPUT_DATA_DIR)
            self.csv.load_export_coordinates(self.config.INPUT_DATA_DIR)
            self.csv.load_export_prompt_responses(self.config.INPUT_DATA_DIR)
            self.csv.load_export_cancelled_prompt_responses(self.config.INPUT_DATA_DIR)

    def load_users(self, uuid=None, load_trips=True, limit=None, start=None, end=None):
        """
        Returns all available users as ``<User>`` objects from the database
        :rtype: list of ``<User>`` objects

        :param uuid:       Optionally supply an individual user's UUID to load
        :param load_trips: Optionally supply False to disable automatic loading
                           of trips to User objects on initialization
        :param limit:      Optionally supply a maximum number of users to load
        :param start:      Optionally supply a miminum timestamp bounds (inclusive)
                           for loading user coordinate and prompts data
        :param end:        Optionally supply a maximum timestamp bounds (inclusive)
                           for loading user coordinate and prompts data

        :type uuid:        string
        :type load_trips:  boolean
        :type limit:       integer
        :type start:       datetime
        :type end:         datetime
        """
        return_one = uuid is not None
        if uuid:
            uuids = [uuid]
        else:
            uuids = [u.uuid for u in UserSurveyResponse.select(UserSurveyResponse.uuid)]
            if limit:
                uuids = uuids[:limit]

        users = []
        for idx, uuid in enumerate(uuids, start=1):
            logger.info(f"Loading user from database: {idx}/{len(uuids)}...")

            user = self.database.load_user(uuid, start=start, end=end)
            if load_trips:
                user.trips = self.database.load_trips(user, start=start, end=end)
            if return_one:
                return user
            users.append(user)
        return users
