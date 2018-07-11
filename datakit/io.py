#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from copy import deepcopy
import csv
import fiona
import fiona.crs
import json
import os
import polyline

from . import utils
from .database import Coordinate, PromptResponse, CancelledPromptResponse


# geojson object templates--to be deepcopied
geojson_collection_template = {
    'type': 'FeatureCollection',
    'features': []
}
geojson_linestring_template = {
    'type': 'Feature',
    'geometry': {
        'type': 'LineString',
        'coordinates': []
    },
    'properties': {}
}
geojson_point_template = {
    'type': 'Feature',
    'geometry': {
        'type': 'Point',
        'coordinates': []
    },
    'properties': {}
}
geojson_multipoint_template = {
    'type': 'Feature',
    'geometry': {
        'type': 'MultiPoint',
        'coordinates': []
    },
    'properties': {}
}
    

# geojson feature generators
def point_to_geojson_point(coordinates, properties):
    geojson_point = deepcopy(geojson_point_template)
    geojson_point['geometry']['coordinates'] = coordinates
    geojson_point['properties'] = dict(properties)
    return geojson_point


def points_to_geojson_linestring(coordinates, properties):
    geojson_linestring = deepcopy(geojson_linestring_template)
    geojson_linestring['properties'] = dict(properties)
    geojson_linestring['geometry']['coordinates'] = coordinates
    return geojson_linestring


# geojson file I/O
def write_input_geojson(cfg, fn_base, coordinates, prompts, cancelled_prompts):
    """
    Writes input coordinates, prompts and cancelled prompts data selected from 
    cache to individual geojson files.

    :param cfg:               Global configuration object (eventually this should be
                              supplied upon initialization like :py:class:`CSVParser`)
    :param fn_base:           The base filename to prepend to each output geojson file.
    :param coordinates:       Iterable of database coordinates to write to geojson
                              file. Usually the result of a database query.
    :param prompts:           Iterable of database prompts to write to geojson
                              file. Usually the result of a database query.
    :param cancelled_prompts: Iterable of database cancelled prompts to write to
                              geojson file. Usually the result of a database query.
    """
    ignore_keys = ('id', 'user', 'longitude', 'latitude')

    # coordinates point features
    input_coordinates_features = []
    for c in coordinates:
        coordinates = (c.longitude, c.latitude)
        # much faster than peewee's playhouse.shortcuts.model_to_dict
        properties = {
            key: getattr(c, key)
            for key in Coordinate._meta.fields.keys()  
            if key not in ignore_keys
        }
        point = point_to_geojson_point(coordinates, properties)
        input_coordinates_features.append(point)
    coordinates_filename = fn_base + '_coordinates.geojson'
    write_features_to_geojson_f(cfg, coordinates_filename, input_coordinates_features)

    # prompts point features
    input_prompts_features = []
    for p in prompts:
        coordinates = (p.longitude, p.latitude)
        properties = {
            key: getattr(p, key)
            for key in PromptResponse._meta.fields.keys()  
            if key not in ignore_keys
        }
        point = point_to_geojson_point(coordinates, properties)
        input_prompts_features.append(point)
    prompts_filename = fn_base + '_prompts.geojson'
    write_features_to_geojson_f(cfg, prompts_filename, input_prompts_features)

    # cancelled prompts point features
    input_cancelled_prompts_features = []
    for cp in cancelled_prompts:
        coordinates = (cp.longitude, cp.latitude)
        properties = {
            key: getattr(cp, key)
            for key in CancelledPromptResponse._meta.fields.keys()  
            if key not in ignore_keys
        }
        point = point_to_geojson_point(coordinates, properties)
        input_cancelled_prompts_features.append(point)
    cancelled_prompts_filename = fn_base + '_cancelled_prompts.geojson'
    write_features_to_geojson_f(cfg, cancelled_prompts_filename, input_cancelled_prompts_features)


def write_trips_geojson(cfg, fn_base, trips):
    """
    Writes detected trips data selected from cache to geojson file.

    :param cfg:     Global configuration object
    :param fn_base: The base filename to prepend to the output geojson file
    :param trips:   Iterable of database trips to write to geojson file
    """
    detected_trips_features = []
    for trip in trips:
        properties = {
            'start_UTC': trip.start_UTC,
            'end_UTC': trip.end_UTC,
            'trip_code': trip.trip_code
        }
        linestring = points_to_geojson_linestring(trip.geojson_coordinates, properties)
        detected_trips_features.append(linestring)
    filename = fn_base + '_trips.geojson'
    write_features_to_geojson_f(cfg, filename, detected_trips_features)


def write_trips_geopackage(cfg, fn_base, trips):
    """
    Writes detected trips data selected from cache to geopackage file.

    :param cfg:     Global configuration object
    :param fn_base: The base filename to prepend to the output geopackage file
    :param trips:   Iterable of database trips to write to geopackage file
    """
    geopackage_fp = os.path.join(cfg.OUTPUT_DATA_DIR, fn_base + '_trips.gpkg')
    schema = {
        'geometry': 'LineString',
        'properties': [('start_UTC', 'datetime'),
                       ('end_UTC', 'datetime'),
                       ('trip_code', 'int')]
    }
    with fiona.open(geopackage_fp, 'w',
                    driver='GPKG',
                    schema=schema,
                    crs=fiona.crs.from_epsg(4326)) as geopackage_f:
        for trip in trips:
            properties = {
                'start_UTC': trip.start_UTC,
                'end_UTC': trip.end_UTC,
                'trip_code': trip.trip_code
            }
            feature = points_to_geojson_linestring(trip.geojson_coordinates, properties)
            geopackage_f.write(feature)




def write_mapmatched_geojson(cfg, fn_base, results):
    """
    Writes map matching results from API query to geojson file.

    :param cfg:     Global configuration object
    :param fn_base: The base filename to prepend to the output geojson file
    :param results: JSON results from map matching API query
    """
    print('matchings:', len(results['matchings']))
    mapmatched_features = []
    # create points features with a confidence for each match (distance in meters)
    for p in results['tracepoints']:
        if not p:
            continue
        
        properties = {}
        point = point_to_geojson_point(p['location'], properties)
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
        linestring = points_to_geojson_linestring(coordinates, properties)
        mapmatched_features.append(linestring)

    filename = fn_base + '_matched.geojson'
    write_features_to_geojson_f(cfg, filename, mapmatched_features)


def write_features_to_geojson_f(cfg, filename, features):
    collection = deepcopy(geojson_collection_template)
    collection['features'] = features
    geojson_fp = os.path.join(cfg.OUTPUT_DATA_DIR, filename)
    with open(geojson_fp, 'w') as geojson_f:
        geojson_f.write(json.dumps(collection, default=utils.json_serialize))


def write_complete_days_csv(cfg, filename, trip_day_summaries):
    csv_fp = os.path.join(cfg.OUTPUT_DATA_DIR, filename)

    csv_rows = []
    for uuid, daily_summaries in sorted(trip_day_summaries.items()):
        for date, summary in sorted(daily_summaries.items()):
            summary['uuid'] = uuid
            summary['date_UTC'] = date
            summary['has_trips'] = int(summary['has_trips'])
            summary['is_complete'] = int(summary['is_complete'])
            csv_rows.append(summary)

    headers = ['uuid', 'date_UTC', 'has_trips', 'is_complete', 'consecutive_inactive_days',
               'inactivity_streak', 'inactivity_distance', 'start_latitude', 'start_longitude',
               'end_latitude', 'end_longitude']
    with open(csv_fp, 'w') as csv_f:
        writer = csv.DictWriter(csv_f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(csv_rows)


