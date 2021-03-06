#!/usr/bin/env python
# Kyle Fitzsimmons, 2019

# 0: setup - run from parent directory
import os
import sys
sys.path[0] = os.path.abspath(os.path.pardir)
os.chdir(os.path.pardir)

# begin
from tripkit import Itinerum
import tripkit_config

STAGE_1 = True
STAGE_2 = True
STAGE_3 = True
STAGE_4 = True
STAGE_5 = True


# 1: import .csv's from Itinerum or QStarz to scratch database and load user objects
itinerum = Itinerum(config=tripkit_config)
itinerum.setup(force=STAGE_1)

users = itinerum.load_users()
if not isinstance(users, list):
    users = [users]

# 2: run trip detection on user coordinates and save to database
if STAGE_2:
    # gert "stage 1" scripts: GPS Preprocessing Module (GPM)
    # TODO: integrate GPS pre-processing to GERT setup
    for user in users:
        gert_coordinates = itinerum.process.gert.gpm.run(user.coordinates)
        stops = itinerum.process.gert.detect_stops.run(gert_coordinates)

