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
import utm

from .models import Coordinate
from tripkit.utils import calc, geo

logger = logging.getLogger('itinerum-tripkit.process.canue.preprocess')


def rolling_window_avg(values, idx, size=20):
    half_size = int(size / 2)
    # do not calculate when not enough preceding values in window
    if (idx - 1) < half_size:
        return
    # do not calculate when not enough trailing values in window
    if (len(values) - (idx + 1)) < half_size:
        return
    lower_idx = idx - half_size
    upper_idx = idx + half_size
    return sum(values[lower_idx:upper_idx]) / (size + 1)

def run(uuid, coordinates):
    total_coordinates = coordinates.count()
    logger.info(f"Uncleaned input coordinates: {total_coordinates}")

    processed = []
    last_gc = None
    last_pct = 0
    logger.info(f"Processing...{last_pct}%")
    for idx, c in enumerate(coordinates):
        pct = int((idx / total_coordinates) * 100)
        update_pct = pct != last_pct and pct % 5 == 0
        if update_pct:
            logger.info(f"Processing...{pct}%", )
            last_pct = pct
        c.uuid = uuid
        gc = Coordinate(c)

        # calculate coordinate attributes compared to previous coordinate
        if not last_gc:
            gc.easting, gc.northing, gc.zone_num, gc.zone_letter = utm.from_latlon(gc.latitude, gc.longitude)
            processed.append(gc)
            last_gc = gc
            continue
        gc.duration_s = geo.duration_s(last_gc, gc)
        gc.distance_m = geo.haversine_distance_m(last_gc, gc)
        gc.bearing = geo.bearing(last_gc, gc)
        gc.delta_heading = geo.delta_heading(last_gc, gc)

        # skip points with speed of 0
        if not gc.speed_ms:
            continue
        if gc.distance_m < 0.1:
            continue
        ## filter points that are not within valid points threshold:
        ## - 50 meters per second (180 km/h; Schuessler and Axhausen, 2009)
        ## - 120 seconds (Wolf, 2000)
        ## - 250 meters (considered as "underground travel"; Bialostozky, 2009)
        # if gc.speed_ms <= 50 and (gc.distance_m <= 250 or gc.duration_s <= 120):
        #     processed.append(gc)

        # augment with projected coordinates
        gc.easting, gc.northing, gc.zone_num, gc.zone_letter = utm.from_latlon(gc.latitude, gc.longitude)
        processed.append(gc)
        last_gc = gc
    logger.info(f"Processing...100%")

    # update rolling averages
    distance_values, delta_heading_values = [], []
    for c in processed:
        distance_values.append(c.distance_m)
        delta_heading_values.append(c.delta_heading)
    for idx, gc in enumerate(processed):
        gc.avg_distance_m = rolling_window_avg(distance_values, idx)
        gc.avg_delta_heading = rolling_window_avg(delta_heading_values, idx)
    logger.info(f"Cleaned input coordinates: {len(processed)}")
    return processed
