#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datakit import Itinerum

import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)

# -- Stage 1: load trip detection results via library algorithms
users = itinerum.load_users(limit=5)

for idx, user in enumerate(users, start=1):
    print('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
    if user.trips:
        results = itinerum.process.complete_days.triplab.counter.run(user.trips)
    else:
        print('No trips available for: {}'.format(user.uuid))