# itinerum-tripkit

[![Python Version](https://img.shields.io/badge/Python-3.6%7C3.7-blue.svg?style=flat-square)]()

Documentation for library usage: https://itinerum-tripkit.readthedocs.io/

This library serves as a bootstrapping framework to process data from the Itinerum platform and hardward GPS loggers in a standardized format. It can be used both through Jupyter for exploring data interactively and imported as a module in standalone applications.

This repository also acts as the development grounds for the version(s) of the Itinerum platform algorithms within the Github TRIPLab repositories. 

## Setup

### Quickstart

1. Clone this repository and `pip install -r requirements.txt` ([virtualenv](https://virtualenv.pypa.io/en/stable/) and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) are recommended)
2. Place source data in the `./input` folder (create if necessary) and edit `./tripkit/config.py` with the appropriate filepaths.

Then either:

 - Start Jupyter in repository directly and get started by `from tripkit import Itinerum`

   *or*

 - Copy the `tripkit` directory into other projects as a library (until more complete packaging is available)

For more complete installation information (e.g., on Windows), see the official [itinerum-tripkit documentation] (https://itinerum-tripkit.readthedocs.io/en/stable/usage/installation.html).


### Loading Subway Stations

Subway station data for trip detection can be loaded similarly for all processing modules. Place a *.csv* file of station entrances with the columns of `x` (or `longitude`) and `y` (or `latitude`). Locations are expected as geographic coordinates only. Edit the `SUBWAY_STATIONS_FP` config parameter to reflect the subway stations *.csv* filepath.

#### Example

*View attributes on a User*

```python
import tripkit_config
itinerum = Itinerum(tripkit_config)

# create a new database and read in .csv data
itinerum.setup()

# load all users from database
users = itinerum.load_all_users()

test_user = users[0]
print(test_user.coordinates)
print(test_user.prompt_responses)
```

*Run trip detection on a User*

```python
import tripkit_config
itinerum = Itinerum(tripkit_config)

# load user from database by uuid
user = itinerum.database.load_user('00000000-0000-0000-0000-000000000000')

# run a provided trip detection algorithm
parameters = {
    'subway_stations': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
}
trips, summaries = itinerum.process.trip_detection.triplab.algorithm.run(user.coordinates.dicts(), 
                                                                         parameters)
```

## Processing

#### Trip Detection

Trips can be detected using the library on a raw dataset or trips can be manually imported from the web platform by calling the `load_trips_data()` method. Any re-detection of trips or manual import will overwrite the existing trips table.

| Arguments         |                                                              |
| ----------------- | ------------------------------------------------------------ |
| `parameters`      | A dictionary to supply arbitrary kwargs to an algorithm      |
| `subway_stations` | A list of subway station entrance database objects containing `latitude` and `longitude` attributes |
| `coordinates`     | A timestamp-ordered list of coordinates as dicts for a specific user. Multiple users should be run in sequence and have their output coordinates concatenated into a single list after if desired. |

#### Outputs

Trips will be output with the following trip codes to indicate the type of trip:

| Trip Code | Description                         |
| --------- | ----------------------------------- |
| 1         | Complete trip                       |
| 2         | Complete trip - subway              |
| 101       | Missing trip                        |
| 102       | Missing trip - subway               |
| 103       | Missing trip - less than 250m       |
| 201       | Single point                        |
| 202       | Distance too short - less than 250m |

#### Map Matching

The instructions that follow use the Multi-Level Djikstra processing pipelines recommended [here](https://github.com/Project-OSRM/osrm-backend/wiki/Running-OSRM) by Project OSRM.

##### Installing the OSRM API with Docker containers

1. Download an OSM extract for your region, such as for Québec

   ```bash
   $ mkdir osrm && cd osrm
   $ wget http://download.geofabrik.de/north-america/canada/quebec-latest.osm.pbf
   ```

2. Process the OSM data using the default network profiles included with OSRM:

   ```bash
   # car
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/quebec-latest.osm.pbf
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/quebec-latest
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/quebec-latest
   $ mkdir car
   $ mv quebec-latest.orsm* car
   
   # bike
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/bicycle.lua /data/quebec-latest.osm.pbf
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/quebec-latest
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/quebec-latest
   $ mkdir bicycle
   $ mv quebec-latest.orsm* bicycle
   
   # walking
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/quebec-latest.osm.pbf
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/quebec-latest
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/quebec-latest
   $ mkdir foot
   $ mv quebec-latest.orsm* foot
   ```

3. Run the Docker OSRM routing API on ports 5000-5002

   ```bash
   $ docker run -d --restart always -p 5000:5000 -v $(pwd)/car:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm
   
   $ docker run -d --restart always -p 5001:5000 -v $(pwd)/bicycle:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm
   
   $ docker run -d --restart always -p 5002:5000 -v $(pwd)/foot:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm
   ```

## Outputs
The aim of this library is to provide easy visualization of Itinerum data to assist in writing trip processing algorthms. Therefore at a minimum, the library provides exporting processed coordinates and traces as .geojson files (TBA: GeoPackage format). With a PostgreSQL backend for caching, PostGIS can be enabled (unimplemented) and a `geom` column generated for directly connection QGIS to the output data. The library should also easily provide methods for easily plotting GPS within Jupyter notebooks.
