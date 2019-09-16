.. _QuickStartPage:

Quick Start
===========
The most common workflow is downloading data from the Itinerum web platform and running the data through tripkit ``processes`` to clean
and infer usable trip information from GPS data. The *itinerum-tripkit* library provides simple interfaces to load download *.csv* data into a
local SQLite database and then providing Python ``class`` objects (such as :py:class:`tripkit.models.User` and :py:class:`tripkit.models.Trip`)
to represent this data for processing.

Load Data
---------
For any of the inlcuded library processes, a configuration object will be expected (see :ref:`ConfigAnchor`).

Input .csv data be loaded to the itinerum-tripkit cache database as follows:

.. code-block:: python

    from tripkit import Itinerum
    import tripkit_config

    itinerum = Itinerum(config=tripkit_config)
    itinerum.setup()

After data has been loaded to the database, survey users can be loaded as a list of :py:class:`tripkit.models.User` objects:

.. code-block:: python

    users = itinerum.load_users()
    for user in users:
        print(len(user.coordinates))


*Note: On first run, .csv data will be imported if the table* :py:class:`user_survey_responses` *does not exist in the cache database.
It is also safe to delete the accompanying .sqlite file to reset the library's cache.*


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
are additional rules to consider days as "complete" if there is an inactive day between two complete days;
it is recommended to review the `process source code`_.

.. code-block:: python

    user = itinerum.load_users(uuid='00000000-0000-0000-0000-000000000000')[0]
    trip_day_summaries = itinerum.process.complete_days.triplab.counter.run(user.trips, tripkit_config.TIMEZONE)
    itinerum.database.save_trip_day_summaries(user, trip_day_summaries, tripkit_config.TIMEZONE)


Run OSRM Map Match on a Trip
----------------------------
If an OSRM server is available, map matching queries can be passed to the API and the response saved to a GIS-friendly
format (*.geojson* or *.gpkg*). The API query is limited by URL length, so map matching should be done for a single trip
and especially long trips may have to be supplied in chunks.

.. code-block:: python

    user = itinerum.database.load_user(
        '00000000-0000-0000-0000-000000000000', start=datetime(2019, 1, 1), end=datetime(2019, 1, 2)
    )
    map_matcher = itinerum.process.map_match.osrm(tripkit_config)
    mapmatched_results = map_matcher.match(coordinates=user.coordinates, matcher='DRIVING')
    itinerum.io.write_mapmatched_geojson(cfg=tripkit_config, fn_base=user.uuid, results=mapmatched_results)

.. _process source code: https://github.com/TRIP-Lab/itinerum-tripkit/blob/master/tripkit/process/complete_days/triplab/counter.py
