#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from peewee import *

from . import config


db = SqliteDatabase(config.DATABASE_FN)


class BaseModel(Model):
    class Meta:
        database = db


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

