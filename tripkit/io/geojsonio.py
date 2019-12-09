#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from copy import deepcopy
import inspect
import json
import os
import polyline

from . import formatters
from . import templates
from ..database import Coordinate, PromptResponse, CancelledPromptResponse
from .. import utils


class GeoJSONIO(object):
    def __init__(self, cfg):
        self.config = cfg

    def _write_features_to_f(self, filename, features):
        collection = deepcopy(templates.geojson_collection)
        collection['features'] = features
        geojson_fp = os.path.join(self.config.OUTPUT_DATA_DIR, filename)
        with open(geojson_fp, 'w') as geojson_f:
            geojson_f.write(json.dumps(collection, default=utils.misc.json_serialize))

    def write_inputs(self, fn_base, coordinates, prompts, cancelled_prompts):
        '''
        Writes input coordinates, prompts and cancelled prompts data selected from
        cache to individual geojson files.

        :param fn_base:           The base filename to prepend to each output geojson file.
        :param coordinates:       Iterable of database coordinates to write to geojson file.
        :param prompts:           Iterable of database prompts to write to geojson file.
        :param cancelled_prompts: Iterable of database cancelled prompts to write to geojson file.

        :type fn_base: str
        :type coordinates: list of :py:class:`tripkit.database.Coordinate`
        :type prompts: list of :py:class:`tripkit.database.PromptResponse`
        :type cancelled_prompts: list of :py:class:`tripkit.database.CancelledPromptResponse`
        '''
        ignore_keys = ('id', 'user', 'longitude', 'latitude')

        # coordinates point features
        coordinates_features = formatters._input_coordinates_features(coordinates, ignore_keys)
        coordinates_filename = f'{fn_base}_coordinates.geojson'
        self._write_features_to_f(coordinates_filename, coordinates_features)

        # prompts point features
        prompts_features = formatters._input_prompts_features(prompts, ignore_keys)
        prompts_filename = f'{fn_base}_prompts.geojson'
        self._write_features_to_f(prompts_filename, prompts_features)

        # cancelled prompts point features
        cancelled_prompts_features = formatters._input_cancelled_prompts_features(cancelled_prompts, ignore_keys)
        cancelled_prompts_filename = f'{fn_base}_cancelled_prompts.geojson'
        self._write_features_to_f(cancelled_prompts_filename, cancelled_prompts_features)

    def write_activity_locations(self, fn_base, locations):
        '''
        Write activity locations (from config or detected) to a geojson file.

        :param fn_base:   The base filename to prepend to each output geojson file.
        :param locations: A dictionary object of a user's survey responses containing columns with activity
                          location latitude and longitudes.

        :type fn_base: str
        :type locations: dict
        '''
        locations_fn = f'{fn_base}_locations.geojson'
        locations_features = formatters._activity_locations_features(locations)
        self._write_features_to_f(locations_fn, locations_features)

    def write_trips(self, fn_base, trips):
        '''
        Writes detected trips data selected from cache to geojson file.

        :param fn_base: The base filename to prepend to the output geojson file
        :param trips:   Iterable of database trips to write to geojson file

        :type fn_base: str
        :type trips: list of :py:class:`tripkit.models.Trip`
        '''
        detected_trips_features = []
        for trip in trips:
            properties = {
                'num': trip.num,
                'start_UTC': trip.start_UTC,
                'end_UTC': trip.end_UTC,
                'distance': trip.distance,
                'duration': trip.duration,
                'trip_code': trip.trip_code,
            }
            linestring = formatters._points_to_geojson_linestring(trip.geojson_coordinates, properties)
            detected_trips_features.append(linestring)
        filename = f'{fn_base}_trips.geojson'
        self._write_features_to_f(filename, detected_trips_features)

    def write_mapmatch(self, fn_base, results):
        '''
        Writes map matching results from API query to geojson file.

        :param fn_base: The base filename to prepend to the output geojson file
        :param results: JSON results from map matching API query

        :type fn_base: str
        :type result: dict
        '''
        mapmatched_features = []
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
            mapmatched_features.append(point)

        # create linestring features from the OSM input network returned as Google polyline
        for m in results['matchings']:
            properties = {}
            coordinates = [t[::-1] for t in polyline.decode(m['geometry'])]
            properties['confidence'] = m['confidence']
            linestring = formatters._points_to_geojson_linestring(coordinates, properties)
            mapmatched_features.append(linestring)

        filename = f'{fn_base}_matched.geojson'
        self._write_features_to_f(filename, mapmatched_features)
