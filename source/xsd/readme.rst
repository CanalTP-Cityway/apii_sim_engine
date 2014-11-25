********
APIISIM
********

Regenerate python interface files from xsd
==========================================

#. Install GenerateDS tool

   ``apt-get install python-pip python-imaging libxml2-dev libxslt1-dev``

   ``pip install lxml``

   ``install generateDS``

#. Build python files

   ``/usr/local/bin/generateDS.py -o "../apiisim/common/mis_capabilities.py" MisCapabilities.xsd``

   ``/usr/local/bin/generateDS.py -o "../apiisim/common/mis_collect_stops.py" MisCollectStops.xsd``

   ``/usr/local/bin/generateDS.py -o "../apiisim/common/mis_plan_summed_up_trip.py" MisPlanSummedUpTrips.xsd``

   ``/usr/local/bin/generateDS.py -o "../apiisim/common/mis_plan_trip.py" MisPlanTrip.xsd``

   ``/usr/local/bin/generateDS.py -o "../apiisim/common/plan_trip.py" PlanTrip.xsd``
