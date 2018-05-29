#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datakit import Itinerum, geo


## Edit ./datakit/config.py first!
itinerum = Itinerum()


# -- Stage 1: load platform data to cache if surveys responses table does not exist
itinerum.setup(force=False)

# manually load detected trips from platform to a database table
itinerum.csv_parser.load_trips_data('./input/trips_20180430.csv')


# -- Stage 2: select user data and process points
## a manually selected trip to perform test map matching on
uuid = '7BE73473-5AF6-42CB-BBAF-2C2C6A3A7BD7'
user = itinerum.load_user(uuid, start=datetime(2018, 5, 9), end=datetime(2018, 5, 10))


## perform mapmatching using OSRM API
mapmatched_results = itinerum.osrm.match(coordinates=user.coordinates, matcher='DRIVING')


# -- Stage 3: write input and output data to geojsons
## write user coordinates to geojson as points
geo.write_input_geojson(fn_base=uuid,
                        coordinates=user.coordinates,
                        prompts=user.prompt_responses,
                        cancelled_prompts=user.cancelled_prompt_responses)

## write user detected trip points and links as linestrings to geojson
geo.write_trips_geojson(fn_base=uuid, trips=user.trips)

## write map matching points and matched links as linestrings to geojson
geo.write_mapmatched_geojson(fn_base=uuid, results=mapmatched_results)

