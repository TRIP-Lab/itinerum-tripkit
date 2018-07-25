.. _QuickStartPage:

Quick Start
===========
The most common workflow is downloading data from the Itinerum web
platform and running the data through a sequence of scripts to clean
and process the GPS data. Itinerum-datakit makes this easy by
loading the `.csv` text data into a type-checked SQLite database. This
could be easily changed to support other SQL variants such as PostgreSQL,
SQLite is the default library for portability.


Load Data
---------
When the configuration has been created (see :ref:`ConfigAnchor`), `.csv` data be loaded to
the itinerum-datakit cache database as easily as::

    >>>> from datakit import Itinerum
    >>>> import datakit_config

    >>>> itinerum = Itinerum(config=datakit_config)
    >>>> itinerum.setup()


Once the data has been loaded to the cache, each surveyed user's data
is available as a list of :py:class:`User` objects::

    >>>> users = itinerum.load_users()
    >>>> len(users[0].coordinates)


Run Trip Detection on a User
----------------------------
Instead of running trip detection on the whole survey, it is possible to
focus on a single user in detail. For writing new processing libraries, this
is often essential.

.. code-block:: python

    >>>> user = itinerum.load_users(uuid='00000000-0000-0000-0000-000000000000')[0]
    >>>> parameters = {
             'subway_stations': itinerum.database.load_subway_entrances(),
             'break_interval_seconds': datakit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
             'subway_buffer_meters': datakit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
             'cold_start_distance': datakit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
             'accuracy_cutoff_meters': datakit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
         }
    >>>> trips, summaries = itinerum.process.trip_detection.triplab.algorithm.run(user.coordinates.dicts(),
                                                                                  parameters)

