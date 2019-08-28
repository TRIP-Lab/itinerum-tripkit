#!/usr/bin/env python
# Kyle Fitzsimmons, 2018-2019
import logging
from peewee import (
    Model,
    SqliteDatabase,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    TextField,
    UUIDField,
)

from .models.Trip import Trip
from .models.TripPoint import TripPoint
from .models.User import User
from .utils import UserNotFoundError

logger = logging.getLogger(__name__)

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
        self.db.create_tables(
            [
                UserSurveyResponse,
                Coordinate,
                PromptResponse,
                CancelledPromptResponse,
                DetectedTripCoordinate,
                DetectedTripDaySummary,
                SubwayStationEntrance,
            ]
        )

    def drop(self):
        """
        Drops all cache database tables.
        """
        self.db.drop_tables(
            [
                UserSurveyResponse,
                Coordinate,
                PromptResponse,
                CancelledPromptResponse,
                DetectedTripCoordinate,
                DetectedTripDaySummary,
                SubwayStationEntrance,
            ]
        )

    def delete_user_from_table(self, Model, user):
        """
        Deletes a given user's records from a table in preparation for overwriting.
        """
        Model.delete().where(Model.user == user.uuid).execute()

    def bulk_insert(self, Model, rows, chunk_size=10000):
        """
        Bulk insert an iterable of dictionaries into a supplied Peewee model by ``chunk_size``.

        :param Model:      Peewee database model of target table for inserts.
        :param rows:       Iterable list or generator of dictionaries matching
                           table model for bulk insert.
        :param chunk_size: `Optional.` Number of rows to insert per transaction.
        """
        db_rows = []
        for row in rows:
            if row:
                db_rows.append(row)
            if len(db_rows) == chunk_size:
                logger.info(f"bulk inserting {len(db_rows)} rows...")
                with self.db.atomic():
                    Model.insert_many(db_rows).execute()
                db_rows = []
        # push any remaining rows
        if db_rows:
            with self.db.atomic():
                Model.insert_many(db_rows).execute()

    def count_users(self):
        """
        Returns a count of all survey responses in cache database.
        """
        return UserSurveyResponse.select().count()

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
        if start and end:
            # TODO: add BETWEEN queries here
            raise NotImplementedError("BETWEEN queries: start and end")
        elif start:
            user.coordinates = user.coordinates.where(Coordinate.timestamp_UTC >= start)
            user.prompt_responses = user.prompt_responses.where(PromptResponse.displayed_at_UTC >= start)
            user.cancelled_prompt_responses = user.cancelled_prompt_responses.where(
                CancelledPromptResponse.displayed_at_UTC >= start
            )
            user.detected_trip_coordinates = user.detected_trip_coordinates.where(
                DetectedTripCoordinate.timestamp_UTC >= start
            )
            user.detected_trip_day_summaries = user.detected_trip_day_summaries.where(
                DetectedTripDaySummary.date >= start.date
            )
        elif end:
            user.coordinates = user.coordinates.where(Coordinate.timestamp_UTC <= end)
            user.prompt_responses = user.prompt_responses.where(PromptResponse.displayed_at_UTC <= end)
            user.cancelled_prompt_responses = user.cancelled_prompt_responses.where(
                CancelledPromptResponse.displayed_at_UTC <= end
            )
            user.detected_trip_coordinates = user.detected_trip_coordinates.where(
                DetectedTripCoordinate.timestamp_UTC <= end
            )
            user.detected_trip_day_summaries = user.detected_trip_day_summaries.where(
                DetectedTripDaySummary.date <= end.date
            )
        return user

    def load_trips(self, user, start=None, end=None):
        """
        Load the sorted trips for a given user as list.

        :param user: A database user response record with a populated
                     `detected_trip_coordinates` relation.
        """
        trips = {}
        for c in user.detected_trip_coordinates:
            if start and c.timestamp_UTC <= start:
                continue
            if end and c.timestamp_UTC >= end:
                continue

            point = TripPoint(
                database_id=c.id,
                latitude=c.latitude,
                longitude=c.longitude,
                h_accuracy=c.h_accuracy,
                distance_before=c.distance_before,
                trip_distance=c.trip_distance,
                period_before=c.period_before,
                timestamp_UTC=c.timestamp_UTC,
            )

            if c.trip_num not in trips:
                trips[c.trip_num] = Trip(num=c.trip_num, trip_code=c.trip_code)
            trips[c.trip_num].points.append(point)
        return [value for _, value in sorted(trips.items())]

    def load_trip_day_summaries(self, user):
        """
        Load the daily trip summaries for a given user as dict.

        :param user: A database user response record with a populated
                     `detected_trip_day_summaries` relation.
        """
        day_summaries = {}
        for s in user.detected_trip_day_summaries:
            day_summaries[s.date] = {
                "has_trips": s.has_trips,
                "is_complete": s.is_complete,
                "consecutive_inactive_days": s.consecutive_inactive_days,
                "inactivity_streak": s.inactivity_streak,
                "inactivity_distance": s.inactivity_distance,
                "start_latitude": s.start_point.latitude if s.start_point else None,
                "start_longitude": s.start_point.longitude if s.start_point else None,
                "end_latitude": s.end_point.latitude if s.start_point else None,
                "end_longitude": s.end_point.longitude if s.start_point else None,
            }
        return day_summaries

    def load_subway_entrances(self):
        """
        Queries cache database for all available subway entrances.
        """
        return SubwayStationEntrance.select()

    def save_trips(self, user, detected_trips, overwrite=True):
        """
        Saves detected trips from processing algorithms to cache database. This
        table will be recreated on each save by default.

        :param user:           A database user response record associate with the saved
                               trip records.
        :param detected_trips: List of labelled coordinates from a trip processing
                               algorithm.
        """

        def _trip_row_filter(trip_rows, model_fields):
            row = {}
            for trip in trip_rows:
                for point in trip.points:
                    row = {
                        "user_id": user.uuid,
                        "trip_num": trip.num,
                        "trip_code": trip.trip_code,
                        "latitude": point.latitude,
                        "longitude": point.longitude,
                        "h_accuracy": point.h_accuracy,
                        "distance_before": point.distance_before,
                        "trip_distance": point.trip_distance,
                        "period_before": point.period_before,
                        "timestamp_UTC": point.timestamp_UTC,
                    }
                    yield row

        if overwrite:
            logger.info("overwriting user trips information...")
            self.delete_user_from_table(DetectedTripCoordinate, user)

        model_fields = set(DetectedTripCoordinate._meta.sorted_field_names)
        self.bulk_insert(DetectedTripCoordinate, _trip_row_filter(detected_trips, model_fields))

    def save_trip_day_summaries(self, user, trip_day_summaries, timezone, overwrite=True):
        """
        Saves the daily summaries for detected trip days to cache database. This
        table with be recreated on each save by default.

        :param trip_day_summaries: List of daily summaries from a daily trip counts algorithm.
        """

        def _row_filter(rows, model_fields):
            for row in rows:
                dict_row = row.__dict__
                dict_row["user_id"] = user.uuid
                dict_row["timezone"] = timezone
                yield dict_row

        if not trip_day_summaries:
            logger.info(f"No daily summaries for {user.uuid}. Has trip detection been run?")
            return

        if overwrite:
            logger.info("Overwriting user daily summaries information...")
            self.delete_user_from_table(DetectedTripDaySummary, user)

        model_fields = set(DetectedTripDaySummary._meta.sorted_field_names)
        self.bulk_insert(DetectedTripDaySummary, _row_filter(trip_day_summaries, model_fields))


