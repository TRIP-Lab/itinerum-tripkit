#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datakit import Itinerum, processing


## Edit ./datakit/config.py first!
itinerum = Itinerum()


# -- Stage 1: load platform data to cache if surveys responses table does not exist
itinerum.setup(force=False)

## or perform trip detection via library algorithms
users = itinerum.load_all_users()
detected_trips = itinerum.run_trip_detection(processing.trip_detection.triplab.algorithm, users)
itinerum.save_trips(detected_trips)
