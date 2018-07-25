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

    >>>> itinerum = Itinerum(config=datakit_config)
    >>>> itinerum.setup()


Once the data has been loaded to the cache, each surveyed user's data
is available as a list of ::py:class:User objects::

    >>>> users = itinerum.load_all_users()
    >>>> len(users[0].coordinates)


Run Trip Detection on a User
----------------------------
To be added.
