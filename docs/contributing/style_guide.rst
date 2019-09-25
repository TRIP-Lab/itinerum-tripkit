.. _ContributingPage:

============
Contributing
============


Style Guide
===========

Notes
-----
The **itinerum-tripkit** is a modular library that is built to be extended. The most common place to contribute will be adding a new *process*
(`itinerum-tripkit/tripkit/process`) for modifying or building new GPS detection algorithms. The process filepath format is:
`tripkit/process/<descriptive-name>/<organization>/library_files.py`. Try to group additions as best as possible within existing directories if
a one exists, but otherwise it is encouraged to be descriptive. If a suitable name doesn't exist, it's better to create a new directory altogether.

Database
++++++++
Library readability is prioritized over absolute execution performance, although both are desired. To keep the Python code base neater, 
the Peewee ORM is used for database operations. Peewee is used instead of SQLAlchemy to help keep the library compact while providing 
comparable functionality. The database functions are intended to be SQL database agnostic, however, bulk inserts for initial data loading
is tightly coupled to SQLite. Additional database engines will require specially handling data import from *.csv*.

Algorithms
++++++++++
Included algorithms follow the format of:
    1. Input user, user.coordinates, user.trips, etc. objects from the database
    2. Perform processing with a siblings ``models.py`` tightly coupled to the processing script. The methods should be primarily getters/setters
and helper methods, the core processing should try to occur entirely in the algorithm scripts to help keep the intention of each step obvious.
    3. Algorithm models should be "wrapped for datakit" which is mapping the algorith's generally more complex model to the library's base
models for general usage. The base model should be as simple as possible to limit what must be stored in the database; if an attribute like
duration can be inferred from a `start` and `end` timestamp, this is preferred over storing the value.


Pull Commits
------------
Python black_ is used to format all library code into a consistent format. Note that two options are used:

* line limit of 120 characters (-l 120)
* skip string normalization (-S, explained below)
::

$ black -l 120 -S -t py37 tripkit

The string formatting exception to Python blacks default rules is to better convey meaning about intention within the library. Internal strings such
as dictionary keys and filenames use single-quote (`'`) endings whereas strings that will print to the user such as log messages use double-quote (`"`)
endings.

.. _black: https://black.readthedocs.io/
