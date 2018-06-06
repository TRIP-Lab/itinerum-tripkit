# itinerum-datakit

[![Python Version](https://img.shields.io/badge/Python-3.6-blue.svg?style=flat-square)]()

This library seeks to serve as a bootstrapping framework to processing data from the Itinerum platform in a standardized format. It is both to be used through Jupyter for exploring data and to provide easy-to-use Itinerum objects in standalone applications.

This repository should mirror the deployed version(s) of the Itinerum platform algorithms.

## Setup

### Quickstart

 - Clone this repository and `pip install -r requirements.txt` ([virtualenv](https://virtualenv.pypa.io/en/stable/) and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) are recommended)
 - Place source data in the `./input` folder and edit `./datakit/config.py` with the appropriate filepaths.

Either

 - Start Jupyter in repository directy and get started by `from datakit import Itinerum`

   *or*

 - The included `datakit` directory can be copied to other projects as a library until more complete packaging is available

### Loading Platform Data

Data exported from the Itinerum dashboard is read directly as .csv files. The source data folder should be placed within the `./input` directory and the `INPUT_DATA_DIR` config option edited to reflect the filepath.

*Note: On first run, .csv data will be imported if the table*  `user_survey_responses` *does not exist in the output database. It is safe to delete the output .sqlite file to reset the library's cache.*

### Loading Subway Stations

Subway station data for trip detection can be loaded similarly to the Itinerum platform data. Place a .csv file of station entrances with the columns of `x` (or `longitude`) and `y` (or `latitude`). Locations are expected as lat/lon geographic coordinates only. Edit the `SUBWAY_STATIONS_FP` config option to reflect the subway stations .csv filepath.

### Example

*View attributes on a User*

```python
import datakit_config
itinerum = Itinerum(datakit_config)

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
import datakit_config
itinerum = Itinerum(datakit_config)

# load user from database by uuid
user = itinerum.database.load_user('00000000-0000-0000-0000-000000000000')

# run a provided trip detection algorithm
parameters = {
'subway_stations': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
}
trips = itinerum.process.trip_detection.triplab.algorithm.run(users, parameters)
```



## Processing

The library is intended to work modularly with drop-in algorithm scripts for trip processing, map matching and mode inference. Therefore, the inputs to each stage should be standardized as described below.

#### Trip Detection

Trips can be detected using the library on a raw dataset or trips can be manually imported from the web platform by calling the `load_trips_data()` method with the trips .csv filepath. Any re-detection of trips or manual import will overwrite the existing trips table.

| Arguments         |                                                              |
| ----------------- | ------------------------------------------------------------ |
| `parameters`      | A dictionary to supply arbitrary kwargs to an algorithm      |
| `subway_stations` | A list of subway station entrance database objects containing `latitude` and `longitude` attributes |
| `coordinates`     | A timestamp-ordered list of coordinates as dicts for a specific user. Multiple users should be run in sequence and have their output coordinates concatenated into a single list after if desired. |

##### Thoughts

The `coordinates`  values should be provided as list of dictionaries instead of database models to provide better compatibility of the detection algorithms across applications. Since a variety of databases and ORMs could be used, it seems simpler to require input data is formatted as dict() than something like a NamedTuple to make the algorithm compatible across SQLAlchemy or Peewee.

#### Map Matching

The instructions that follow use the Mult-Level Djikstra processing pipelines recommended [here](https://github.com/Project-OSRM/osrm-backend/wiki/Running-OSRM) by Project OSRM.

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

## To Do

Add Sphinx autodoc to generate automatic library documentation.
