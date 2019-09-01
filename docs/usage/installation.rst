Installation
============

The ``itinerum-datakit`` can be installed as a library using pip or the included `setup.py` file, or can be included in
as an included dependency in your own project by cloning:

.. rst-class:: center

http://github.com/TRIP-Lab/itinerum-datakit

and copying the ``datakit`` directory.


Virtual Env
-----------
It is recommended to use venv_ to keep the datakit dependencies isolate from system Python packges.::

Linux & MacOS
+++++++++++++

    $ python3 -m venv datakit-venv
    $ chmod +x datakit-ven/bin/activate
    $ source ./datakit-ven/bin/activate

Windows
+++++++

PowerShell:

With PowerShell, `Set-ExecutionPolicy Unrestricted -Force` (be sure you understand the implications first!), may 
be required to allow the `Activate.ps1` script to run. Be sure to restart the PS prompt if you update the permissions.::

    PS C:\Code\itinerum-datakit> python -m venv datakit-venv
    PS C:\Code\itinerum-datakit> .\datakit-venv\Scripts\Activate.ps1


Dependencies
------------
Note: Although datakit may install fine in versions older than 3.7, the SQLite library (v. ?.?.?) bundled with previous
versions of Python will be too old for bulk insert database operations to function as intended. With larger surveys, this
will result in memory errors. (See note under "Bulk Inserts": http://docs.peewee-orm.com/en/latest/peewee/querying.html#bulk-inserts)

Linux & MacOS
+++++++++++++

Project dependencies can be installed with pip::

    (datakit-venv) $ pip install -r requirements.txt


Windows
+++++++

First the GDAL library must be installed for geospatial operations. If it hasn't already been installed on your system with OSGeo4W or some other means,
the easiest way is from the gisinternals.com pre-compiled binaries. For your system version (in 2019, likely MSVC 2017 / x64), click "Downloads". From the downloads
page, the core GDAL library is all that is needed ("gdal-204-1911-64-core.msi"). Install this file and set two Windows environment variables:
    - Append the PATH: C:\Program Files\GDAL
    - Create GDAL_DATA: C:\Program Files\GDAL\gdal-data
After these variables have been set, close and re-open the terminal (and re-activate the virtual env if using). Next, the Python dependencies can been installed.

On Windows, some packages may fail to install without their pre-existing build dependencies. Compiled wheel versions can be
downloaded from various mirrors (i.e., https://www.lfd.uci.edu/~gohlke/pythonlibs), copied to the local directory and installed with pip directly.::

    (datakit-venv) PS C:\Code\itinerum-datakit> pip install .\Fiona-1.8.6-cp37-cp37m-win_amd64.whl

Compiled packages to install:
- https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
- https://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona


.. _venv: https://docs.python.org/3/library/venv.html