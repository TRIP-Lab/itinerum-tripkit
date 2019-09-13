.. _QuickStartPage:

Quick Start
===========
The most common workflow is downloading data from the Itinerum web platform and running the data through various operations to clean
and infer usable trip information from GPS data. *Itinerum-tripkit* makes this simple by loading the .csv text data into a type-checked 
SQLite database and then constructing generalized library objects (such as :py:class:`tripkit.models.User` and :py:class:`tripkit.models.Trip`)
to represent this data between processing modules. This could be changed to support other SQL variants such as PostgreSQL, but SQLite is 
chosen as the default library for portability.


Load Data
---------
When the configuration has been created (see :ref:`ConfigAnchor`), input .csv data be loaded to the itinerum-tripkit cache database as follows:

.. code-block:: python

    from tripkit import Itinerum
    import tripkit_config

    itinerum = Itinerum(config=tripkit_config)
    itinerum.setup()

When the data has been loaded to the cache database, each surveyed user's data is available as a list of :py:class:`tripkit.models.User` objects:

.. code-block:: python

    users = itinerum.load_users()
    for user in users:
        print(len(user.coordinates))


*Note: On first run, .csv data will be imported if the table* :py:class:`user_survey_responses` *does not exist in the cache database.
It is safe to delete the accompanying .sqlite file to reset the library's cache.*


Run Trip Detection on a User
----------------------------
Instead of running trip detection on the whole survey, it is possible to focus on a single user in detail.
For writing new processing libraries, this is often an essential first step.

.. code-block:: python

    user = itinerum.load_users(uuid='00000000-0000-0000-0000-000000000000')[0]
    params = {
        'subway_stations': itinerum.database.load_subway_entrances(),
        'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
        'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
        'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
        'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
    }
    trips, summaries = itinerum.process.trip_detection.triplab.algorithm.run(user.coordinates.dicts(),
                                                                             parameters=params)


Run Complete Days Summaries on a User
-------------------------------------
When trips have been detected for a user, the complete days summary process can be run on individual users.
This will check to see if a day is "complete" (contains no missing trips), "incomplete", or "inactive". There
are some additional rules to consider days as complete if there is an inactive day between two complete days and
it is recommended to review the process source code.

.. code-block:: python

    user = itinerum.load_users(uuid='00000000-0000-0000-0000-000000000000')[0]
    trip_day_summaries = itinerum.process.complete_days.triplab.counter.run(user.trips, tripkit_config.TIMEZONE)
    itinerum.database.save_trip_day_summaries(user, trip_day_summaries, tripkit_config.TIMEZONE)
