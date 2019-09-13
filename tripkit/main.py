#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
#
# This module implements the core Itinerum object
from datetime import datetime
import logging

from . import io
from . import models
from . import process
from .csvparser import ItinerumCSVParser, QstarzCSVParser
from .database import Database, UserSurveyResponse
from .database import Coordinate, PromptResponse, CancelledPromptResponse, DetectedTripCoordinate, SubwayStationEntrance

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Itinerum(object):
    '''
    The vase Itinerum object provides an interface for working with
    .csv data exported from the Itinerum platform. The object
    is passed the `config` at initialization which should be an imported
    Python file of global variables or class with the same attributes as
    expected here.

    This Itinerum object is the entry API for loading .csv data to
    an SQLite database (used as cache), running algorithms on the GPS data,
    and visualizing or exporting the results to GIS-friendly formats.

    The Itinerum instance is usually created in your main module
    like this::

        from tripkit import Itinerum
        import tripkit_config

        itinerum = Itinerum(config=tripkit_config)
        itinerum.setup()

    :param config: An imported Python file of global variables or
                   a bare config class with the same attributes,
                   see :ref:`ConfigAnchor` for more information.

    '''

    def __init__(self, config):
        self.config = config

        self._database = Database()
        self._database.db.init(config.DATABASE_FN)
        self._csv = self._init_csv_parser()

        # attach I/O functions and extensions as objects
        self._io = io
        self._process = process
        self._process.map_match.osrm(self.config)

    def _init_csv_parser(self):
        if self.config.INPUT_DATA_TYPE == 'itinerum':
            return ItinerumCSVParser(self._database)
        if self.config.INPUT_DATA_TYPE == 'qstarz':
            return QstarzCSVParser(self._database, self.config.INPUT_DATA_DIR)
        raise Exception(
            f"Input data type not recognized: {self.config.INPUT_DATA_TYPE} Valid options: itinerum, qstarz"
        )

    @property
    def csv(self):
        '''
        Provides access to the :py:class:`tripkit.csvparser` objects.
        '''
        return self._csv

    @property
    def database(self):
        '''
        Provides access to the cache :py:class:`tripkit.database.Database` object.
        '''
        return self._database

    @property
    def io(self):
        '''
        Provides access to the file reading and writing functions.
        '''
        return self._io

    @property
    def process(self):
        '''
        Provides access to the GPS point and trip processing algorithm submodules.
        '''
        return self._process

    def setup(self, force=False, generate_null_survey=False):
        '''
        Create the cache database tables if the ``UserSurveyResponse`` table does not exist.

        :param force:                Supply True to force creation of a new cache database
        :param generate_null_survey: Supply True to generate an empty survey responses table
                                     for coordinates-only data

        :type force:                 boolean, optional
        :type generate_null_survey:  boolean, optional
        '''
        if force:
            self.database.drop()

        if not UserSurveyResponse.table_exists():
            self.database.create()
            self.csv.load_subway_stations(self.config.SUBWAY_STATIONS_FP)

            if self.config.INPUT_DATA_TYPE == 'itinerum':
                if generate_null_survey is False:
                    self.csv.load_export_survey_responses(self.config.INPUT_DATA_DIR)
                else:
                    self.csv.generate_null_survey(self.config.INPUT_DATA_DIR)
                self.csv.load_export_coordinates(self.config.INPUT_DATA_DIR)
                self.csv.load_export_prompt_responses(self.config.INPUT_DATA_DIR)
                self.csv.load_export_cancelled_prompt_responses(self.config.INPUT_DATA_DIR)
            elif self.config.INPUT_DATA_TYPE == 'qstarz':
                self.csv.generate_null_survey(self.config.INPUT_DATA_DIR)
                self.csv.load_export_coordinates(self.config.INPUT_DATA_DIR)

    def load_users(self, uuid=None, load_trips=True, limit=None, start=None, end=None):
        '''
        Returns all available users as :py:class:`tripkit.models.User` objects from the database

        :param uuid:       Supply an individual user's UUID to load
        :param load_trips: Supply False to disable automatic loading of trips to
                           py:class:`tripkit.models.User` objects on initialization
        :param limit:      Supply a maximum number of users to load
        :param start:      Supply a miminum timestamp bounds (inclusive) for loading user
                           coordinate and prompts data
        :param end:        Supply a maximum timestamp bounds (inclusive) for loading user
                           coordinate and prompts data

        :type uuid:        string, optional
        :type load_trips:  boolean, optional
        :type limit:       integer, optional
        :type start:       datetime, optional
        :type end:         datetime, optional

        :rtype: list of :py:class:`tripkit.models.User`
        '''
        if uuid:
            uuids = [uuid]
        else:
            uuids = [u.uuid for u in UserSurveyResponse.select(UserSurveyResponse.uuid)]
            if limit:
                uuids = uuids[:limit]

        users = []
        return_one = uuid is not None
        for idx, _uuid in enumerate(uuids, start=1):
            logger.info(f"Loading user from database: {idx}/{len(uuids)}...")

            user = self.database.load_user(_uuid, start=start, end=end)
            if load_trips:
                user.trips = self.database.load_trips(user, start=start, end=end)
            if return_one:
                return user
            users.append(user)
        return users
