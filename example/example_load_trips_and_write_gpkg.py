#!/usr/bin/env python
# Kyle Fitzsimmons, 2018-2019

# run from parent directory
import os
import sys

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
from tripkit import Itinerum

import tripkit_config


# Edit ./tripkit_config.py first!
itinerum = Itinerum(config=tripkit_config)

# -- Load user trip from database and write as GIS file
user = itinerum.load_users(uuid='00807c5b-7542-4868-8462-14b79a9fcc9f')
itinerum.io.write_trips_geopackage(tripkit_config, fn_base=user.uuid, trips=user.trips)
