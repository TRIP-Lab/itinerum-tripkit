#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from peewee import *

from .models.Trip import Trip
from .models.TripPoint import TripPoint
from .models.User import User
from .utils import UserNotFoundError

# globally create a single database connection for SQLite
deferred_db = SqliteDatabase(None)


class Database(object):
    """
    Handles itinerum-datakit interactions with the cached database using peewee. `Note: This 
    may soon transition to SQLAlchemy to maintain direct compatibility with the Itinerum API 
    code base.`
    """

    def __init__(self):
        self.db = deferred_db

    def create(self):
        """
        Creates all the tables necessary for the itinerum-datakit cache database.
        """
        self.db.create_tables([UserSurveyResponse, Coordinate, PromptResponse,
                               CancelledPromptResponse, DetectedTripCoordinate,
                               SubwayStationEntrance])


    def drop(self):
        """
        Drops all cache database tables.
        """
        self.db.drop_tables([UserSurveyResponse, Coordinate, PromptResponse,
                             CancelledPromptResponse, DetectedTripCoordinate,
                             SubwayStationEntrance])


    def load_user(self, uuid, start=None, end=None):
        """
        Loads user by ``uuid`` to an itinerum-datakit :py:class:`User` object.

        :param uuid:  A specific user's UUID from within an Itinerum survey.
        :param start: `Optional.` Naive datetime object (set within UTC) for
                      selecting a user's coordinates start period.
        :param end:   `Optional.` Naive datetime object (set within UTC) for
                      selecting a user's coordinates end period.
        """
        db_user = UserSurveyResponse.get_or_none(uuid=uuid)
        if not db_user:
            raise UserNotFoundError(uuid)
        
        user = User(db_user)
        if start:
            user.coordinates = user.coordinates.where(Coordinate.timestamp_UTC >= start)
            user.prompt_responses = user.prompt_responses.where(PromptResponse.displayed_at_UTC >= start)
            user.cancelled_prompt_responses = (user.cancelled_prompt_responses
                                                   .where(CancelledPromptResponse.displayed_at_UTC >= start))
        if end:
            user.coordinates = user.coordinates.where(Coordinate.timestamp_UTC <= end)
            user.prompt_responses = user.prompt_responses.where(PromptResponse.displayed_at_UTC <= end)
            user.cancelled_prompt_responses = (user.cancelled_prompt_responses
                                                   .where(CancelledPromptResponse.displayed_at_UTC <= end))

        for c in db_user.detected_trip_coordinates:
            if start and c.timestamp_UTC <= start:
                continue
            if end and c.timestamp_UTC >= end:
                continue

            point = TripPoint(latitude=c.latitude,
                              longitude=c.longitude,
                              h_accuracy=c.h_accuracy,
                              timestamp_UTC=c.timestamp_UTC)

            if not c.trip_num in user.trips:
                user.trips[c.trip_num] = Trip(num=c.trip_num, trip_code=c.trip_code)
            user.trips[c.trip_num].points.append(point)
        return user


    def load_subway_entrances(self):
        """
        Queries cache database for all available subway entrances.
        """
        return SubwayStationEntrance.select()


    def save_trips(self, detected_trips):
        """
        Saves detected trips from processing algorithms to cache database. This
        table will be recreated on each save.
        
        :param detected_trips: List of labelled coordinates from a trip processing
                               algorithm.
        """
        DetectedTripCoordinate.drop_table()
        DetectedTripCoordinate.create_table()
        for c in detected_trips:
            # TODO: this would be more consistent if trip coordinates
            # were named tuples for dot attributes
            DetectedTripCoordinate.create(user=c['uuid'],
                                          trip_num=c['trip'],
                                          trip_code=c['trip_code'],
                                          latitude=c['latitude'],
                                          longitude=c['longitude'],
                                          h_accuracy=c['h_accuracy'],
                                          timestamp_UTC=c['timestamp_UTC'])




class BaseModel(Model):
    class Meta:
        database = deferred_db


class UserSurveyResponse(BaseModel):
    class Meta:
        table_name = 'survey_responses'

    uuid = UUIDField(unique=True, primary_key=True)
    created_at_UTC = DateTimeField()
    modified_at_UTC = DateTimeField()
    itinerum_version = CharField()
    location_home_lat = FloatField()
    location_home_lon = FloatField()
    location_study_lat = FloatField(null=True)
    location_study_lon = FloatField(null=True)
    location_work_lat = FloatField(null=True)
    location_work_lon = FloatField(null=True)
    member_type = CharField()
    model = CharField()
    os = CharField()
    os_version = CharField()
    travel_mode_study_primary = CharField(null=True)
    travel_mode_study_secondary = CharField(null=True)
    travel_mode_work_primary = CharField(null=True)
    travel_mode_work_secondary = CharField(null=True)


class Coordinate(BaseModel):
    class Meta:
        table_name = 'coordinates'

    user = ForeignKeyField(UserSurveyResponse, backref='coordinates')
    latitude = FloatField()
    longitude = FloatField()
    altitude = FloatField(null=True)
    speed = FloatField()
    h_accuracy = FloatField()
    v_accuracy = FloatField()
    acceleration_x = FloatField()
    acceleration_y = FloatField()
    acceleration_z = FloatField()
    mode_detected = IntegerField(null=True)
    timestamp_UTC = DateTimeField()


class PromptResponse(BaseModel):
    class Meta:
        table_name = 'prompt_responses'

    user = ForeignKeyField(UserSurveyResponse, backref='prompts')
    prompt_uuid = UUIDField()
    prompt_num = IntegerField()
    response = TextField()
    latitude = FloatField()
    longitude = FloatField()
    displayed_at_UTC = DateTimeField()
    recorded_at_UTC = DateTimeField()
    edited_at_UTC = DateTimeField()


class CancelledPromptResponse(BaseModel):
    class Meta:
        table_name = 'cancelled_prompt_responses'

    user = ForeignKeyField(UserSurveyResponse, backref='cancelled_prompts')
    prompt_uuid = UUIDField(unique=True)
    latitude = FloatField()
    longitude = FloatField()
    displayed_at_UTC = DateTimeField()
    cancelled_at_UTC = DateTimeField(null=True)
    is_travelling = BooleanField(null=True)


class DetectedTripCoordinate(BaseModel):
    class Meta:
        table_name = 'detected_trip_coordinates'

    user = ForeignKeyField(UserSurveyResponse, backref='detected_trip_coordinates')
    trip_num = IntegerField()
    trip_code = IntegerField()
    latitude = FloatField()
    longitude = FloatField()
    h_accuracy = FloatField()
    timestamp_UTC = DateTimeField()


class SubwayStationEntrance(BaseModel):
    class Meta:
        table_name = 'subway_station_entrances'
        indexes = (
            (('latitude', 'longitude'), True),
        )

    latitude = FloatField()
    longitude = FloatField()

