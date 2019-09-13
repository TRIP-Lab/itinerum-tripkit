#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
from datetime import datetime

from datakit import Itinerum
import datakit_config


# Edit ./datakit_config.py and populate trip detection coordinates in cache db first!
itinerum = Itinerum(config=datakit_config)


# -- Stage 1: load platform data to cache
itinerum.setup()

# -- Stage 2: select user data and process points
# a manually selected trip to perform test map matching on
user = itinerum.database.load_user('00807c5b-7542-4868-8462-14b79a9fcc9f',
                                   start=datetime(2017, 11, 29),
                                   end=datetime(2017, 11, 30))


# perform mapmatching using OSRM API
map_matcher = itinerum.process.map_match.osrm(datakit_config)
mapmatched_results = map_matcher.match(coordinates=user.coordinates, matcher='DRIVING')


# -- Stage 3: write input and output data to geojsons
# write user coordinates to geojson as points
itinerum.io.write_input_geojson(
    cfg=datakit_config,
    fn_base=user.uuid,
    coordinates=user.coordinates,
    prompts=user.prompt_responses,
    cancelled_prompts=user.cancelled_prompt_responses,
)

# write user detected trip points and links as linestrings to geojson
itinerum.io.write_trips_geojson(cfg=datakit_config, fn_base=user.uuid, trips=user.trips)

# write map matching points and matched links as linestrings to geojson
itinerum.io.write_mapmatched_geojson(cfg=datakit_config, fn_base=user.uuid, results=mapmatched_results)
