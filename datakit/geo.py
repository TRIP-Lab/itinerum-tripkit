#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from copy import deepcopy
import json
import os
import polyline

from . import config
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
def write_input_geojson(fn_base, coordinates, prompts, cancelled_prompts):
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
    write_features_to_geojson_f(coordinates_filename, input_coordinates_features)

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
    write_features_to_geojson_f(prompts_filename, input_prompts_features)

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
    write_features_to_geojson_f(cancelled_prompts_filename, input_cancelled_prompts_features)


def write_trips_geojson(fn_base, trips):
    detected_trips_features = []
    for trip_num, trip in trips.items():
        properties = {
            'start_UTC': trip.start_UTC,
            'end_UTC': trip.end_UTC,
            'trip_code': trip.trip_code
        }
        linestring = points_to_geojson_linestring(trip.geojson_coordinates, properties)
        detected_trips_features.append(linestring)
    filename = fn_base + '_trips.geojson'
    write_features_to_geojson_f(filename, detected_trips_features)


def write_mapmatched_geojson(fn_base, mapmatching_results):
    print('matchings:', len(mapmatching_results['matchings']))
    mapmatched_features = []
    # create points features with a confidence for each match (distance in meters)
    for p in mapmatching_results['tracepoints']:
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
            point['properties']['weight'] = mapmatching_results['matchings'][matchings_idx]['legs'][waypoint_idx]['weight']
        mapmatched_features.append(point)    

    # create linestring features from the OSM input network returned as Google polyline
    for m in mapmatching_results['matchings']:
        properties = {}
        properties.update(defaults)
        coordinates = [t[::-1] for t in polyline.decode(m['geometry'])]
        properties['confidence'] = m['confidence']
        linestring = points_to_geojson_linestring(coordinates, properties)
        mapmatched_features.append(linestring)

    filename = fn_base + '_matched.geojson'
    write_features_to_geojson_f(filename, mapmatched_features)


def write_features_to_geojson_f(filename, features):
    collection = deepcopy(geojson_collection_template)
    collection['features'] = features
    geojson_fp = os.path.join(config.OUTPUT_DATA_DIR, filename)
    with open(geojson_fp, 'w') as geojson_f:
        geojson_f.write(json.dumps(collection, default=utils.json_serialize))

