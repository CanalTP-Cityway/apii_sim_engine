import os
from base import MisApi as StubApi

NAME = "stub_bourgogne"


class MisApi(StubApi):
    _STOPS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "stub_bourgogne_stops.json")
    _DB_NAME = "stub_bourgogne_db"
