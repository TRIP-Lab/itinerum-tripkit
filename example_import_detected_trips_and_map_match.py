#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datakit import Itinerum
import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)


# -- Stage 1: load platform data to cache
itinerum.setup(force=True)

# manually load detected trips from platform to a database table
itinerum.csv.load_trips('./input/trips_20171106.csv')


# -- Stage 2: select user data and process points
## a manually selected trip to perform test map matching on
uuid = 'a9611f09-acbe-416f-9b2a-f5d760be29cd'
user = itinerum.database.load_user(uuid, start=datetime(2018, 4, 11), end=datetime(2018, 4, 12))


## perform mapmatching using OSRM API
mapmatched_results = itinerum.process.map_match.osrm.match(coordinates=user.coordinates, matcher='WALKING')


# -- Stage 3: write input and output data to geojsons
## write user coordinates to geojson as points
itinerum.io.write_input_geojson(cfg=datakit_config,
                                fn_base=uuid,
                                coordinates=user.coordinates,
                                prompts=user.prompt_responses,
                                cancelled_prompts=user.cancelled_prompt_responses)

## write user detected trip points and links as linestrings to geojson
itinerum.io.write_trips_geojson(cfg=datakit_config, fn_base=uuid, trips=user.trips)

## write map matching points and matched links as linestrings to geojson
itinerum.io.write_mapmatched_geojson(cfg=datakit_config, fn_base=uuid, results=mapmatched_results)

