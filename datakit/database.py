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

        # sort trip coordinates into list of Trips
        trips = {}
        for c in db_user.detected_trip_coordinates:
            if start and c.timestamp_UTC <= start:
                continue
            if end and c.timestamp_UTC >= end:
                continue

            point = TripPoint(latitude=c.latitude,
                              longitude=c.longitude,
                              h_accuracy=c.h_accuracy,
                              timestamp_UTC=c.timestamp_UTC,
                              database_id=c.id)

            if not c.trip_num in trips:
                trips[c.trip_num] = Trip(num=c.trip_num, trip_code=c.trip_code)
            trips[c.trip_num].points.append(point)
        user.trips = [value for key, value in sorted(trips.items())]
        
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
        datasource = []
        for c in detected_trips:
            # TODO: this would be more consistent if trip coordinates
            # were named tuples for dot attributes
            datasource.append({
                'user': c['uuid'],
                'trip_num': c['trip'],
                'trip_code': c['trip_code'],
                'latitude': c['latitude'],
                'longitude': c['longitude'],
                'h_accuracy': c['h_accuracy'],
                'timestamp_UTC': c['timestamp_UTC']
            })

        with self.db.atomic():
            for idx in range(0, len(datasource), 80):
                DetectedTripCoordinate.insert_many(datasource[idx:idx+80]).execute()

    def save_trip_day_summaries(self, trip_day_summaries):
        """
        Saves the daily summaries for detected trip days to cache database. This
        table with be recreated on each save.

        :param trip_day_summaries: List of daily summaries from a daily trip counts algorithm.
        """
        DetectedTripDaySummary.drop_table()
        DetectedTripDaySummary.create_table()

        for s in trip_day_summaries:
            start_point_id, end_point_id = None, None
            if s['start_point']:
                start_point_id = s['start_point'].database_id
                end_point_id = s['end_point'].database_id
            DetectedTripDaySummary.create(user=s['uuid'],
                                          date_UTC=s['date_UTC'],
                                          has_trips=s['has_trips'],
                                          start_point=start_point_id,
                                          end_point=end_point_id,
                                          is_complete=s['is_complete'])


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

    @property
    def coordinates(self):
        return self.coordinates_backref.order_by(Coordinate.timestamp_UTC)

    @property
    def prompts(self):
        return self.prompts_backref
    
    @property
    def cancelled_prompts(self):
        return self.cancelled_prompts_backref

    @property
    def detected_trip_coordinates(self):
        return self.detected_trip_coordinates_backref.order_by(DetectedTripCoordinate.timestamp_UTC)

    @property
    def detected_trip_day_summaries(self):
        return self.detected_trip_day_summaries_backref.order_by(DetectedTripDaySummary.trip_num)
    


class Coordinate(BaseModel):
    class Meta:
        table_name = 'coordinates'

    user = ForeignKeyField(UserSurveyResponse, backref='coordinates_backref')
    latitude = FloatField()
    longitude = FloatField()
    altitude = FloatField(null=True)
    speed = FloatField()
    h_accuracy = FloatField()
    v_accuracy = FloatField()
    acceleration_x = FloatField(null=True)
    acceleration_y = FloatField(null=True)
    acceleration_z = FloatField(null=True)
    mode_detected = IntegerField(null=True)
    timestamp_UTC = DateTimeField()


class PromptResponse(BaseModel):
    class Meta:
        table_name = 'prompt_responses'

    user = ForeignKeyField(UserSurveyResponse, backref='prompts_backref')
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

    user = ForeignKeyField(UserSurveyResponse, backref='cancelled_prompts_backref')
    prompt_uuid = UUIDField(unique=True)
    latitude = FloatField()
    longitude = FloatField()
    displayed_at_UTC = DateTimeField()
    cancelled_at_UTC = DateTimeField(null=True)
    is_travelling = BooleanField(null=True)


class DetectedTripCoordinate(BaseModel):
    class Meta:
        table_name = 'detected_trip_coordinates'

    user = ForeignKeyField(UserSurveyResponse, backref='detected_trip_coordinates_backref')
    trip_num = IntegerField()
    trip_code = IntegerField()
    latitude = FloatField()
    longitude = FloatField()
    h_accuracy = FloatField()
    timestamp_UTC = DateTimeField()


class DetectedTripDaySummary(BaseModel):
    class Meta:
        table_name = 'detected_trip_day_summaries'

    user = ForeignKeyField(UserSurveyResponse, backref='detected_trip_day_summaries_backref')
    date_UTC = DateField()
    has_trips = BooleanField()
    start_point = ForeignKeyField(DetectedTripCoordinate, null=True)
    end_point = ForeignKeyField(DetectedTripCoordinate, null=True)
    is_complete = BooleanField()


class SubwayStationEntrance(BaseModel):
    class Meta:
        table_name = 'subway_station_entrances'
        indexes = (
            (('latitude', 'longitude'), True),
        )

    latitude = FloatField()
    longitude = FloatField()

