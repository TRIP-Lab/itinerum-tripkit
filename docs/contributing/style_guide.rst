.. _StyleGuidePage:

Contributing the itinerum-datakit
=================================


Notes
-----
Itinerum-datakit is a modular library that is built to be extended. The most common place to contribute will be adding a new __process__
(`itinerum-datakit/datakit/process`) for modifying or building new GPS detection algorithms. The process filepath format is:
`../process/<descriptive-name>/<organization>/library_files.py`. Try to group additions as best as possible within existing directories if
a one exists, but otherwise it is encouraged to be descriptive. If a suitable name doesn't exist, it's better to create a new directory altogether.


Did you know?


Pull Commits
------------
Python black_ is used to format all library code into a consistent format. Note that two options are used: line limit of 120 characters (-l 120)
and skip string normalization (-S, explained below).::

$ black -l 120 -S -t py37 datakit

The string formatting exception to Python blacks default rules is to better convey meaning about intention within the library. Internal strings such
as dictionary keys and filenames use single-quote (') endings whereas strings that will print to the user such as log messages use double-quote (")
endings.

.. _black: https://black.readthedocs.io/
