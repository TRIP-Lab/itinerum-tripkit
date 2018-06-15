Configuration
=============

Itinerum-datakit is configured by a global configuration object that is passed to
the class at initialization. This can be created either as a Python file of 
global variables that is important or defined as a bare class Config object.


..  _ConfigAnchor:

Generating the Configuration
----------------------------
The following parameters are accepted by itinerum-datakit.


.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

============================================= ==============================================
``DATABASE_FN``                               The filename to be used for the cache
                                              SQLite database
``INPUT_DATA_DIR``                            Directory of the unpacked Itinerum
                                              export .csv files. Usually a subdirectory
                                              of the ``./input`` directory.
``OUTPUT_DATA_DIR``                           Directory to export processed data into
``TRIP_DETECTION_BREAK_INTERVAL_SECONDS``     Minimum stop time for breaking GPS coordinates
                                              into trips
``TRIP_DETECTION_SUBWAY_BUFFER_METERS``       Buffer in meters for associating a trip end
                                              with a subway station entrance
``TRIP_DETECTION_COLD_START_DISTANCE_METERS`` Leeway distance in meters for allowing a
                                              device acquire a GPS fix before inferring that
                                              an intemediary trip with missing data has
                                              occured.
``TRIP_DETECTION_ACCURACY_CUTOFF_METERS``     Minimum horizontal accuracy in meters for
                                              including GSP points within trip detection
                                              algorithms. Greater values indicate worse
                                              accuracy; generally 30-50 is deemed an
                                              acceptable range.
============================================= ==============================================