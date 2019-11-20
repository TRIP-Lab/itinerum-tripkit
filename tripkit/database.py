#!/usr/bin/env python
# Kyle Fitzsimmons, 2018-2019
from datetime import datetime
import itertools
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
import utm
import uuid

from .models.DaySummary import DaySummary
from .models.ActivityLocation import ActivityLocation
from .models.Trip import Trip
from .models.TripPoint import TripPoint
from .models.User import User
from .utils import geo
from .utils.misc import UserNotFoundError, temp_path

logger = logging.getLogger('itinerum-tripkit.database')

# globally create a single database connection for SQLite
deferred_db = SqliteDatabase(None)


class Database(object):
    '''
    Handles itinerum-tripkit interactions with the cached database using peewee.
    '''

    def __init__(self, config):
        self.config = config
        database_fp = temp_path(f'{self.config.SURVEY_NAME}.sqlite')

        self.db = deferred_db
        self.db.init(database_fp)

    def create(self):
        '''
        Creates all the tables necessary for the itinerum-tripkit cache database.
        '''
        self.db.create_tables(
            [
                UserSurveyResponse,
                Coordinate,
                PromptResponse,
                CancelledPromptResponse,
                DetectedTripCoordinate,
                DetectedTripDaySummary,
                SubwayStationEntrance,
                UserLocation,
            ]
        )

    def drop(self):
        '''
        Drops all cache database tables.
        '''
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
        '''
        Deletes a given user's records from a table in preparation for overwriting.
        '''
        Model.delete().where(Model.user == user.uuid).execute()

    def bulk_insert(self, Model, rows, chunk_size=50000):
        '''
        Bulk insert an iterable of dictionaries into a supplied Peewee model by ``chunk_size``.

        :param Model:      Peewee database model of target table for inserts.
        :param rows:       Iterable of dictionaries matching table model for bulk insert.
        :param chunk_size: Number of rows to insert per transaction.

        :type chunk_size:  int, optional
        :type rows:        list
        '''
        # Note: Peewee runs into "TOO MANY SQL VARIABLES" limits across systems with similar
        # versions of Python. The alternative below is to write the bulk insert operations using
        # the base sqlite3 library directly.
        conn = self.db.connection()
        cur = conn.cursor()
        table_name = Model._meta.table_name
        columns = list(Model._meta.columns.keys())
        if 'id' in columns:
            columns.remove('id')

        chunk = []
        columns_str = ','.join(columns)
        values_str = ','.join(['?'] * len(columns))
        query = f'''INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});'''
        rows_inserted = 0
        inserted_row_ids = []
        cur.execute('''BEGIN TRANSACTION;''')
        for row in rows:
            if not row:
                continue

            # transform uuids to the hex representation used by peewee
            if table_name == 'survey_responses':
                row['uuid'] = uuid.UUID(hex=row['uuid']).hex
                row.setdefault('orig_id', None)
            elif 'uuid' in row:
                row['user_id'] = uuid.UUID(hex=row['uuid']).hex
            elif 'user_id' not in row:
                row['user_id'] = uuid.UUID(hex=row['user']).hex
            elif isinstance(row['user_id'], uuid.UUID):
                row['user_id'] = row['user_id'].hex
            chunk.append([row[c] for c in columns])

            # write rows to database as transactions of multiple executemany statements
            if len(chunk) == chunk_size:
                rows_inserted += chunk_size
                logger.info(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: bulk inserting {chunk_size} rows ({rows_inserted})..."
                )
                cur.executemany(query, chunk)
                cur.execute('''COMMIT;''')
                start_row_id = cur.lastrowid - chunk_size + 1
                row_ids = range(start_row_id, cur.lastrowid + 1)
                inserted_row_ids.extend(row_ids)
                cur.execute('''BEGIN TRANSACTION;''')
                # reset chunk
                chunk = []
        # commit all remaining transactions
        if chunk:
            cur.executemany(query, chunk)
            cur.execute('''COMMIT;''')
            start_row_id = cur.lastrowid - len(chunk) + 1
            row_ids = range(start_row_id, cur.lastrowid + 1)
            inserted_row_ids.extend(row_ids)
        conn.commit()
        return inserted_row_ids

    def count_users(self):
        '''
        Returns a count of all survey responses in cache database.
        '''
        return UserSurveyResponse.select().count()

    def get_uuid(self, orig_id):
        '''
        Returns the database uuid for a user's original id from a non-Itinerum dataset.

        :param orig_id: The original dataset's user id for an individual user.
        '''
        user = UserSurveyResponse.get_or_none(orig_id=orig_id)
        if user:
            return user.uuid

    def load_user(self, uuid, start=None, end=None):
        '''
        Loads user by ``uuid`` to an itinerum-tripkit :py:class:`User` object.

        :param uuid:  A individual user's UUID from within an Itinerum survey.
        :param start: `Optional.` Naive datetime object (set within UTC) for
                      selecting a user's coordinates start period.
        :param end:   `Optional.` Naive datetime object (set within UTC) for
                      selecting a user's coordinates end period.
        '''
        db_user = UserSurveyResponse.get_or_none(uuid=uuid)
        if not db_user:
            raise UserNotFoundError(uuid)

        user = User(db_user)
        if start and end:
            user.coordinates = user.coordinates.where(
                Coordinate.timestamp_UTC >= start, Coordinate.timestamp_UTC <= end
            )
            user.prompt_responses = user.prompt_responses.where(
                PromptResponse.displayed_at_UTC >= start, PromptResponse.displayed_at_UTC <= end
            )
            user.cancelled_prompt_responses = user.cancelled_prompt_responses.where(
                CancelledPromptResponse.displayed_at_UTC >= start, CancelledPromptResponse.displayed_at_UTC <= end
            )
            user.detected_trip_coordinates = user.detected_trip_coordinates.where(
                DetectedTripCoordinate.timestamp_UTC >= start, DetectedTripCoordinate.timestamp_UTC <= end
            )
            user.detected_trip_day_summaries = user.detected_trip_day_summaries.where(
                DetectedTripDaySummary.date >= start.date, DetectedTripDaySummary.date <= end.date
            )
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

    def clear_trips(self, user=None):
        '''
        Clears the detected trip points table or for an individual user.

        :param user: (Optional) Delete trips for particular user only.
        '''
        if user:
            self.delete_user_from_table(DetectedTripCoordinate, user)
        else:
            DetectedTripCoordinate.delete().execute()

    def load_trips(self, user, start=None, end=None):
        '''
        Load the sorted trips for a given user as list.

        :param user: A database user response record with a populated
                     `detected_trip_coordinates` relation.
        '''
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
        '''
        Load the daily trip summaries for a given user as dict.

        :param user: A database user response record with a populated `detected_trip_day_summaries` relation.
        '''
        day_summaries = []
        for s in user.detected_trip_day_summaries:
            day_summaries.append(
                DaySummary(
                    timezone=s.timezone,
                    date=s.date,
                    has_trips=s.has_trips,
                    is_complete=s.is_complete,
                    start_point=s.start_point,
                    end_point=s.end_point,
                    consecutive_inactive_days=s.consecutive_inactive_days,
                    inactivity_streak=s.inactivity_streak,
                )
            )
        return day_summaries

    def load_subway_entrances(self):
        '''
        Queries cache database for all available subway entrances.
        '''
        return SubwayStationEntrance.select()

    def load_activity_locations(self, user):
        '''
        Queries cache database for activity locations known for a user.

        :param user: A database user response record
        '''
        locations = []
        for loc in user.user_locations:
            easting, northing, zone_num, zone_letter = utm.from_latlon(loc.latitude, loc.longitude)
            locations.append(
                ActivityLocation(
                    label=loc.label,
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    easting=easting,
                    northing=northing,
                    zone_num=zone_num,
                    zone_letter=zone_letter
                )
            )
        return locations


    def save_trips(self, user, trips, overwrite=True):
        '''
        Saves detected trips from processing algorithms to cache database. This
        table will be recreated on each save by default.

        :param user:  A database user response record associated with the trip records.
        :param trips: Iterable of detected trips from a trip processing algorithm.

        :type user: :py:class:`tripkit.models.User`
        :type trips: list of :py:class:`tripkit.models.Trip`
        '''

        def _trip_row_filter(trip_rows, model_fields):
            row = {}
            for trip in trip_rows:
                for point in trip.points:
                    row = {
                        'user_id': user.uuid,
                        'trip_num': trip.num,
                        'trip_code': trip.trip_code,
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'h_accuracy': point.h_accuracy,
                        'distance_before': point.distance_before,
                        'trip_distance': point.trip_distance,
                        'period_before': point.period_before,
                        'timestamp_UTC': point.timestamp_UTC,
                    }
                    yield row

        if overwrite:
            logger.info("overwriting user trips information...")
            self.delete_user_from_table(DetectedTripCoordinate, user)

        model_fields = set(DetectedTripCoordinate._meta.sorted_field_names)
        db_row_ids = self.bulk_insert(DetectedTripCoordinate, _trip_row_filter(trips, model_fields))

        # attach data to original user's object with database id
        idx = 0
        for trip in trips:
            for point in trip.points:
                point.database_id = db_row_ids[idx]
                idx += 1
        user.trips = trips

    def save_trip_day_summaries(self, user, trip_day_summaries, timezone, overwrite=True):
        '''
        Saves the daily summaries for detected trip days to cache database. This
        table with be recreated on each save by default.

        :param user:               A database user response record associated with the trip day
                                   summaries.
        :param trip_day_summaries: List of daily summaries from a daily trip counts algorithm.
        :param timezone:           The tz database timezone name for the location that was used to
                                   localize the complete days detection.
        :param overwrite:          Provide `False` to keep existing summaries for user in database.

        :type user: :py:class:`tripkit.models.User`
        :type trip_day_summaries: list of :py:class:`tripkit.models.DaySummary`
        :type timezone: str
        :type overwrite: boolean, optional
        '''

        def _row_filter(rows, model_fields):
            for row in rows:
                dict_row = row.__dict__
                dict_row['user_id'] = user.uuid
                dict_row['timezone'] = timezone
                dict_row['start_point_id'] = row.start_point.database_id if row.start_point else None
                dict_row['end_point_id'] = row.end_point.database_id if row.end_point else None
                yield dict_row

        if not trip_day_summaries:
            logger.info(f"no daily summaries for {user.uuid}. Has trip detection been run?")
            return

        if overwrite:
            logger.info("overwriting user daily summaries information...")
            self.delete_user_from_table(DetectedTripDaySummary, user)

        model_fields = set(DetectedTripDaySummary._meta.sorted_field_names)
        self.bulk_insert(DetectedTripDaySummary, _row_filter(trip_day_summaries, model_fields))


