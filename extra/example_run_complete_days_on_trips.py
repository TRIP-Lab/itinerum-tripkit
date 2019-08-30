#!/usr/bin/env python
# Kyle Fitzsimmons, 2018

# run from parent directory
import os
import sys

sys.path[0] = sys.path[0].replace('/extra', '')
os.chdir(sys.path[0])

# begin
from datakit import Itinerum

import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)


# -- Stage 1: load trip detection results via library algorithms
#             and save complete day counts to cache database
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


# -- Stage 2: load from cache database and write complete day summaries to .csv
print('Loading complete day summaries from cache...')
trip_day_summaries = {}
for user in users:
    trip_day_summaries[user.uuid] = itinerum.database.load_trip_day_summaries(user)

print('Saving complete day summaries to .csv...')
csv_name = datakit_config.DATABASE_FN.split('.')[0] + '.csv'
itinerum.io.write_complete_days_csv(datakit_config, csv_name, trip_day_summaries)
