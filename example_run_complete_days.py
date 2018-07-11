#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datakit import Itinerum

import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)

# -- Stage 1: load trip detection results via library algorithms
users = itinerum.load_users()

trip_day_summaries = []
for idx, user in enumerate(users, start=1):
    print('Processing user ({}) trips: {}/{}...'.format(user.uuid, idx, len(users)))
    if user.trips:
        results = itinerum.process.complete_days.triplab.counter.run(user.trips)
        for date, row in results.items():
            row['uuid'] = user.uuid
            row['date_UTC'] = date
            trip_day_summaries.append(row)
    else:
        print('No trips available for: {}'.format(user.uuid))

print('Saving complete day summaries to database...')
itinerum.database.save_trip_day_summaries(trip_day_summaries)
