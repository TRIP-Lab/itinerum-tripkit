.. _QuickStartPage:

Quick Start
===========
The **itinerum-tripkit** library provides simple interfaces to load *.csv* data into a local SQLite database
and providing Python ``class`` objects (such as :py:class:`tripkit.models.User` and :py:class:`tripkit.models.Trip`)
to represent this data for processing and inferring metadata.

Load Data
---------
To initilize the libary, a configuration object is expected (see :ref:`ConfigAnchor`).

First, input .csv data be loaded to the **itinerum-tripkit** cache database:

.. code-block:: python

    from tripkit import TripKit
    import tripkit_config

    tripkit = TripKit(config=tripkit_config)
    tripkit.setup()

After data has been loaded to the database, survey participants or *users* can be loaded as a list of :py:class:`tripkit.models.User` objects:

.. code-block:: python

    users = tripkit.load_users()
    for user in users:
        print(len(user.coordinates))


*Note: On first run, .csv data will be imported if the table* :py:class:`user_survey_responses` *does not exist in the cache database.
To delete the cache, the temporary files can be deleted between runs.*


Run Trip Detection on a User
----------------------------
Instead of running trip detection on the whole survey, it is possible to focus on a single user in detail.
For writing new processing libraries, this is often an essential first step.

.. code-block:: python

    user = tripkit.load_users(uuid='00000000-0000-0000-0000-000000000000')
    params = {
        'load_subway_entrances': tripkit.database.load_subway_entrances(),
        'break_interval_seconds': tripkit_config.TRIP_DETECTION_BREAK_INTERVAL_SECONDS,
        'subway_buffer_meters': tripkit_config.TRIP_DETECTION_SUBWAY_BUFFER_METERS,
        'cold_start_distance': tripkit_config.TRIP_DETECTION_COLD_START_DISTANCE_METERS,
        'accuracy_cutoff_meters': tripkit_config.TRIP_DETECTION_ACCURACY_CUTOFF_METERS
    }
    trips = tripkit.process.trip_detection.triplab.algorithm.run(user.coordinates,
                                                                  parameters=params)


Run Complete Days Summaries on a User
-------------------------------------
When trips have been detected for a user, the complete days summary process can be run on individual users.
This will check to see if a day is "complete" (contains no missing trips), "incomplete", or "inactive". There
are additional rules to consider days as "complete" if there is an inactive day between two complete days;
it is recommended to review the `process source code`_.

.. code-block:: python

    user = tripkit.load_users(uuid='00000000-0000-0000-0000-000000000000')
    trip_day_summaries = tripkit.process.complete_days.triplab.counter.run(user.trips,
                                                                            tripkit_config.TIMEZONE)
    tripkit.database.save_trip_day_summaries(user, trip_day_summaries, tripkit_config.TIMEZONE)


Run Semantic Location Activity Detection on a User
--------------------------------------------------
If common user locations are available within survey responses or supplied separately (such as from the outputs of a
clustering process), dwell times from nearby GPS points can be tallied. Note: the ``Coordinate`` model is currently
created on-the-fly as demonstrated, but this should soon be available as an included library class-object.

.. code-block:: python

    Coordinate = namedtuple('Coordinate', ['latitude', 'longitude'])
    user = tripkit.load_users(uuid='00000000-0000-0000-0000-000000000000')
    locations = {
        'home': Coordinate(latitude=45.5, longitude=-73.5)
    }
    tripkit.io.write_activity_locations_geojson(tripkit_config, fn_base=user.uuid, locations=locations)
    summary = tripkit.process.activities.triplab.detect.run(
        user, locations, proximity_m=tripkit_config.ACTIVITY_LOCATION_PROXIMITY_METERS, timezone=tripkit_config.TIMEZONE)
    dwell_time_summaries = [summary]  # usually, multiple users would be summarized for output
    tripkit.io.write_user_summaries_csv(tripkit_config, dwell_time_summaries)


Run OSRM Map Matching on a Trip
-------------------------------
If an OSRM server is available, map matching queries can be passed to the API and the response saved to a GIS-friendly
format (*.geojson* or *.gpkg*). The API query is limited by URL length, so map matching should be done for a single trip
and especially long trips may have to be supplied in chunks.

.. code-block:: python

    user = tripkit.load_users(uuid='00807c5b-7542-4868-8462-14b79a9fcc9f',
                              start=datetime(2017, 11, 29),
                              end=datetime(2017, 11, 30))
    map_matcher = tripkit.process.map_match.osrm(tripkit_config)
    mapmatched_results = map_matcher.match(coordinates=user.coordinates, matcher='DRIVING')
    tripkit.io.write_mapmatched_geojson(cfg=tripkit_config, fn_base=user.uuid, results=mapmatched_results)

.. _process source code: https://github.com/TRIP-Lab/itinerum-tripkit/blob/master/tripkit/process/complete_days/triplab/counter.py
