#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from copy import deepcopy
import csv
import datetime
import fiona
import fiona.crs
import inspect
import json
import os
import polyline

from . import utils
from .database import Coordinate, PromptResponse, CancelledPromptResponse


# geojson object templates--to be deepcopied
geojson_collection_template = {"type": "FeatureCollection", "features": []}
geojson_linestring_template = {
    "type": "Feature",
    "geometry": {"type": "LineString", "coordinates": []},
    "properties": {},
}
geojson_point_template = {"type": "Feature", "geometry": {"type": "Point", "coordinates": []}, "properties": {}}
geojson_multipoint_template = {
    "type": "Feature",
    "geometry": {"type": "MultiPoint", "coordinates": []},
    "properties": {},
}


# geojson feature generators
def _point_to_geojson_point(coordinates, properties):
    geojson_point = deepcopy(geojson_point_template)
    geojson_point["geometry"]["coordinates"] = coordinates
    geojson_point["properties"] = dict(properties)
    return geojson_point


def _points_to_geojson_linestring(coordinates, properties):
    geojson_linestring = deepcopy(geojson_linestring_template)
    geojson_linestring["properties"] = dict(properties)
    geojson_linestring["geometry"]["coordinates"] = coordinates
    return geojson_linestring


# input data formatters
def _input_gpkg_schema(db_model, ignore_keys=None):
    if not ignore_keys:
        ignore_keys = []

    schema = {"geometry": "Point", "properties": []}
    for column in db_model._meta.sorted_fields:
        if column.name in ignore_keys:
            continue
        if not inspect.isclass(column.adapt):
            if column.field_type == "DATETIME":
                schema["properties"].append((column.name, "datetime"))
            elif column.field_type == "TEXT":
                schema["properties"].append((column.name, "str"))
            else:
                raise Exception(
                    f"Could not determine Python type from database model"
                    f" for .gpkg schema: {column.name} ({column.field_type})"
                )
        else:
            schema["properties"].append((column.name, column.adapt.__name__))
    return schema


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
    ignore_keys = ("id", "user", "longitude", "latitude")

    # coordinates point features
    coordinates_features = _input_coordinates_features(coordinates, ignore_keys)
    coordinates_filename = fn_base + "_coordinates.geojson"
    write_features_to_geojson_f(cfg, coordinates_filename, coordinates_features)

    # prompts point features
    prompts_features = _input_prompts_features(prompts, ignore_keys)
    prompts_filename = fn_base + "_prompts.geojson"
    write_features_to_geojson_f(cfg, prompts_filename, prompts_features)

    # cancelled prompts point features
    cancelled_prompts_features = _input_cancelled_prompts_features(cancelled_prompts, ignore_keys)
    cancelled_prompts_filename = fn_base + "_cancelled_prompts.geojson"
    write_features_to_geojson_f(cfg, cancelled_prompts_filename, cancelled_prompts_features)


def write_trips_geojson(cfg, fn_base, trips):
    """
    Writes detected trips data selected from cache to geojson file.

    :param cfg:     Global configuration object
    :param fn_base: The base filename to prepend to the output geojson file
    :param trips:   Iterable of database trips to write to geojson file
    """
    detected_trips_features = []
    for trip in trips:
        properties = {"start_UTC": trip.start_UTC, "end_UTC": trip.end_UTC, "trip_code": trip.trip_code}
        linestring = _points_to_geojson_linestring(trip.geojson_coordinates, properties)
        detected_trips_features.append(linestring)
    filename = fn_base + "_trips.geojson"
    write_features_to_geojson_f(cfg, filename, detected_trips_features)


def write_mapmatched_geojson(cfg, fn_base, results):
    """
    Writes map matching results from API query to geojson file.

    :param cfg:     Global configuration object
    :param fn_base: The base filename to prepend to the output geojson file
    :param results: JSON results from map matching API query
    """
    mapmatched_features = []
    # create points features with a confidence for each match (distance in meters)
    for p in results["tracepoints"]:
        if not p:
            continue

        properties = {}
        point = _point_to_geojson_point(p["location"], properties)
        point["properties"]["name"] = p["name"]

        # associate matching confidence to point attribute
        matchings_idx = p["matchings_index"]
        waypoint_idx = p["waypoint_index"] - 1
        if p["waypoint_index"] == 0:
            point["properties"]["weight"] = 0  # first point does not have a weight
        else:
            point["properties"]["weight"] = results["matchings"][matchings_idx]["legs"][waypoint_idx]["weight"]
        mapmatched_features.append(point)

    # create linestring features from the OSM input network returned as Google polyline
    for m in results["matchings"]:
        properties = {}
        coordinates = [t[::-1] for t in polyline.decode(m["geometry"])]
        properties["confidence"] = m["confidence"]
        linestring = _points_to_geojson_linestring(coordinates, properties)
        mapmatched_features.append(linestring)

    filename = fn_base + "_matched.geojson"
    write_features_to_geojson_f(cfg, filename, mapmatched_features)


def write_features_to_geojson_f(cfg, filename, features):
    collection = deepcopy(geojson_collection_template)
    collection["features"] = features
    geojson_fp = os.path.join(cfg.OUTPUT_DATA_DIR, filename)
    with open(geojson_fp, "w") as geojson_f:
        geojson_f.write(json.dumps(collection, default=utils.json_serialize))


