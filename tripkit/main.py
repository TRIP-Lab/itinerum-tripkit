#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
#
# This module implements the core TripKit object
from datetime import datetime
import logging
import time

from .io import IO
from . import models
from . import process
from .csvparser import ItinerumCSVParser, QstarzCSVParser
from .database import Database, UserSurveyResponse
from .database import Coordinate, PromptResponse, CancelledPromptResponse, DetectedTripCoordinate, SubwayStationEntrance


logger = logging.getLogger('itinerum-tripkit.main')


class TripKit(object):
    '''
    The base TripKit object provides an interface for working with .csv data exported from
    the Itinerum platform or QStarz GPS data loggers. The object is passed the `config` at
    initialization which should be an imported Python file of global variables or class with
    the same attributes as expected here.

    This TripKit object is the entry API for loading .csv data to an SQLite database (used as cache),
    running algorithms on the GPS data, and visualizing or exporting the results to GIS-friendly formats.

    The TripKit instance is usually created in your main module like this::

        from tripkit import TripKit
        import tripkit_config

        tripkit = TripKit(config=tripkit_config)
        tripkit.setup()

    :param config: An imported Python file of global variables or
                   a bare config class with the same attributes,
                   see :ref:`ConfigAnchor` for more information.

    '''

    def __init__(self, config):
        self.config = config

        self._database = Database(self.config)
        self._csv = self._init_csv_parser()

        # attach I/O functions and extensions as objects
        self._io = IO(self.config)
        self._process = process
        self._process.map_match.osrm(self.config)

    def _init_csv_parser(self):
        if self.config.INPUT_DATA_TYPE == 'itinerum':
            return ItinerumCSVParser(self._database)
        if self.config.INPUT_DATA_TYPE == 'qstarz':
            return QstarzCSVParser(self.config, self._database)
        raise Exception(
            f"Input data type not recognized: {self.config.INPUT_DATA_TYPE} Valid options: itinerum, qstarz"
        )

    @property
    def csv(self):
        '''
        Provides access to the CSV parser objects.
        '''
        return self._csv

    @property
    def database(self):
        '''
        Provides access to the cache database object.
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

        :param force:                Supply `True` to force creation of a new cache database
        :param generate_null_survey: Supply `True` to generate an empty survey responses table
                                     for coordinates-only data

        :type force:                 boolean, optional
        :type generate_null_survey:  boolean, optional
        '''
        if force:
            self.database.drop()

        if not UserSurveyResponse.table_exists():
            self.database.create()
            if getattr(self.config, 'SUBWAY_STATIONS_FP', None):
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
                self.csv.load_user_locations(self.config.INPUT_DATA_DIR)

    def check_setup(self):
        '''
        Raises exception if `UserSurveyResponse` table is not found in database.
        '''
        survey_responses_table_exists = self.database.db.table_exists(UserSurveyResponse._meta.table_name)
        if not survey_responses_table_exists:
            raise Exception(
                "UserSurveyResponse table does not exist in database. Please re-run setup " "and try again."
            )

    def load_users(self, uuid=None, load_trips=True, load_locations=True, limit=None, start=None, end=None):
        '''
        Returns all available users as :py:class:`tripkit.models.User` objects from the database

        :param uuid:           Supply an individual user's UUID to load
        :param load_trips:     Supply False to disable automatic loading of trips to
                               :py:class:`tripkit.models.User` objects on initialization
        :param load_locations: Supple False to disable automatic loading of activity locations to
                               :py:class:`tripkit.models.User` objects on initialization
        :param limit:          Maximum number of users to load
        :param start:          Mininum timestamp bounds (inclusive) for loading user coordinate and
                               prompts data
        :param end:            Maximum timestamp bounds (inclusive) for loading user coordinate and
                               prompts data

        :type uuid:            string, optional
        :type load_trips:      boolean, optional
        :type load_locations:  boolean, optional
        :type limit:           integer, optional
        :type start:           datetime, optional
        :type end:             datetime, optional

        :rtype: list of :py:class:`tripkit.models.User`
        '''
        self.check_setup()

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
            if user.coordinates.count() == 0:
                logger.info(f"User {idx} has no points, skipped.")
                continue
            if load_trips:
                user.trips = self.database.load_trips(user, start=start, end=end)
            if load_locations:
                user.activity_locations = self.database.load_activity_locations(user)
            if return_one:
                return user
            users.append(user)
        return users

    def load_user_by_orig_id(self, orig_id, load_trips=True, start=None, end=None):
        '''
        Returns all available users as :py:class:`tripkit.models.User` objects from the database

        :param orig_id:    An individual user's original ID from a non-Itinerum dataset to load
        :param load_trips: Supply False to disable automatic loading of trips to
                           py:class:`tripkit.models.User` objects on initialization
        :param start:      Miminum timestamp bounds (inclusive) for loading user coordinate and
                           prompts data
        :param end:        Maximum timestamp bounds (inclusive) for loading user coordinate and
                           prompts data

        :type uuid:        string, optional
        :type load_trips:  boolean, optional
        :type start:       datetime, optional
        :type end:         datetime, optional

        :rtype: :py:class:`tripkit.models.User`
        '''
        self.check_setup()

        uuid = self.database.get_uuid(orig_id)
        if uuid:
            user = self.database.load_user(uuid, start=start, end=end)
            user.activity_locations = self.database.load_activity_locations(user)
            if load_trips:
                user.trips = self.database.load_trips(user, start=start, end=end)
            return user
