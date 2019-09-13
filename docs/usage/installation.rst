Installation
============

The ``itinerum-tripkit`` can be installed as a library using pip or the included `setup.py` file, or can be included in
as an included dependency in your own project by cloning: http://github.com/TRIP-Lab/itinerum-tripkit and copying the ``tripkit`` directory.


Virtual Environments
--------------------
It is recommended to use venv_ to keep the tripkit dependency versions isolated from system packages.

Linux & MacOS
+++++++++++++
::

    $ python3 -m venv tripkit-venv
    $ chmod +x tripkit-ven/bin/activate
    $ source ./tripkit-ven/bin/activate

Windows
+++++++

**PowerShell:**
With PowerShell, `Set-ExecutionPolicy Unrestricted -Force` may be required to allow the `Activate.ps1` 
script to run. If you update the permissions, the PowerShell prompt must also be restarted.:
::

    PS C:\Code\itinerum-tripkit> python -m venv tripkit-venv
    PS C:\Code\itinerum-tripkit> .\tripkit-venv\Scripts\Activate.ps1


Dependencies
------------
Linux & MacOS
+++++++++++++

Project dependencies can be installed with pip::

    (tripkit-venv) $ pip install -r requirements.txt


Windows
+++++++
GDAL
~~~~
First the GDAL library must be installed for geospatial operations. If it hasn't already been installed on your system with OSGeo4W or some other means,
the easiest way is from the gisinternals.com pre-compiled binaries. For your system version (in 2019, likely MSVC 2017 / x64), click "Downloads". From the downloads
page, the core GDAL library is all that is needed ("gdal-204-1911-64-core.msi"). Install this file and set two Windows environment variables:
- Append the PATH: C:\Program Files\GDAL
- Create GDAL_DATA: C:\Program Files\GDAL\gdal-data
After these variables have been set, close and re-open the terminal (and re-activate the virtual env if using). Next, the Python dependencies can been installed.

Compiled Python Packages
~~~~~~~~~~~~~~~~~~~~~~~~
On Windows, some packages may fail to install without their pre-existing build dependencies. Compiled wheel versions can be
downloaded from various mirrors (i.e., https://www.lfd.uci.edu/~gohlke/pythonlibs), copied to the local directory and installed with pip directly.::

    (tripkit-venv) PS C:\Code\itinerum-tripkit> pip install .\Fiona-1.8.6-cp37-cp37m-win_amd64.whl

Compiled packages to install:

* https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
* https://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona
* https://www.lfd.uci.edu/~gohlke/pythonlibs/#scikit-learn


.. _venv: https://docs.python.org/3/library/venv.html
.. _`Bulk Inserts`: http://docs.peewee-orm.com/en/latest/peewee/querying.html#bulk-inserts
