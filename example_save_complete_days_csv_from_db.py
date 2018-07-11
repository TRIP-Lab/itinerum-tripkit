#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datakit import Itinerum

import datakit_config


## Edit ./datakit_config.py first!
itinerum = Itinerum(config=datakit_config)

# -- Stage 1: load trip detection results via library algorithms
users = itinerum.load_users()

# -- Stage 2: write complete day summaries to .csv
trip_day_summaries = {}
for user in users:
    trip_day_summaries[user.uuid] = itinerum.database.load_trip_day_summaries(user)

print('Saving complete day summaries to .csv...')
csv_name = datakit_config.DATABASE_FN.split('.')[0] + '.csv'
itinerum.io.write_complete_days_csv(datakit_config, csv_name, trip_day_summaries)
