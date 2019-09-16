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
