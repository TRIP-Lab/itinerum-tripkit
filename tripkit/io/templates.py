#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


# geojson object templates--to be deepcopied
geojson_collection = {'type': 'FeatureCollection', 'features': []}
geojson_linestring = {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': []}, 'properties': {}}
geojson_point = {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': []}, 'properties': {}}
geojson_multipoint = {'type': 'Feature', 'geometry': {'type': 'MultiPoint', 'coordinates': []}, 'properties': {}}
