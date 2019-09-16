Installation
============

The **itinerum-tripkit** can be installed as a library using pip or the included `setup.py` file, or can be included in
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
page, the core GDAL library is all that is needed ("gdal-204-1911-64-core.msi").

Install this file and set two Windows environment variables:

- Append to PATH: C:\Program Files\GDAL
- Create GDAL_DATA: C:\Program Files\GDAL\gdal-data

After setting these variables, close and re-open the command prompt (re-activate the virtual env if using) and the Python dependencies can be installed.

Compiled Python Packages
~~~~~~~~~~~~~~~~~~~~~~~~
On Windows, some packages may fail to install without their pre-existing build dependencies. Compiled wheel versions can be
downloaded from various mirrors (i.e., https://www.lfd.uci.edu/~gohlke/pythonlibs), copied to the local directory and installed with pip directly.::

    (tripkit-venv) PS C:\Code\itinerum-tripkit> pip install .\Fiona-1.8.6-cp37-cp37m-win_amd64.whl

Compiled packages to install:

* GDAL: https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
* Fiona: https://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona
* Scikit-learn: https://www.lfd.uci.edu/~gohlke/pythonlibs/#scikit-learn


Optional Components
-------------------
OSRM
++++

The **itinerum-tripkit** provides interfaces for submitting map matching queries to an OSRM API and writing results to file.

The instructions that follow use the `Multi-Level Djikstra processing pipelines` recommended by Project OSRM.

Installing the OSRM API with Docker containers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Download an OSM extract for your region (ex. Québec)

.. code-block:: bash

   $ mkdir osrm && cd osrm
   $ wget http://download.geofabrik.de/north-america/canada/quebec-latest.osm.pbf


2. Process the OSM data using the default network profiles included with OSRM:

.. code-block:: bash

   # car
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/quebec-latest.osm.pbf
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/quebec-latest
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/quebec-latest
   $ mkdir car
   $ mv quebec-latest.orsm* car
   
   # bike
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/bicycle.lua /data/quebec-latest.osm.pbf
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/quebec-latest
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/quebec-latest
   $ mkdir bicycle
   $ mv quebec-latest.orsm* bicycle
   
   # walking
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/quebec-latest.osm.pbf
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/quebec-latest
   $ docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/quebec-latest
   $ mkdir foot
   $ mv quebec-latest.orsm* foot

3. Run the Docker OSRM API containers on ports ``5000-5002`` to reverse proxy for public access

.. code-block:: bash
   $ docker run -d --restart always -p 5000:5000 -v $(pwd)/car:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm
   
   $ docker run -d --restart always -p 5001:5000 -v $(pwd)/bicycle:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm
   
   $ docker run -d --restart always -p 5002:5000 -v $(pwd)/foot:/data osrm/osrm-backend osrm-routed --algorithm MLD --max-matching-size=5000 /data/quebec-latest.osrm


.. _venv: https://docs.python.org/3/library/venv.html
.. _Bulk Inserts: http://docs.peewee-orm.com/en/latest/peewee/querying.html#bulk-inserts
.. _Multi-Level Djikstra processing pipelines:https://github.com/Project-OSRM/osrm-backend/wiki/Running-OSRM