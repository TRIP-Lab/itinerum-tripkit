#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from copy import deepcopy
from datetime import datetime
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


def _input_shp_schema(db_model, ignore_keys=None):
    if not ignore_keys:
        ignore_keys = []

    schema = {'geometry': 'Point', 'properties': []}
    for column in db_model._meta.sorted_fields:
        if column.name in ignore_keys:
            continue
        if not inspect.isclass(column.adapt):
            if column.field_type == 'INT':
                schema['properties'].append((column.name, 'int'))
            elif column.field_type == 'FLOAT':
                schema['properties'].append((column.name, 'float'))
            elif column.field_type == 'DATETIME':
                schema['properties'].append((column.name, 'str'))
            elif column.field_type == 'TEXT':
                schema['properties'].append((column.name, 'str'))
            else:
                raise Exception(
                    f'Could not determine Python type from database model'
                    f' for .shp schema: {column.name} ({column.field_type})'
                )
        else:
            schema['properties'].append((column.name, column.adapt.__name__))
    return schema


def __infer_keys_to_normalize(normalize_types, properties):
    normalize = {}
    for key, value in properties.items():
        for _type in normalize_types:
            if isinstance(value, _type):
                normalize.setdefault(_type, []).append(key)
    return normalize


def __normalize_values(normalize, properties):
    for _type, keys in normalize.items():
        for k in keys:
            if _type == datetime:
                properties[k] = properties[k].isoformat()


def _activity_locations_features(locations):
    features = []
    for location in locations:
        properties = {'label': location.label}
        point = _point_to_geojson_point((location.longitude, location.latitude), properties)
        features.append(point)
    return features


def _input_coordinates_features(coordinates, ignore_keys=None, normalize_types=None):
    if not ignore_keys:
        ignore_keys = []

    normalize = None
    features = []
    for c in coordinates:
        coordinates = (c.longitude, c.latitude)
        # much faster than peewee's playhouse.shortcuts.model_to_dict
        properties = {key: getattr(c, key) for key in Coordinate._meta.fields.keys() if key not in ignore_keys}
        
        # infer from the first row the keys->values that will need to be normalized
        # based upon normalize_types and apply to subsequent rows
        if normalize_types and not isinstance(normalize, dict):
            normalize = __infer_keys_to_normalize(normalize_types, properties)
        if normalize:
            __normalize_values(normalize, properties)

        point = _point_to_geojson_point(coordinates, properties)
        features.append(point)
    return features


def _input_prompts_features(prompts, ignore_keys=None, normalize_types=None):
    if not ignore_keys:
        ignore_keys = []

    normalize = None
    features = []
    for p in prompts:
        coordinates = (p.longitude, p.latitude)
        properties = {key: getattr(p, key) for key in PromptResponse._meta.fields.keys() if key not in ignore_keys}

        # infer from the first row the keys->values that will need to be normalized
        # based upon normalize_types and apply to subsequent rows
        if normalize_types and not isinstance(normalize, dict):
            normalize = __infer_keys_to_normalize(normalize_types, properties)
        if normalize:
            __normalize_values(normalize, properties)

        point = _point_to_geojson_point(coordinates, properties)
        features.append(point)
    return features


def _input_cancelled_prompts_features(cancelled_prompts, ignore_keys=None, normalize_types=None):
    if not ignore_keys:
        ignore_keys = []

    normalize = None
    features = []
    for cp in cancelled_prompts:
        coordinates = (cp.longitude, cp.latitude)
        properties = {
            key: getattr(cp, key) for key in CancelledPromptResponse._meta.fields.keys() if key not in ignore_keys
        }

        # infer from the first row the keys->values that will need to be normalized
        # based upon normalize_types and apply to subsequent rows
        if normalize_types and not isinstance(normalize, dict):
            normalize = __infer_keys_to_normalize(normalize_types, properties)
        if normalize:
            __normalize_values(normalize, properties)

        point = _point_to_geojson_point(coordinates, properties)
        features.append(point)
    return features
