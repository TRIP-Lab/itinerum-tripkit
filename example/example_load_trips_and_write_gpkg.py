#!/usr/bin/env python
# Kyle Fitzsimmons, 2018-2019

# run from parent directory
import os
import sys
import tripkit_config_itinerum as cfg

sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)
# begin
import logging
from tripkit import TripKit

logging.basicConfig(level=logging.INFO)
logging.getLogger('itinerum-tripkit').setLevel(level=logging.DEBUG)


# Edit ./tripkit_config.py first!
tripkit = TripKit(config=cfg)
tripkit.setup()

# -- Load user trip from database and write as GIS file
print('Writing cached database trip to .gpkg file...')
user = tripkit.load_users(uuid='00807c5b-7542-4868-8462-14b79a9fcc9f')
tripkit.io.geopackage.write_trips(fn_base=user.uuid, trips=user.trips)
