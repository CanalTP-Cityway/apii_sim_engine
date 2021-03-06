#!/usr/bin/python
# -*- encoding: utf8 -*-
import unittest
import os
import Queue
import logging
from datetime import timedelta, datetime, date as date_type
from itertools import permutations

from apiisim import tests
from apiisim.planner import TraceStop, Planner
from apiisim.planner.plan_trip_calculator import PlanTripCalculator
from apiisim.common.plan_trip import PlanTripRequestType, EndPointType, \
    LocationPointType, LocationPointType, \
    LocationStructure
from apiisim.common.mis_plan_summed_up_trip import SummedUpTripType, TripStopPlaceType


TEST_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "")


def new_location(longitude, latitude):
    ret = LocationPointType()
    ret.AccessTime = timedelta(seconds=100)
    l = LocationStructure()
    l.Longitude = longitude
    l.Latitude = latitude
    ret.Position = l
    return ret


class TestPlanner(unittest.TestCase):
    def setUp(self):
        try:
            tests.drop_db()
        except:
            pass
        tests.create_db(populate_script=TEST_DIR + "test_planner.sql")
        self._planner = Planner("postgresql+psycopg2://%s:%s@localhost/%s" %
                                (tests.ADMIN_NAME, tests.ADMIN_PASS, tests.DB_NAME))

    def tearDown(self):
        # Force planner deletion to reset SQLAlchemy connection pool. Otherwise,
        # some connections can stay open, which will prevent us from deleting
        # the database.
        del self._planner
        tests.drop_db()

    def test_departure_at_detailed_trace(self):
        request = PlanTripRequestType()
        request.Departure = TraceStop(PlaceTypeId="departure")
        request.Arrival = TraceStop(PlaceTypeId="arrival")
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())

        for i in [2, 3, 4]:
            res = calculator._detailed_trace(range(1, i + 1))
            logging.debug(res)
            for j in range(0, i):
                k = j + 1
                self.assertEquals(res[j][0].get_name(), "mis%s" % k)
                if j == 0:
                    self.assertEquals(res[j][1][0].PlaceTypeId, "departure")
                    self.assertEquals(res[j][2][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][3][0].PlaceTypeId, "stop_code%s0" % (k + 1))
                elif j == (i - 1):
                    self.assertEquals(res[j][1][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][2][0].PlaceTypeId, "arrival")
                    self.assertEquals(res[j][3], None)
                else:
                    self.assertEquals(res[j][1][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][2][0].PlaceTypeId, "stop_code%s1" % k)
                    self.assertEquals(res[j][3][0].PlaceTypeId, "stop_code%s0" % (k + 1))

    def test_filter_traces(self):
        request = PlanTripRequestType()
        request.Departure = TraceStop(PlaceTypeId="departure")
        request.Arrival = TraceStop(PlaceTypeId="arrival")
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        self.assertEquals(calculator._filter_traces([[1, 2, 3, 4], [1, 3, 4], [4, 3, 1],
                                                     [2, 1, 4], [3, 4, 2], [3, 2, 4],
                                                     [1, 4, 3, 2], [4, 3, 1, 2], [3, 2, 1, 4]]),
                          [[1, 3, 4], [4, 3, 1], [1, 4, 3, 2]])

    def test_compute_traces(self):
        request = PlanTripRequestType()
        request.Departure = new_location(1, 1)
        request.Arrival = new_location(3, 3)
        request.DepartureTime = datetime.now()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        calculator.MAX_TRACE_LENGTH = 3
        # arrival mis not geographic compliant
        self.assertEquals(calculator.compute_traces(), [])

        request.Departure = new_location(1.4, 1.4)
        request.Arrival = new_location(4, 4)
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        calculator.MAX_TRACE_LENGTH = 3
        self.assertEquals(calculator.compute_traces(), [[2, 3, 4]])

        request.Departure = new_location(2, 2)
        request.Arrival = new_location(4, 4)
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        calculator.MAX_TRACE_LENGTH = 3
        # origin outside of mis shape
        self.assertEquals(calculator.compute_traces(), [])

        request.Departure = new_location(1, 1)
        request.Arrival = new_location(4, 4)
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        calculator.MAX_TRACE_LENGTH = 3
        self.assertEquals(calculator.compute_traces(), [[1, 4]])

        request.Departure = new_location(1, 1)
        request.Arrival = new_location(1.4, 1.4)
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        calculator.MAX_TRACE_LENGTH = 3
        self.assertEquals(calculator.compute_traces(), [[1, 2]])

        request.Departure = new_location(1, 1)
        request.Arrival = new_location(2, 2)
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        calculator.MAX_TRACE_LENGTH = 3
        # arrival outside of mis shape
        self.assertEquals(calculator.compute_traces(), [])

        request.Departure = new_location(1, 2)
        request.Arrival = new_location(3, 4)
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        calculator.MAX_TRACE_LENGTH = 3
        # unfound departure or arrival
        self.assertEquals(calculator.compute_traces(), [])

    def test_get_transfers(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())

        transfers = calculator._get_transfers(1, 2)
        self.assertEquals(len(transfers), 3)
        self.assertEquals(len(transfers[0]), 1)
        self.assertEquals(len(transfers[1]), 1)
        self.assertEquals(len(transfers[2]), 1)
        self.assertEquals(transfers[0][0], timedelta(seconds=10))
        self.assertEquals(transfers[1][0].PlaceTypeId, "stop_code10")
        self.assertEquals(transfers[2][0].PlaceTypeId, "stop_code20")

        transfers = calculator._get_transfers(1, 1)
        self.assertEquals(transfers, ([], [], []))

        transfers = calculator._get_transfers(1, 4)
        self.assertEquals(len(transfers), 3)
        self.assertEquals(len(transfers[0]), 1)
        self.assertEquals(len(transfers[1]), 1)
        self.assertEquals(len(transfers[2]), 1)
        self.assertEquals(transfers[0][0], timedelta(seconds=30))
        self.assertEquals(transfers[1][0].PlaceTypeId, "stop_code10")
        self.assertEquals(transfers[2][0].PlaceTypeId, "stop_code42")

        transfers = calculator._get_transfers(2, 4)
        self.assertEquals(transfers, ([], [], []))

        transfers = calculator._get_transfers(4, 2)
        self.assertEquals(transfers, ([], [], []))

        transfers = calculator._get_transfers(3, 4)
        self.assertEquals(len(transfers), 3)
        self.assertEquals(len(transfers[0]), 2)
        self.assertEquals(len(transfers[1]), 2)
        self.assertEquals(len(transfers[2]), 2)
        self.assertEquals(transfers[0][0], timedelta(seconds=10))
        self.assertEquals(transfers[0][1], timedelta(seconds=10))
        self.assertEquals(transfers[1][0].PlaceTypeId, "stop_code31")
        self.assertEquals(transfers[2][0].PlaceTypeId, "stop_code40")
        self.assertEquals(transfers[1][1].PlaceTypeId, "stop_code32")
        self.assertEquals(transfers[2][1].PlaceTypeId, "stop_code40")

        transfers = calculator._get_transfers(2, 3)
        self.assertEquals(len(transfers), 3)
        self.assertEquals(len(transfers[0]), 3)
        self.assertEquals(len(transfers[1]), 3)
        self.assertEquals(len(transfers[2]), 3)
        self.assertEquals(transfers[0][0], timedelta(seconds=10))
        self.assertEquals(transfers[0][1], timedelta(seconds=10))
        self.assertEquals(transfers[0][2], timedelta(seconds=20))
        self.assertEquals(transfers[1][0].PlaceTypeId, "stop_code21")
        self.assertEquals(transfers[2][0].PlaceTypeId, "stop_code30")
        self.assertEquals(transfers[1][1].PlaceTypeId, "stop_code22")
        self.assertEquals(transfers[2][1].PlaceTypeId, "stop_code30")
        self.assertEquals(transfers[1][2].PlaceTypeId, "stop_code23")
        self.assertEquals(transfers[2][2].PlaceTypeId, "stop_code30")

        transfers = calculator._get_transfers(2, 6)
        self.assertEquals(transfers, ([], [], []))

        # There is a transfer between MIS 3 and MIS 6 but it is not active,
        # so it should be ignored by _get_transfers().
        transfers = calculator._get_transfers(3, 6)
        self.assertEquals(transfers, ([], [], []))

        transfers1 = calculator._get_transfers(2, 3)
        transfers2 = calculator._get_transfers(3, 2)
        self.assertEquals(transfers1[0], transfers2[0])
        self.assertEquals([x.PlaceTypeId for x in transfers1[1]],
                          [x.PlaceTypeId for x in transfers2[2]])
        self.assertEquals([x.PlaceTypeId for x in transfers1[2]],
                          [x.PlaceTypeId for x in transfers2[1]])

    def test_get_surrounding_mis(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        date = date_type(year=2010, month=4, day=8)

        position = LocationStructure(Longitude=1, Latitude=1)
        self.assertEquals(calculator._get_surrounding_mis(position, date), {1})

        position = LocationStructure(Longitude=3, Latitude=3)
        # MIS 3 excluded (not geographic compliant)
        self.assertEquals(calculator._get_surrounding_mis(position, date), set([]))

        position = LocationStructure(Longitude=7, Latitude=33)
        self.assertEquals(calculator._get_surrounding_mis(position, date), set([]))

        position = LocationStructure(Longitude=0, Latitude=0)
        # MIS 3 excluded (not geographic compliant)
        self.assertEquals(calculator._get_surrounding_mis(position, date), {1, 2})

        position = LocationStructure(Longitude=1.4, Latitude=1.4)
        self.assertEquals(calculator._get_surrounding_mis(position, date), {2})

        position = LocationStructure(Longitude=2, Latitude=2)
        # outside of mis shape
        self.assertEquals(calculator._get_surrounding_mis(position, date), set([]))

    def test_get_mis_modes(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        self.assertEquals(calculator._get_mis_modes(1), {"bus", "tram"})
        self.assertEquals(calculator._get_mis_modes(2), {"bus", "tram"})
        self.assertEquals(calculator._get_mis_modes(3), {"tram", "funicular"})
        self.assertEquals(calculator._get_mis_modes(4), {"bus"})
        self.assertEquals(calculator._get_mis_modes(5), {"bus", "tram", "funicular"})
        self.assertEquals(calculator._get_mis_modes(6), set([]))

    def test_get_connected_mis(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        self.assertEquals(calculator._get_connected_mis(1), {2, 4})
        self.assertEquals(calculator._get_connected_mis(2), {1, 3})
        self.assertEquals(calculator._get_connected_mis(3), {2, 4})
        self.assertEquals(calculator._get_connected_mis(4), {1, 3})
        self.assertEquals(calculator._get_connected_mis(5), set([]))
        self.assertEquals(calculator._get_connected_mis(6), set([]))

    def test_get_trace_transfers(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        for l in [permutations([1, 2, 3]), permutations([1, 4, 6])]:
            for a, b, c in l:
                transfers = calculator._get_trace_transfers([a, b, c])
                self.assertEquals(transfers,
                                  {a: {b: calculator._get_transfers(a, b)},
                                   b: {c: calculator._get_transfers(b, c)}})

        for l in [permutations([1, 2, 3, 4]), permutations([1, 3, 4, 6])]:
            for a, b, c, d in l:
                transfers = calculator._get_trace_transfers([a, b, c, d])
                self.assertEquals(transfers,
                                  {a: {b: calculator._get_transfers(a, b)},
                                   b: {c: calculator._get_transfers(b, c)},
                                   c: {d: calculator._get_transfers(c, d)}})

    def test_get_providers(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        providers = calculator._get_providers([2, 1, 3])
        self.assertEquals(providers[0].Name, "mis2")
        self.assertEquals(providers[1].Name, "mis1")
        self.assertEquals(providers[2].Name, "mis3")
        self.assertEquals(providers[0].Url, "mis2_url")
        self.assertEquals(providers[1].Url, "mis1_url")
        self.assertEquals(providers[2].Url, "mis3_url")
        self.assertEquals(len(providers), 3)
        providers = calculator._get_providers([])
        self.assertEquals(providers, [])

    def test_generate_trace_id(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        self.assertEquals(calculator._generate_trace_id([2, 3, 4]), "2_3_4")
        self.assertEquals(calculator._generate_trace_id([2, 3, 4, 5, 6]), "2_3_4_5_6")
        self.assertEquals(calculator._generate_trace_id([1]), "1")
        self.assertEquals(calculator._generate_trace_id([]), "")

    def test_update_departures(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        departures = [TraceStop(PlaceTypeId="1"),
                      TraceStop(PlaceTypeId="2"),
                      TraceStop(PlaceTypeId="3"),
                      TraceStop(PlaceTypeId="4")]
        linked_stops = [TraceStop(PlaceTypeId="l1"),
                        TraceStop(PlaceTypeId="l2"),
                        TraceStop(PlaceTypeId="l3"),
                        TraceStop(PlaceTypeId="l4")]
        link_durations = [timedelta(seconds=20),
                          timedelta(seconds=40),
                          timedelta(seconds=60),
                          timedelta(seconds=80)]
        trips = [
            SummedUpTripType(
                Departure=EndPointType(
                    TripStopPlace=TripStopPlaceType(id="1"),
                    DateTime=datetime(year=2014, month=2, day=1))),
            SummedUpTripType(
                Departure=EndPointType(
                    TripStopPlace=TripStopPlaceType(id="0"),
                    DateTime=datetime(year=2014, month=2, day=2))),
            SummedUpTripType(
                Departure=EndPointType(
                    TripStopPlace=TripStopPlaceType(id="36"),
                    DateTime=datetime(year=2014, month=2, day=4))),
            SummedUpTripType(
                Departure=EndPointType(
                    TripStopPlace=TripStopPlaceType(id="3"),
                    DateTime=datetime(year=2014, month=2, day=21))),
        ]
        calculator._update_transition_departures(departures, linked_stops, link_durations, trips)
        self.assertEquals(len(departures), 2)
        self.assertEquals(departures[0].PlaceTypeId, "1")
        self.assertEquals(departures[0].departure_time, datetime(year=2014, month=2, day=1))
        self.assertEquals(departures[1].PlaceTypeId, "3")
        self.assertEquals(departures[1].departure_time, datetime(year=2014, month=2, day=21))
        self.assertEquals(len(linked_stops), 2)
        self.assertEquals(linked_stops[0].PlaceTypeId, "l1")
        self.assertEquals(linked_stops[1].PlaceTypeId, "l3")
        self.assertEquals(len(link_durations), 2)
        self.assertEquals(link_durations[0].seconds, 20)
        self.assertEquals(link_durations[1].seconds, 60)

    def test_update_arrivals(self):
        request = PlanTripRequestType()
        calculator = PlanTripCalculator(self._planner, request, Queue.Queue())
        arrivals = [TraceStop(PlaceTypeId="1"),
                    TraceStop(PlaceTypeId="2"),
                    TraceStop(PlaceTypeId="3"),
                    TraceStop(PlaceTypeId="4")]
        linked_stops = [TraceStop(PlaceTypeId="l1"),
                        TraceStop(PlaceTypeId="l2"),
                        TraceStop(PlaceTypeId="l3"),
                        TraceStop(PlaceTypeId="l4")]
        link_durations = [timedelta(seconds=20),
                          timedelta(seconds=40),
                          timedelta(seconds=60),
                          timedelta(seconds=80)]
        trips = [
            SummedUpTripType(
                Arrival=EndPointType(
                    TripStopPlace=TripStopPlaceType(id="1"),
                    DateTime=datetime(year=2014, month=2, day=1))),
            SummedUpTripType(
                Arrival=EndPointType(
                    TripStopPlace=TripStopPlaceType(id="0"),
                    DateTime=datetime(year=2014, month=2, day=2))),
            SummedUpTripType(
                Arrival=EndPointType(
                    TripStopPlace=TripStopPlaceType(id="4"),
                    DateTime=datetime(year=2014, month=2, day=26))),
            SummedUpTripType(
                Arrival=EndPointType(
                    TripStopPlace=TripStopPlaceType(id="43"),
                    DateTime=datetime(year=2014, month=2, day=4))),
        ]
        calculator._update_transition_arrivals(arrivals, linked_stops, link_durations, trips)
        self.assertEquals(len(arrivals), 2)
        self.assertEquals(arrivals[0].PlaceTypeId, "1")
        self.assertEquals(arrivals[0].arrival_time, datetime(year=2014, month=2, day=1))
        self.assertEquals(arrivals[1].PlaceTypeId, "4")
        self.assertEquals(arrivals[1].arrival_time, datetime(year=2014, month=2, day=26))
        self.assertEquals(len(linked_stops), 2)
        self.assertEquals(linked_stops[0].PlaceTypeId, "l1")
        self.assertEquals(linked_stops[1].PlaceTypeId, "l4")
        self.assertEquals(len(link_durations), 2)
        self.assertEquals(link_durations[0].seconds, 20)
        self.assertEquals(link_durations[1].seconds, 80)


if __name__ == '__main__':
    unittest.main()
