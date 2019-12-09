#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from datetime import datetime
import fiona
import fiona.crs
import os
import polyline

from . import formatters


class ShapefileIO(object):
    def __init__(self, cfg):
        self.config = cfg

    def _write_features_to_f(self, filename, schema, features):
        shapefile_fp = os.path.join(self.config.OUTPUT_DATA_DIR, filename)
        with fiona.open(
            shapefile_fp, 'w', driver='ESRI Shapefile', schema=schema, crs=fiona.crs.from_epsg(4326)
        ) as shp_f:
            normalize = None
            for feature in features:
                shp_f.write(feature)

    def write_inputs(self, fn_base, coordinates, prompts, cancelled_prompts):
        '''
        Writes input coordinates, prompts and cancelled prompts data selected from
        cache to individual shapefile files.

        :param fn_base:           The base filename to prepend to each output file.
        :param coordinates:       Iterable of database coordinates to write to shapefile files.
        :param prompts:           Iterable of database prompts to write to shapefile files.
        :param cancelled_prompts: Iterable of database cancelled prompts to write to shapefile files.

        :type fn_base: str
        :type coordinates: list of :py:class:`tripkit.database.Coordinate`
        :type prompts: list of :py:class:`tripkit.database.PromptResponse`
        :type cancelled_prompts: list of :py:class:`tripkit.database.CancelledPromptResponse`
        '''
        ignore_keys = ('id', 'user', 'longitude', 'latitude', 'prompt_uuid')
        normalize_keys = (datetime,)

        # coordinates point features
        coordinates_filename = f'{fn_base}_coordinates.shp'
        coordinates_shp_schema = formatters._input_shp_schema(coordinates.model, ignore_keys)
        coordinates_features = formatters._input_coordinates_features(coordinates, ignore_keys, normalize_keys)
        self._write_features_to_f(coordinates_filename, coordinates_shp_schema, coordinates_features)

        # prompts point features
        prompts_filename = f'{fn_base}_prompts.shp'
        prompts_shp_schema = formatters._input_shp_schema(prompts.model, ignore_keys)
        prompts_features = formatters._input_prompts_features(prompts, ignore_keys, normalize_keys)
        self._write_features_to_f(prompts_filename, prompts_shp_schema, prompts_features)

        # cancelled prompts point features
        cancelled_prompts_filename = f'{fn_base}_cancelled_prompts.shp'
        cancelled_prompts_shp_schema = formatters._input_shp_schema(cancelled_prompts.model, ignore_keys)
        cancelled_prompts_features = formatters._input_cancelled_prompts_features(cancelled_prompts, ignore_keys, normalize_keys)
        self._write_features_to_f(cancelled_prompts_filename, cancelled_prompts_shp_schema, cancelled_prompts_features)

    def write_activity_locations(self, fn_base, locations):
        '''
        Write activity locations (from config or detected) to shapefile files.

        :param fn_base:   The base filename to prepend to each output file.
        :param locations: A dictionary object of a user's survey responses containing columns with activity
                          location latitude and longitudes.

        :type fn_base: str
        :type locations: dict
        '''
        locations_fn = f'{fn_base}_locations.shp'
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
        Writes detected trips data to shapefile files.

        :param fn_base: The base filename to prepend to the output file
        :param trips:   Iterable of database trips to write to file

        :param fn_base: str
        :param trips: list of :py:class:`tripkit.models.Trip`
        '''
        shapefile_fp = os.path.join(self.config.OUTPUT_DATA_DIR, f'{fn_base}_trips.shp')
        schema = {
            'geometry': 'LineString',
            'properties': [
                ('start_UTC', 'str'),
                ('end_UTC', 'str'),
                ('trip_code', 'int'),
                ('distance', 'float'),
            ],
        }
        with fiona.open(
            shapefile_fp, 'w', driver='ESRI Shapefile', schema=schema, crs=fiona.crs.from_epsg(4326)
        ) as shp_f:
            for trip in trips:
                properties = {
                    'start_UTC': trip.start_UTC.isoformat(),
                    'end_UTC': trip.end_UTC.isoformat(),
                    'trip_code': trip.trip_code,
                    'distance': trip.distance,
                }
                feature = formatters._points_to_geojson_linestring(trip.geojson_coordinates, properties)
                shp_f.write(feature)

    def write_mapmatch(self, fn_base, results):
        '''
        Writes map matching results from API query to shapefile files.

        :param fn_base: The base filename to prepend to the output file
        :param results: JSON results from map matching API query

        :type fn_base: str
        :type result: dict
        '''
        points_features = []
        # create points features with a confidence for each match (distance in meters)
        for p in results['tracepoints']:
            if not p:
                continue

            properties = {}
            point = formatters._point_to_geojson_point(p['location'], properties)
            point['properties']['name'] = p['name']

            # associate matching confidence to point attribute
            matchings_idx = p['matchings_index']
            waypoint_idx = p['waypoint_index'] - 1
            if p['waypoint_index'] == 0:
                point['properties']['weight'] = 0  # first point does not have a weight
            else:
                point['properties']['weight'] = results['matchings'][matchings_idx]['legs'][waypoint_idx]['weight']
            points_features.append(point)

        points_filename = f'{fn_base}_matched_points.shp'
        points_schema = {
            'geometry': 'Point',
            'properties': [
                ('name', 'str'),
                ('weight', 'float'),
            ],
        }
        self._write_features_to_f(points_filename, points_schema, points_features)

        # create linestring features from the OSM input network returned as Google polyline
        trips_features = []
        for m in results['matchings']:
            properties = {}
            coordinates = [t[::-1] for t in polyline.decode(m['geometry'])]
            properties['confidence'] = m['confidence']
            linestring = formatters._points_to_geojson_linestring(coordinates, properties)
            trips_features.append(linestring)
        
        trips_filename = f'{fn_base}_matched_trips.shp'
        trips_schema = {
            'geometry': 'LineString',
            'properties': [
                ('confidence', 'float')
            ]
        }
        self._write_features_to_f(trips_filename, trips_schema, trips_features)