# geopackage file I/O
def write_input_geopackage(cfg, fn_base, coordinates, prompts, cancelled_prompts):
    """
    Writes input coordinates, prompts and cancelled prompts data selected from
    cache to individual geopackage files.

    :param cfg:               Global configuration object (eventually this should be
                              supplied upon initialization like :py:class:`CSVParser`)
    :param fn_base:           The base filename to prepend to each output geopackage file.
    :param coordinates:       Iterable of database coordinates to write to geopackage
                              file. Usually the result of a database query.
    :param prompts:           Iterable of database prompts to write to geopackage
                              file. Usually the result of a database query.
    :param cancelled_prompts: Iterable of database cancelled prompts to write to
                              geopackage file. Usually the result of a database query.
    """
    ignore_keys = ("id", "user", "longitude", "latitude", "prompt_uuid")

    # coordinates point features
    coordinates_filename = fn_base + "_coordinates.gpkg"
    coordinates_gpkg_schema = _input_gpkg_schema(coordinates.model, ignore_keys)
    coordinates_features = _input_coordinates_features(coordinates, ignore_keys)
    write_features_to_geopackage_f(cfg, coordinates_filename, coordinates_gpkg_schema, coordinates_features)

    # prompts point features
    prompts_filename = fn_base + "_prompts.gpkg"
    prompts_gpkg_schema = _input_gpkg_schema(prompts.model, ignore_keys)
    prompts_features = _input_prompts_features(prompts, ignore_keys)
    write_features_to_geopackage_f(cfg, prompts_filename, prompts_gpkg_schema, prompts_features)

    # cancelled prompts point features
    cancelled_prompts_filename = fn_base + "_cancelled_prompts.gpkg"
    cancelled_prompts_gpkg_schema = _input_gpkg_schema(cancelled_prompts.model, ignore_keys)
    cancelled_prompts_features = _input_cancelled_prompts_features(cancelled_prompts, ignore_keys)
    write_features_to_geopackage_f(
        cfg, cancelled_prompts_filename, cancelled_prompts_gpkg_schema, cancelled_prompts_features
    )


def write_trips_geopackage(cfg, fn_base, trips):
    """
    Writes detected trips data selected from cache to geopackage file.

    :param cfg:     Global configuration object
    :param fn_base: The base filename to prepend to the output geopackage file
    :param trips:   Iterable of database trips to write to geopackage file
    """
    geopackage_fp = os.path.join(cfg.OUTPUT_DATA_DIR, fn_base + "_trips.gpkg")
    schema = {
        "geometry": "LineString",
        "properties": [("start_UTC", "datetime"), ("end_UTC", "datetime"), ("trip_code", "int"), ("distance", "float")],
    }
    with fiona.open(geopackage_fp, "w", driver="GPKG", schema=schema, crs=fiona.crs.from_epsg(4326)) as geopackage_f:
        for trip in trips:
            properties = {
                "start_UTC": trip.start_UTC,
                "end_UTC": trip.end_UTC,
                "trip_code": trip.trip_code,
                "distance": trip.distance,
            }
            feature = _points_to_geojson_linestring(trip.geojson_coordinates, properties)
            geopackage_f.write(feature)


def write_features_to_geopackage_f(cfg, filename, schema, features):
    geopackage_fp = os.path.join(cfg.OUTPUT_DATA_DIR, filename)
    with fiona.open(geopackage_fp, "w", driver="GPKG", schema=schema, crs=fiona.crs.from_epsg(4326)) as geopackage_f:
        for feature in features:
            geopackage_f.write(feature)


# csv file I/0
def write_trip_summaries_csv(cfg, filename, summaries, extra_fields=None):
    export_csv = os.path.join(cfg.OUTPUT_DATA_DIR, filename)
    with open(export_csv, "w") as csv_f:
        headers = [
            "uuid",
            "trip_id",
            "start",
            "end",
            "trip_code",
            "olat",
            "olon",
            "dlat",
            "dlon",
            "merge_codes",
            "direct_distance",
            "cumulative_distance",
        ]
        if extra_fields:
            headers.extend(extra_fields)
        writer = csv.DictWriter(csv_f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(summaries)


def write_complete_days_csv(cfg, filename, trip_day_summaries):
    csv_fp = os.path.join(cfg.OUTPUT_DATA_DIR, filename)

    csv_rows = []
    for uuid, daily_summaries in sorted(trip_day_summaries.items()):
        for date, summary in sorted(daily_summaries.items()):
            summary["uuid"] = uuid
            summary["date_UTC"] = date
            summary["has_trips"] = int(summary["has_trips"])
            summary["is_complete"] = int(summary["is_complete"])
            csv_rows.append(summary)

    headers = [
        "uuid",
        "date_UTC",
        "has_trips",
        "is_complete",
        "consecutive_inactive_days",
        "inactivity_streak",
        "inactivity_distance",
        "start_latitude",
        "start_longitude",
        "end_latitude",
        "end_longitude",
    ]
    with open(csv_fp, "w") as csv_f:
        writer = csv.DictWriter(csv_f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(csv_rows)
