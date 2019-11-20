#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from copy import deepcopy
import inspect

from . import templates
from ..database import Coordinate, PromptResponse, CancelledPromptResponse


def _point_to_geojson_point(coordinates, properties):
    geojson_point = deepcopy(templates.geojson_point)
    geojson_point['geometry']['coordinates'] = coordinates
    geojson_point['properties'] = dict(properties)
    return geojson_point


def _points_to_geojson_linestring(coordinates, properties):
    geojson_linestring = deepcopy(templates.geojson_linestring)
    geojson_linestring['properties'] = dict(properties)
    geojson_linestring['geometry']['coordinates'] = coordinates
    return geojson_linestring


def _input_gpkg_schema(db_model, ignore_keys=None):
    if not ignore_keys:
        ignore_keys = []

    schema = {'geometry': 'Point', 'properties': []}
    for column in db_model._meta.sorted_fields:
        if column.name in ignore_keys:
            continue
        if not inspect.isclass(column.adapt):
            if column.field_type == 'DATETIME':
                schema['properties'].append((column.name, 'datetime'))
            elif column.field_type == 'TEXT':
                schema['properties'].append((column.name, 'str'))
            else:
                raise Exception(
                    f'Could not determine Python type from database model'
                    f' for .gpkg schema: {column.name} ({column.field_type})'
                )
        else:
            schema['properties'].append((column.name, column.adapt.__name__))
    return schema


def _activity_locations_features(locations):
    features = []
    for location in locations:
        properties = {'label': location.label}
        point = _point_to_geojson_point((location.longitude, location.latitude), properties)
        features.append(point)
    return features


def _input_coordinates_features(coordinates, ignore_keys=None):
    if not ignore_keys:
        ignore_keys = []

    features = []
    for c in coordinates:
        coordinates = (c.longitude, c.latitude)
        # much faster than peewee's playhouse.shortcuts.model_to_dict
        properties = {key: getattr(c, key) for key in Coordinate._meta.fields.keys() if key not in ignore_keys}
        point = _point_to_geojson_point(coordinates, properties)
        features.append(point)
    return features


def _input_prompts_features(prompts, ignore_keys=None):
    if not ignore_keys:
        ignore_keys = []

    features = []
    for p in prompts:
        coordinates = (p.longitude, p.latitude)
        properties = {key: getattr(p, key) for key in PromptResponse._meta.fields.keys() if key not in ignore_keys}
        point = _point_to_geojson_point(coordinates, properties)
        features.append(point)
    return features


def _input_cancelled_prompts_features(cancelled_prompts, ignore_keys=None):
    if not ignore_keys:
        ignore_keys = []

    features = []
    for cp in cancelled_prompts:
        coordinates = (cp.longitude, cp.latitude)
        properties = {
            key: getattr(cp, key) for key in CancelledPromptResponse._meta.fields.keys() if key not in ignore_keys
        }
        point = _point_to_geojson_point(coordinates, properties)
        features.append(point)
    return features
