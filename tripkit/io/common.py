#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from .csvio import CSVIO
from .geojsonio import GeoJSONIO
from .geopackageio import GeopackageIO


class IO(object):
    '''
    The entrypoint class for the various I/O readers and writers.
    '''

    def __init__(self, cfg):
        self.csv = CSVIO(cfg)
        self.geojson = GeoJSONIO(cfg)
        self.geopackage = GeopackageIO(cfg)
