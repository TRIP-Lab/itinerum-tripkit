Configuration
=============

The **itinerum-tripkit** is configured by a global configuration object that is passed to
the class at initialization. This can be created either as a Python file of 
global variables that is imported or defined as a bare class Config object and named
``tripkit_config``.


..  _ConfigAnchor:

Generating the Configuration
----------------------------
The following parameters are accepted by **itinerum-tripkit**:


.. tabularcolumns:: |p{6.5cm}|p{6.5cm}|

============================================= ===============================================
``DATABASE_FN``                               The filename to be used for the cache
                                              SQLite database.
``INPUT_DATA_DIR``                            Directory of the unpacked TripKit
                                              export .csv files. Usually a subdirectory
                                              of the ``./input`` directory.
``INPUT_DATA_TYPE``                           Data source: ``itinerum`` or ``qstarz``
``OUTPUT_DATA_DIR``                           Output directory to save processed export data.
``SUBWAY_STATIONS_FP``                        Relative filepath of subway .csv data for
                                              connecting gaps during trip detection
                                              algorithms.
``TRIP_DETECTION_BREAK_INTERVAL_SECONDS``     Minimum stop time for breaking GPS coordinates
                                              into trips.
``TRIP_DETECTION_SUBWAY_BUFFER_METERS``       Buffer in meters for associating a trip end
                                              with a subway station entrance.
``TRIP_DETECTION_COLD_START_DISTANCE_METERS`` Leeway distance in meters for allowing a
                                              device acquire a GPS fix before inferring that
                                              an intemediary trip with missing data has
                                              occured.
``TRIP_DETECTION_ACCURACY_CUTOFF_METERS``     Minimum horizontal accuracy in meters for
                                              including GSP points within trip detection
                                              algorithms. Greater values indicate worse
                                              accuracy; generally 30-50 is deemed an
                                              acceptable range.
============================================= ===============================================

**Process parameters**

These parameters are only needed if their related processes will be run.

.. tabularcolumns:: |p{6.5cm}|p{6.5cm}|

============================================= ===============================================
``TIMEZONE``                                  The timezone name as described within the
                                              tzdata database for complete days detection
                                              (e.g., America/Montreal)

``SEMANTIC_LOCATIONS``                        Mapping of semantic locations to *latitude*
                                              *longitude* columns within survey responses
                                              (see below for example).
``SEMANTIC_LOCATION_PROXIMITY_METERS``        Buffer distance in meters to consider a GPS
                                              point to be at a semantic location.
============================================= ===============================================

**Extra parameters**

These parameters are to configure plug-in processes (OSRM map matching API below). Check the
plug-in source code to see what is expected in these cases.

============================================= ===============================================
``MAP_MATCHING_BIKING_API_URL``               Endpoint for OSRM bicycle network map
                                              maptching.
``MAP_MATCHING_DRIVING_API_URL``              Endpoint for OSRM car network map maptching.
``MAP_MATCHING_WALKING_API_URL``              Endpoint for OSRM foot network map maptching.
============================================= ===============================================
