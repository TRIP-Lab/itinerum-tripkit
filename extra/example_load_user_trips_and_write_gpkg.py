#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys

sys.path[0] = sys.path[0].replace('/extra', '')
os.chdir(sys.path[0])

# begin
from datakit import Itinerum
from pprint import pprint

import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)

# -- Load user trip from database and write as GIS file
uuid = '005991eb3c174a7cba3de66210910bf8'
user = itinerum.load_users(uuid=uuid)


pprint(user.survey_response)
print('num trips:', len(user.trips))

itinerum.io.write_trips_geopackage(datakit_config, fn_base=uuid, trips=user.trips)
