#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from .csvio import CSVIO
from .geojsonio import GeoJSONIO
from .geopackageio import GeopackageIO
from .shapefileio import ShapefileIO


class IO(object):
    def __init__(self, cfg):
        self.csv = CSVIO(cfg)
        self.geojson = GeoJSONIO(cfg)
        self.geopackage = GeopackageIO(cfg)
        self.shapefile = ShapefileIO(cfg)
