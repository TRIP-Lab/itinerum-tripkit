#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
#
# This contains functions common to multiple csv parsers to be attached
# as class methods on the parent parsers
import csv
from datetime import datetime
import logging
import os

from ..database import SubwayStationEntrance, UserLocation, UserSurveyResponse

logger = logging.getLogger('itinerum-tripkit.csvparser.common')


def _load_subway_stations(subway_stations_csv_fp):
    '''
    Loads a subway station entrances .csv the database for use by trip
    detection algorithms. Each .csv row should represent a station entrance
    with the column names of 'x' (or 'longitude') and 'y' (or 'latitude').

    :param subway_stations_csv_fp: The full filepath of subway station entrances
                                    `.csv` for the survey study region.

    :param type subway_stations_csv_fp: str                                    
    '''
    # change selected column keys to latitude and longitude
    def _rename_columns(location_columns, rows):
        lat_label, lng_label = location_columns
        for row in rows:
            row['latitude'] = row.pop(lat_label)
            row['longitude'] = row.pop(lng_label)
            yield row

    logger.info("Loading subway stations .csv to db...")
    with open(subway_stations_csv_fp, 'r') as csv_f:
        # detect whether commas or semicolon is used a separator (english/french)
        dialect = csv.Sniffer().sniff(csv_f.read(), delimiters=';,')
        csv_f.seek(0)

        reader = csv.DictReader(csv_f, dialect=dialect)
        reader.fieldnames = [name.lower() for name in reader.fieldnames]

        # determine the exsting keys out of the options for the lat/lng columns
        location_columns = None
        location_columns_options = [('latitude', 'longitude'), ('lat', 'lng'), ('lat', 'lon'), ('y', 'x')]

        for columns in location_columns_options:
            if set(columns).issubset(set(reader.fieldnames)):
                location_columns = columns

        # rename columns if latitude/longitude are not already found
        rename = ('latitude' and 'longitude') not in location_columns
        if rename:
            reader = _rename_columns(location_columns, reader)

        for row in reader:
            SubwayStationEntrance.create(latitude=float(row['latitude']), longitude=float(row['longitude']))


def _load_user_locations(locations_csv_fp, uuid_lookup=None):
    '''
    Loads user location labels and centroids from file.

    :param locations_csv_fp: The full filepath of an user locations csv.

    :param type locations_csv_fp: str
    '''
    logger.info("Loading user locations .csv to db...")
    with open(locations_csv_fp, 'r') as csv_f:
        # detect whether commas or semicolon is used a separator (english/french)
        dialect = csv.Sniffer().sniff(csv_f.read(), delimiters=';,')
        csv_f.seek(0)

        reader = csv.DictReader(csv_f, dialect=dialect)
        reader.fieldnames = [name.lower() for name in reader.fieldnames]
        for row in reader:
            user_id = row.get('user').strip()
            if not user_id:
                continue
            if uuid_lookup:
                user_id = uuid_lookup[user_id]
            label = row.get('label')
            lat = float(row['latitude'])
            lon = float(row['longitude'])
            UserLocation.create(user=user_id, label=label, latitude=lat, longitude=lon)


def _generate_null_survey(input_dir, coordinates_csv_fn, id_column='uuid', uuid_lookup=None, headers=None):
    '''
    Generates an empty survey responses table for surveys with only coordinate data. Used for populating foreign keys
    for queries on the child data tables.
    '''
    logger.info("Reading coordinates .csv and populating survey responses with null data in db...")
    coordinates_fp = os.path.join(input_dir, coordinates_csv_fn)
    orig_ids = None
    if uuid_lookup:
        orig_ids = list(uuid_lookup.keys())
    else:
        with open(coordinates_fp, 'r', encoding='utf-8-sig') as csv_f:
            # much faster than csv.DictReader
            reader = csv.reader(csv_f)
            if not headers:
                headers = [h.lower() for h in next(reader)]
            orig_id_idx = headers.index(id_column)
            orig_ids = {r[orig_id_idx] for r in reader}

    for uuid in orig_ids:
        orig_id = None
        if uuid_lookup:
            orig_id = uuid
            uuid = uuid_lookup[orig_id]

        UserSurveyResponse.create(
            uuid=uuid,
            orig_id=orig_id,
            created_at_UTC=datetime(2000, 1, 1),
            modified_at_UTC=datetime(2000, 1, 1),
            itinerum_version=-1,
            member_type=-1,
            model=-1,
            os=-1,
            os_version=-1,
        )
