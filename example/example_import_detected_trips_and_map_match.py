#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
# run from parent directory
import os
import sys
import tripkit_config_itinerum as cfg

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
import logging
from datetime import datetime
from tripkit import TripKit

logging.basicConfig(level=logging.INFO)
logging.getLogger('itinerum-tripkit').setLevel(level=logging.DEBUG)


# Edit ./tripkit_config.py and populate trip detection coordinates in cache db first!
tripkit = TripKit(config=cfg)


# -- Stage 1: load platform data to cache
tripkit.setup()


# -- Stage 2: select user data and process points
# a manually selected trip to perform test map matching on
user = tripkit.load_users(
    uuid='00807c5b-7542-4868-8462-14b79a9fcc9f', start=datetime(2017, 11, 29), end=datetime(2017, 11, 30)
)
map_matcher = tripkit.process.map_match.osrm(cfg)
mapmatched_results = map_matcher.match(coordinates=user.coordinates, matcher='DRIVING')


# -- Stage 3: write input and output data to geojsons
# write user coordinates to geojson as points
tripkit.io.geojson.write_inputs(
    fn_base=user.uuid,
    coordinates=user.coordinates,
    prompts=user.prompt_responses,
    cancelled_prompts=user.cancelled_prompt_responses,
)

# write user detected trip points and links as linestrings to geojson
tripkit.io.geojson.write_trips(fn_base=user.uuid, trips=user.trips)

# write map matching points and matched links as linestrings to geojson
tripkit.io.geojson.write_mapmatch(fn_base=user.uuid, results=mapmatched_results)
