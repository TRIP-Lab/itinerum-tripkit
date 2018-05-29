# itinerum-library

This library seeks to serve as a bootstrapping framework for processing data from the Itinerum platform in a standardized format. It is intended to be used through Jupyter for exploring data and to provide standardized Itinerum objects for standalone applications.

This repository should mirror the deployed version(s) of the Itinerum platform algorithms.

## Setup

### Configuration

All global configuration parameters are set through the `./config.py` file in the repository root directory. Specific parameters are discussed below in their related sections.

### Loading Platform Data

Data exported from the Itinerum dashboard can be read directly as .csv files. The source data folder should be placed within the `./data` directory and the `INPUT_DATA_DIR` config option (`config.py`) edited to reflect the source data directory name.

*Note: On first run, .csv data will be imported if the table*  `user_survey_responses` *does not exist in the output database. It is safe to delete the output .sqlite file to reset the library's cache.*

### Loading Subway Stations

Subway station data for trip detection can be loaded similarly to the Itinerum platform data. Place a .csv file of station entrances with the columns of 'x' (or 'longitude') and 'y' (or 'latitude'). Locations are expected as WGS84 lat/lon geographic coordinates. Edit the `SUBWAY_STATIONS_FP` config option to reflect the subway stations .csv filepath.

## Processing

The library is intended to work modularly with drop-in algorithm scripts for trip processing, map matching and mode inference. Therefore, the inputs to each stage should be standardized as described below.

#### Trip Detection

Trips can be detected using the library on a raw dataset or trips can be manually imported from the web platform by calling the `CSVParser.load_trips_data()` function with the trips .csv filepath. Any re-detection of trips or manual import will overwrite the existing trips table.

| Arguments         |                                                              |
| ----------------- | ------------------------------------------------------------ |
| `parameters`      | A dictionary to supply arbitrary kwargs to an algorithm      |
| `subway_stations` | A list of subway station entrance database objects containing `latitude` and `longitude` attributes |
| `coordinates`     | A timestamp-ordered list of coordinates as dicts for a specific user. Multiple users should be run in sequence and have their output coordinates concatenated into a single list after if desired. |

##### Thoughts

The `coordinates`  values should be provided as list of dictionaries instead of database models to provide better compatibility of the detection algorithms across applications. Since a variety of databases and ORMs could be used, it seems simpler to require input data is formatted as dict() than something like a NamedTuple to make the algorithm compatible across SQLAlchemy or Peewee.

#### Map Matching

 TBA



## Outputs

The aim of this library is to provide easy visualization of Itinerum data to assist in writing trip processing algorthms. Therefore at a minimum, the library provides exporting processed coordinates and traces as .geojson files (TBA: GeoPackage format). With a PostgreSQL backend for caching, PostGIS can be enabled (unimplemented) and a `geom` column generated for directly connection QGIS to the output data. The library should also easily provide methods for easily plotting GPS within Jupyter notebooks.

## Notes

Running the OSRM Docker containers indefinitely on routing server--must be in appropriate data directory:

```bash
docker run -d --restart always -p 5000:5000 -v $(pwd)/car:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm

docker run -d --restart always -p 5001:5000 -v $(pwd)/bicycle:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm

docker run -d --restart always -p 5002:5000 -v $(pwd)/foot:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm
```

