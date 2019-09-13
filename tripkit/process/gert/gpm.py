#!/usr/bin/env python

# Based upon GERT 1.2 (2016-06-03): GIS-based Episode Reconstruction Toolkit
# Stage 1 - GPS Preprocessing Module (gert_1.2/scripts/gpsfilter.py)
# Ported to itinerum-tripkit by Kyle Fitzsimmons, 2019
'''
GERT Stage 1: GPS Preprocessing

This module removes invalid points from raw GPS data in csv format using data
cleaning procedures. Generally, invalid points include redundant points (points
with the same coordinates), and outliers (with speed greater than or equal to
50 m/s). GPM uses several algorithms to filter valid trajectories and these
algorithms were written in several sub-modules focusing on certain aspects of
GPS pre-processing.

Cited References:
Bialostozky, E. (2009). Development of a Mode Detection Algorithm for GPS-Based Personal
    Travel Surveys in New York City. New York: New York Metropolitan Transportation Council.
Schuessler, N., & Axhausen, K. (2009). Processing Raw Data from Global Positioning
    Systems Without Additional Information. [10.3141/2105-04]. Transportation Research
    Record: Journal of the Transportation Research Board, 2105, 28-36.
Wolf, J. (2000). Using GPS Data Loggers to Replace Travel Diaries in the Collection of
    Travel Data. Ph.D. Thesis, Georgia Institute of Technology, Atlanta.
'''
import logging

from .models import GertCoordinate
from .utils import geo


logger = logging.getLogger(__name__)


def run(coordinates):
    coordinates = list(coordinates)
    logger.debug(f"Uncleaned input coordinates: {coordinates}")

    processed = []
    last_gc = None
    for c in coordinates:
        gc = GertCoordinate(c)

        # calculate coordinate attributes compared to previous coordinate
        if not last_gc:
            processed.append(gc)
            last_gc = gc
            continue
        gc.duration_s = geo.calculate_duration(last_gc, gc)
        gc.distance_m = geo.calculate_distance(last_gc, gc)
        gc.bearing = geo.calculate_bearing(last_gc, gc)
        gc.delta_heading = geo.calculate_delta_heading(last_gc, gc)

        # skip points with speed of 0
        if not gc.speed_ms:
            continue
        # filter points that are not within valid points threshold:
        # - 50 meters per second (180 km/h; Schuessler and Axhausen, 2009)
        # - 120 seconds (Wolf, 2000)
        # - 250 meters (considered as "underground travel"; Bialostozky, 2009)
        if gc.speed_ms <= 50 and (gc.distance_m <= 250 or gc.duration_s <= 120):
            processed.append(gc)

        last_gc = gc
    logger.debug(f"Cleaned input coordinates: {len(processed)}")
    return processed
