*********************************************
How to build APIISIM components and run them
*********************************************

Dependencies
============

#. Python

   * psycopg2
   * sqlalchemy
   * flask
   * geoalchemy2
   * flask-restful (https://github.com/l-vincent-l/flask-restful) **patched version**
   * python-mod-pywebsocket (needed by planner webservice)   
   * websocket-client (only needed by 'planner_client' module, can be skipped using 'planner_client_no_ws' module)
   * jsonschema (only needed by test clients)

#. Other

   * apache2
   * postgresql (9.3+)
   * postgis (2+)

You can use the given *install_deps.sh* script that will install all required
dependencies (tested on Debian 7 only).

Build & Install
===============

#. Firstly, install git

   ``apt-get install git``

#. Get the source from git

   ``git clone https://github.com/CanalTP-Cityway/apii_sim_engine.git -b master /tmp/apiisim``

#. Install all required dependencies (you must have root privileges)

   ``cd /tmp/apiisim/source``

   ``./install_deps.sh``

#. If postgresql wasn't previously installed, you need to set a password for the "postgres" user (you must have root privileges)

   ``su postgres``

   ``psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"``

   ``exit``

#. Build and install the package (you must have root privileges)

   ``./install.sh``

Launching components
==================

In this example, we'll setup APIISIM components using the default configuration,
which only uses stub MIS based on some data provided by CanalTP Navitia API. 
To customize the setup to your liking, you can edit the following configuration files:

Metabase settings (MIS definition)

   * apiisim/metabase/sql_scripts/default.conf (linux)
   * apiisim/metabase/sql_scripts/default.conf.cmd (windows)
   * apiisim/metabase/sql_scripts/populate_db_mis_only_stubs.sql

Planner settings

   * /etc/apache2/mods-enabled/python.conf

You may certainly have to change Postgresql username and password in those files 
to match your setup.


#. Creating the metabase

   The first step is to create the database that will store data shared by all components.
   In this step, we'll also populate the database with every MIS that will be used
   to calculate itineraries.
   To do so, we execute the provided *create_db.sh* linux script or *create_db.cmd* window 
   script. Here, we only use stub MIS, to add other MIS API, just edit the SQL script that 
   populates the database (*apiisim/metabase/sql_scripts/populate_db_mis_only_stubs.sql*).

   ``cd apiisim/metabase/sql_scripts/``

   ``./create_db.sh default.conf`` (linux)
   
   ``./create_db.cmd default.conf.cmd`` (windows)

#. Launch mis_translator

   The mis_translator is a Web service that acts as an abstraction layer for
   both the back_office and the planner to allow them to communicate with different MIS
   via a unique API. Therefore, it must always be up and running so that the
   back office and the planner can work properly. (except if you use your own connector)

   ``cd /usr/local/lib/python2.7/dist-packages/apiisim-0.1-py2.7.egg/apiisim/mis_translator/``

   ``nohup python run.py --log /var/log/apiisim/mis_translator.log &``

   #. Check with mis_translator_client
   
   Run mis_translator_client example to check that this component is working properly.

   ``cd /tmp/apiisim/source/apiisim/test_clients/mis_translator_client/``

   ``python mis_translator_client.py``

#. Launch back_office

   It will retrieve stops from all MIS configured in the database,
   calculate transfers between those stops and deduce connections between
   MIS. This will provide to APIISIM components what is needed to compute
   trips.

   ``cd /usr/local/lib/python2.7/dist-packages/apiisim-0.1-py2.7.egg/apiisim/back_office/``

   ``python run.py --config default.conf``

   The back_office does some pretty heavy calculations so this step can last a few
   minutes.

#. Launch the planner web socket service

   This is the most important component, the one that actually calculates "meta-trips".
   As it is an Apache module, not a standalone program, it should already be running
   but in doubt, you can restart Apache.

   ``/etc/init.d/apache2 restart``

   Entry point of web service should be here:

   ``/var/www/pywebsocket/handlers/planner_wsh.py``

   #. Check with planner_client

   Run planner_client example to check that all components are up and working properly.

   ``cd /tmp/apiisim/source/apiisim/test_clients/planner_client``

   ``python planner_client.py``

   Check computation algorithm regardless to web socket issues:

   ``python planner_client_no_ws.py``
