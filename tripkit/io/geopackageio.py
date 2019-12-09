#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import fiona
import fiona.crs
import os

from . import formatters


class GeopackageIO(object):
    def __init__(self, cfg):
        self.config = cfg

    def _write_features_to_f(self, filename, schema, features):
        geopackage_fp = os.path.join(self.config.OUTPUT_DATA_DIR, filename)
        with fiona.open(
            geopackage_fp, 'w', driver='GPKG', schema=schema, crs=fiona.crs.from_epsg(4326)
        ) as gpkg_f:
            for feature in features:
                gpkg_f.write(feature)

    def write_inputs(self, fn_base, coordinates, prompts, cancelled_prompts):
        '''
        Writes input coordinates, prompts and cancelled prompts data selected from
        cache to individual geopackage files.

        :param fn_base:           The base filename to prepend to each output geopackage file.
        :param coordinates:       Iterable of database coordinates to write to geopackage file.
        :param prompts:           Iterable of database prompts to write to geopackage file.
        :param cancelled_prompts: Iterable of database cancelled prompts to write to geopackage file.

        :type fn_base: str
        :type coordinates: list of :py:class:`tripkit.database.Coordinate`
        :type prompts: list of :py:class:`tripkit.database.PromptResponse`
        :type cancelled_prompts: list of :py:class:`tripkit.database.CancelledPromptResponse`
        '''
        ignore_keys = ('id', 'user', 'longitude', 'latitude', 'prompt_uuid')

        # coordinates point features
        coordinates_filename = f'{fn_base}_coordinates.gpkg'
        coordinates_gpkg_schema = formatters._input_gpkg_schema(coordinates.model, ignore_keys)
        coordinates_features = formatters._input_coordinates_features(coordinates, ignore_keys)
        self._write_features_to_f(coordinates_filename, coordinates_gpkg_schema, coordinates_features)

        # prompts point features
        prompts_filename = f'{fn_base}_prompts.gpkg'
        prompts_gpkg_schema = formatters._input_gpkg_schema(prompts.model, ignore_keys)
        prompts_features = formatters._input_prompts_features(prompts, ignore_keys)
        self._write_features_to_f(prompts_filename, prompts_gpkg_schema, prompts_features)

        # cancelled prompts point features
        cancelled_prompts_filename = f'{fn_base}_cancelled_prompts.gpkg'
        cancelled_prompts_gpkg_schema = formatters._input_gpkg_schema(cancelled_prompts.model, ignore_keys)
        cancelled_prompts_features = formatters._input_cancelled_prompts_features(cancelled_prompts, ignore_keys)
        self._write_features_to_f(cancelled_prompts_filename, cancelled_prompts_gpkg_schema, cancelled_prompts_features)

    def write_activity_locations(self, fn_base, locations):
        '''
        Write activity locations (from config or detected) to a geopackage file.

        :param fn_base:   The base filename to prepend to each output geopackage file.
        :param locations: A dictionary object of a user's survey responses containing columns with activity
                          location latitude and longitudes.

        :type fn_base: str
        :type locations: dict
        '''
        locations_fn = f'{fn_base}_locations.gpkg'
        locations_schema = {
            'geometry': 'Point',
            'properties': [
                ('label', 'str')
            ]
        }
        locations_features = formatters._activity_locations_features(locations)
        self._write_features_to_f(locations_fn, locations_schema, locations_features)

    def write_trips(self, fn_base, trips):
        '''
        Writes detected trips data to a geopackage file.

        :param fn_base: The base filename to prepend to the output geopackage file
        :param trips:   Iterable of database trips to write to geopackage file

        :param fn_base: str
        :param trips: list of :py:class:`tripkit.models.Trip`
        '''
        geopackage_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{fn_base}_trips.gpkg')
        schema = {
            'geometry': 'LineString',
            'properties': [
                ('start_UTC', 'datetime'),
                ('end_UTC', 'datetime'),
                ('trip_code', 'int'),
                ('distance', 'float'),
            ],
        }
        with fiona.open(
            geopackage_fp, 'w', driver='GPKG', schema=schema, crs=fiona.crs.from_epsg(4326)
        ) as gpkg_f:
            for trip in trips:
                properties = {
                    'start_UTC': trip.start_UTC,
                    'end_UTC': trip.end_UTC,
                    'trip_code': trip.trip_code,
                    'distance': trip.distance,
                }
                feature = formatters._points_to_geojson_linestring(trip.geojson_coordinates, properties)
                gpkg_f.write(feature)
