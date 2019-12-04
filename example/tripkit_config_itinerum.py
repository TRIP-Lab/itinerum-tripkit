#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


SURVEY_NAME = 'cfse'

# path of raw data directory exported from Itinerum platform or Qstarz
INPUT_DATA_DIR = './input/cfse-csv'
# types: "itinerum" or "qstarz"
INPUT_DATA_TYPE = 'itinerum'

# path of export data from itinerum-cli
OUTPUT_DATA_DIR = './output'

# path of subway station entrances .csv for trip detection
SUBWAY_STATIONS_FP = './input/subway_stations/mtl_stations.csv'

# trip detection parameters
TRIP_DETECTION_BREAK_INTERVAL_SECONDS = 300
TRIP_DETECTION_SUBWAY_BUFFER_METERS = 300
TRIP_DETECTION_COLD_START_DISTANCE_METERS = 750
TRIP_DETECTION_ACCURACY_CUTOFF_METERS = 50

# timezone of study area for calculating complete trip days
TIMEZONE = 'America/Montreal'

# location radius for activity dwell tallies
SEMANTIC_LOCATIONS = {
    'home': ['location_home_lat', 'location_home_lon'],
    'work': ['location_work_lat', 'location_work_lon'],
    'study': ['location_study_lat', 'location_study_lon']
}
ACTIVITY_LOCATION_PROXIMITY_METERS = 50

# OSRM map matcher API URLs
MAP_MATCHING_BIKING_API_URL = 'https://mapper.triplab.ca/osrm/match/v1/biking/'
MAP_MATCHING_DRIVING_API_URL = 'https://mapper.triplab.ca/osrm/match/v1/driving/'
MAP_MATCHING_WALKING_API_URL = 'https://mapper.triplab.ca/osrm/match/v1/walking/'