class BaseModel(Model):
    class Meta:
        database = deferred_db


class UserSurveyResponse(BaseModel):
    class Meta:
        table_name = 'survey_responses'

    uuid = UUIDField(unique=True, primary_key=True)
    orig_id = TextField(null=True)
    created_at_UTC = DateTimeField()
    modified_at_UTC = DateTimeField()
    itinerum_version = CharField()
    location_home_lat = FloatField(null=True)
    location_home_lon = FloatField(null=True)
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

    @property
    def user_locations(self):
        return self.user_locations_backref


class Coordinate(BaseModel):
    class Meta:
        table_name = 'coordinates'

    user = ForeignKeyField(UserSurveyResponse, backref='coordinates_backref')
    latitude = FloatField()
    longitude = FloatField()
    altitude = FloatField(null=True)
    speed = FloatField(null=True)
    direction = FloatField(null=True)
    h_accuracy = FloatField(null=True)
    v_accuracy = FloatField(null=True)
    acceleration_x = FloatField(null=True)
    acceleration_y = FloatField(null=True)
    acceleration_z = FloatField(null=True)
    point_type = TextField(null=True)
    mode_detected = TextField(null=True)
    timestamp_UTC = DateTimeField()
    timestamp_epoch = IntegerField()


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
    distance_before = FloatField()
    trip_distance = FloatField()
    period_before = IntegerField()
    timestamp_UTC = DateTimeField()


class DetectedTripDaySummary(BaseModel):
    class Meta:
        table_name = 'detected_trip_day_summaries'

    user = ForeignKeyField(UserSurveyResponse, backref='detected_trip_day_summaries_backref')
    timezone = TextField()
    date = DateField()
    has_trips = BooleanField()
    is_complete = BooleanField()
    start_point = ForeignKeyField(DetectedTripCoordinate, null=True)
    end_point = ForeignKeyField(DetectedTripCoordinate, null=True)
    consecutive_inactive_days = IntegerField(null=True)
    inactivity_streak = IntegerField(null=True)


class SubwayStationEntrance(BaseModel):
    class Meta:
        table_name = 'subway_station_entrances'
        indexes = ((('latitude', 'longitude'), True),)

    latitude = FloatField()
    longitude = FloatField()


class UserLocation(BaseModel):
    class Meta:
        table_name = 'user_locations'
        indexes = ((('user', 'label'), True),)

    user = ForeignKeyField(UserSurveyResponse, backref='user_locations_backref')
    label = TextField()
    latitude = FloatField()
    longitude = FloatField()
