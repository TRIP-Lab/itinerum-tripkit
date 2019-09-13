#!/usr/bin/env python
# Kyle Fitzsimmons, 2019

# run from parent directory
import datetime
import os
import pytz
import sys
sys.path[0] = sys.path[0].replace('/debug', '')
os.chdir(sys.path[0])
# begin
from tripkit import Itinerum
import tripkit_config

from debug.debug_tools import v1_wrap_for_tripkit


# Edit ./tripkit_config.py first!
itinerum = Itinerum(config=tripkit_config)
itinerum.setup(force=False)
tz = pytz.timezone('America/Montreal')
start = datetime.datetime(2019, 3, 29, 0, 0, 0, tzinfo=tz)
end = datetime.datetime(2019, 3, 29, 23, 59, 59, tzinfo=tz)
users = itinerum.load_users()

parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
}

all_summaries = []
for idx, user in enumerate(users, start=1):
    print("Writing user data to file...")
    data_fn = f'{user.uuid}-input'
    itinerum.io.write_input_geopackage(tripkit_config,
                                       fn_base=data_fn,
                                       coordinates=user.coordinates,
                                       prompts=user.prompt_responses,
                                       cancelled_prompts=user.cancelled_prompt_responses)

    print(f"Processing user ({user.uuid}) trips: {idx}/{len(users)}...")
    parameters['subway_stations'] = parameters['subway_entrances']
    user.trips, summaries = itinerum.process.trip_detection.triplab.v1.algorithm.run(user.coordinates.dicts(),
                                                                                     parameters=parameters)
    fn1 = f'{user.uuid}-v1'
    v1_trips = v1_wrap_for_tripkit(user.trips)
    itinerum.io.write_trips_geopackage(tripkit_config, fn_base=fn1, trips=v1_trips)
    if summaries:
        all_summaries.extend(list(summaries.values()))

    trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters=parameters)
    fn2 = f'{user.uuid}-v2'
    itinerum.io.write_trips_geopackage(tripkit_config, fn_base=fn2, trips=trips)
    import sys; sys.exit()


# print('Writing summaries to .csv...')
# csv_filename = '{}-trip_summaries.csv'.format(tripkit_config.DATABASE_FN.split('.')[0])
# itinerum.io.write_trip_summaries_csv(tripkit_config, csv_filename, all_summaries)