class BaseModel(Model):
    class Meta:
        database = deferred_db


class UserSurveyResponse(BaseModel):
    class Meta:
        table_name = "survey_responses"

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
        return self.prompts_backref.order_by(PromptResponse.displayed_at_UTC)

    @property
    def cancelled_prompts(self):
        return self.cancelled_prompts_backref.order_by(CancelledPromptResponse.displayed_at_UTC)

    @property
    def detected_trip_coordinates(self):
        return self.detected_trip_coordinates_backref.order_by(DetectedTripCoordinate.timestamp_UTC)

    @property
    def detected_trip_day_summaries(self):
        return self.detected_trip_day_summaries_backref.order_by(DetectedTripDaySummary.date)


class Coordinate(BaseModel):
    class Meta:
        table_name = "coordinates"

    user = ForeignKeyField(UserSurveyResponse, backref="coordinates_backref")
    latitude = FloatField()
    longitude = FloatField()
    altitude = FloatField(null=True)
    speed = FloatField()
    direction = FloatField(null=True)
    h_accuracy = FloatField()
    v_accuracy = FloatField()
    acceleration_x = FloatField()
    acceleration_y = FloatField()
    acceleration_z = FloatField()
    point_type = IntegerField(null=True)
    mode_detected = IntegerField(null=True)
    timestamp_UTC = DateTimeField()
    timestamp_epoch = IntegerField()


class PromptResponse(BaseModel):
    class Meta:
        table_name = "prompt_responses"

    user = ForeignKeyField(UserSurveyResponse, backref="prompts_backref")
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
        table_name = "cancelled_prompt_responses"

    user = ForeignKeyField(UserSurveyResponse, backref="cancelled_prompts_backref")
    prompt_uuid = UUIDField(unique=True)
    latitude = FloatField()
    longitude = FloatField()
    displayed_at_UTC = DateTimeField()
    cancelled_at_UTC = DateTimeField(null=True)
    is_travelling = BooleanField(null=True)


class DetectedTripCoordinate(BaseModel):
    class Meta:
        table_name = "detected_trip_coordinates"

    user = ForeignKeyField(UserSurveyResponse, backref="detected_trip_coordinates_backref")
    trip_num = IntegerField()
    trip_code = IntegerField()
    latitude = FloatField()
    longitude = FloatField()
    h_accuracy = FloatField()
    distance_before = FloatField()
    trip_distance = FloatField()
    period_before = IntegerField()
    timestamp_UTC = DateTimeField()


class DetectedTripDaySummary(BaseModel):
    class Meta:
        table_name = "detected_trip_day_summaries"

    user = ForeignKeyField(UserSurveyResponse, backref="detected_trip_day_summaries_backref")
    timezone = TextField()
    date = DateField()
    has_trips = BooleanField()
    is_complete = BooleanField()
    inactivity_distance = FloatField(null=True)
    start_point = ForeignKeyField(DetectedTripCoordinate, null=True)
    end_point = ForeignKeyField(DetectedTripCoordinate, null=True)


class SubwayStationEntrance(BaseModel):
    class Meta:
        table_name = "subway_station_entrances"
        indexes = ((("latitude", "longitude"), True),)

    latitude = FloatField()
    longitude = FloatField()
