# itinerum-tripkit

Documentation for library usage: https://itinerum-tripkit.readthedocs.io/

This library serves as a framework to process data from the Itinerum platform and hardware GPS loggers (e.g., QStarz). It can be used both through as a library in Jupyter to explore datasets interactively or imported as a module in standalone scripts and applications.

This repository also serves as the development bed for the Itinerum platform algorithms within the TRIP Lab repositories.

Looking to get started without coding? Try the [itinerum-tripkit-cli](https://github.com/TRIP-Lab/itinerum-tripkit-cli)!

## Setup

### Quickstart

1. Install this library from PyPI (a Python [virtual environment](https://docs.python.org/3/library/venv.html) is recommended)
2. Create a configuration file with input filepaths, output filepaths, and trip processing parameters. See the included `tripkit_config.py` file for a full example.
3. Import `tripkit` as a dependency in a notebook or script

For more complete installation information, see the official [itinerum-tripkit documentation](https://itinerum-tripkit.readthedocs.io/en/stable/usage/installation.html).

### Loading Subway Stations

Subway station data for trip detection can be loaded similarly for all processing modules. Place a _.csv_ file of station entrances with the columns of `x` (or `longitude`) and `y` (or `latitude`). Locations are expected as geographic coordinates only. Edit the `SUBWAY_STATIONS_FP` config parameter to reflect the subway stations _.csv_ filepath.

#### Example

_View attributes on a User_

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

_Run trip detection on a User_

```python
import tripkit_config
itinerum = Itinerum(tripkit_config)

# load user from database by uuid
user = itinerum.database.load_user('00000000-0000-0000-0000-000000000000')

# run a provided trip detection algorithm
parameters = {
    'subway_entrances': itinerum.database.load_subway_entrances(),
    'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
    'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
    'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
    'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
}
trips = itinerum.process.trip_detection.triplab.v2.algorithm.run(user.coordinates, parameters)
```

## Processing

#### Trip Detection

| Arguments         |                                                                                                                                                                                                    |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `parameters`      | A dictionary to supply arbitrary kwargs to an algorithm                                                                                                                                            |
| `subway_stations` | A list of subway station entrance database objects containing `latitude` and `longitude` attributes                                                                                                |
| `coordinates`     | A timestamp-ordered list of coordinates as dicts for a specific user. Multiple users should be run in sequence and have their output coordinates concatenated into a single list after if desired. |

#### Trip Outputs

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

## Outputs

The aim of this library is to provide easy visualization of Itinerum data to assist in writing trip processing algorthms. Therefore at a minimum, the library provides exporting processed coordinates and traces as .geojson files (TBA: GeoPackage format). With a PostgreSQL backend for caching, PostGIS can be enabled (unimplemented) and a `geom` column generated for directly connection QGIS to the output data. The library should also easily provide methods for easily plotting GPS within Jupyter notebooks.
