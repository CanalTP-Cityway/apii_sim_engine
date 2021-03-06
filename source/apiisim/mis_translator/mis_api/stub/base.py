# -*- coding: utf8 -*-

"""
    Generic Mis API stub class. It retrieves stops from a JSON file, then creates
    and populates a database with them. When receiving itinerary requests, several
    implementations are available:
        - one that returns random itineraries by randomly choosing stops in its database.
            -> _RandomMisApi
        - one that returns shortest itineraries based on "as the crow flies"
          distance between stop points (using PostGIS). Although simplistic, it
          provides much more meaningful results than the random stub.
            -> _CrowFliesMisApi
        - other implementations, useful for some testing cases.
"""
import json
import logging
import traceback
import os
from datetime import timedelta, datetime
from random import randint

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Distance, GenericFunction

from apiisim.mis_translator.mis_api import MisApiBase, MisCapabilities
from apiisim.common import PlanSearchOptions, TransportModeEnum, PublicTransportModeEnum, SelfDriveModeEnum, \
    TypeOfPlaceEnum
from apiisim.common.mis_collect_stops import StopPlaceType, QuayType, CentroidType, LocationStructure
from apiisim.common.mis_plan_trip import EndPointType, TripStopPlaceType, TripType, PTNetworkType, SectionType, \
    LegType, StepEndPointType, StepType, LineType, PTRideType
from apiisim.common.mis_plan_summed_up_trip import SummedUpTripType
from apiisim import metabase


NAME = "stub_base"

DB_ADMIN_NAME = "postgres"
DB_ADMIN_PASS = "postgres"

DB_TRIGGER = \
    """
    CREATE OR REPLACE FUNCTION stop_pre_update_handler()
    RETURNS trigger AS $$
    BEGIN
        -- When inserting, OLD is not defined so we have to make a special case for INSERT
        IF (TG_OP = 'INSERT') THEN
            NEW.geog:='POINT('||NEW.long||' '||NEW.lat||')';
        ELSE
            IF NEW.lat != OLD.lat OR NEW.long != OLD.long THEN
                NEW.geog:='POINT('||NEW.long||' '||NEW.lat||')';
            END IF;
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE 'plpgsql';

    CREATE TRIGGER stop_pre_update BEFORE INSERT OR UPDATE ON stop
    FOR EACH ROW
    EXECUTE PROCEDURE stop_pre_update_handler();
    """


class StGeogFromText(GenericFunction):
    name = 'ST_GeogFromText'
    type = Geography


Base = declarative_base()


class DbStop(Base):
    __tablename__ = 'stop'

    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False)
    name = Column(String, nullable=False)
    lat = Column(Float(53), nullable=False)
    long = Column(Float(53), nullable=False)
    geog = Column(Geography(geometry_type="POINT", srid=4326,
                            spatial_index=True))


def create_db(db_name):
    engine = create_engine("postgresql+psycopg2://%s:%s@localhost/postgres" %
                           (DB_ADMIN_NAME, DB_ADMIN_PASS),
                           echo=False)
    conn = engine.connect()
    # Delete database. If it doesn't exist, SQLAlchemy will raise an error,
    # just ignore it.
    try:
        conn.execute("COMMIT")
        conn.execute("DROP DATABASE IF EXISTS %s" % db_name)
        conn.execute("COMMIT")
        conn.execute("CREATE DATABASE %s" % db_name)
        conn.execute("COMMIT")
    except:
        logging.getLogger('exceptions').error(traceback.format_exc())
        raise
    finally:
        conn.close()
        engine.dispose()

    engine = create_engine("postgresql+psycopg2://%s:%s@localhost/%s" %
                           (DB_ADMIN_NAME, DB_ADMIN_PASS, db_name),
                           echo=False)
    conn = engine.connect()
    try:
        conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        conn.execute("COMMIT")
        Base.metadata.create_all(bind=engine)
        conn.execute(DB_TRIGGER)
    except:
        logging.getLogger('exceptions').error(traceback.format_exc())
        raise
    finally:
        conn.close()
        engine.dispose()


def connect_db(db_name):
    engine = create_engine("postgresql+psycopg2://%s:%s@localhost/%s" %
                           (DB_ADMIN_NAME, DB_ADMIN_PASS, db_name),
                           echo=False)
    return Session(bind=engine, expire_on_commit=False)


def populate_db(db_name, stops_file, stops_field):
    db_session = connect_db(db_name)
    try:
        with open(stops_file, 'r') as f:
            content = f.read()
            content = json.loads(content[content.find('{"%s"' % stops_field):])

        for s in content[stops_field]:
            new_stop = DbStop()
            new_stop.code = s["id"]
            new_stop.name = s["name"]
            new_stop.lat = s["coord"]["lat"]
            new_stop.long = s["coord"]["lon"]
            db_session.add(new_stop)
        db_session.commit()
    finally:
        db_session.close()
        db_session.bind.dispose()


# location is a LocationContextType object
def get_location_id(location):
    return location.PlaceTypeId or "%s;%s" % (location.Position.Longitude, location.Position.Latitude)


def random_date(min_date, max_date):
    if min_date and max_date:
        delta = (max_date - min_date).total_seconds()
    else:
        delta = 36000  # 10 hours
    if min_date:
        return min_date + timedelta(seconds=randint(0, delta))
    else:
        return max_date - timedelta(seconds=randint(0, delta))


# location is a LocationContextType object
def location_to_end_point(location, departure_time=None, arrival_time=None, point_time=None):
    ret = EndPointType()
    if point_time:
        ret.DateTime = point_time
    elif not departure_time and not arrival_time:
        ret.DateTime = None
    else:
        ret.DateTime = random_date(departure_time, arrival_time)
    place = TripStopPlaceType()
    place.id = get_location_id(location)
    place.Position = location.Position
    place.TypeOfPlaceRef = TypeOfPlaceEnum.LOCATION
    ret.TripStopPlace = place

    return ret


def generate_section(leg=False):
    ret = SectionType()
    ret.PartialTripId = "stub_id"

    end_point = EndPointType(
        TripStopPlace=TripStopPlaceType(
            id="stop_id",
            TypeOfPlaceRef=TypeOfPlaceEnum.LOCATION,
            Position=LocationStructure(Latitude=0, Longitude=0)))

    if not leg:
        ptr = PTRideType()
        line = LineType()
        line.id = "LINE:ID:387"
        line.Name = "Line 387"
        line.Number = "387"
        line.PublishedName = "Line 387"
        line.RegistrationNumber = "LINE:ID:387"
        ptr.Line = line

        network = PTNetworkType()
        network.id = "NETWORK:ID:241"
        network.Name = "Network 421"
        network.RegistrationNumber = "NETWORK:ID:241"
        ptr.PTNetwork = network

        ptr.PublicTransportMode = PublicTransportModeEnum.BUS
        ptr.Departure = end_point
        ptr.Arrival = end_point
        ptr.Departure.DateTime = datetime(year=2014, month=3, day=7)
        ptr.Arrival.DateTime = datetime(year=2014, month=3, day=7)
        ptr.Duration = timedelta(seconds=20)
        ptr.Distance = 100
        ptr.StopHeadSign = "Head Sign 387"
        ptr.steps = []
        step_end_point = StepEndPointType(
            TripStopPlace=TripStopPlaceType(
                id="stop_id",
                TypeOfPlaceRef=TypeOfPlaceEnum.LOCATION,
                Position=LocationStructure(Latitude=0, Longitude=0)))
        for i in range(0, 3):
            step = StepType()
            step.Departure = step_end_point
            step.Arrival = step_end_point
            step.id = "%s:%s" % (step.Departure.TripStopPlace.id, step.Arrival.TripStopPlace.id)
            step.Departure.DateTime = datetime(year=2014, month=3, day=7)
            step.Arrival.DateTime = datetime(year=2014, month=3, day=7)
            step.Duration = timedelta(seconds=10)
            ptr.steps.append(step)

        ret.PTRide = ptr
    else:
        leg = LegType()
        leg.Departure = end_point
        leg.Arrival = end_point
        leg.Departure.DateTime = datetime(year=2014, month=3, day=7)
        leg.Arrival.DateTime = datetime(year=2014, month=3, day=7)
        leg.Duration = timedelta(seconds=30)
        leg.SelfDriveMode = SelfDriveModeEnum.FOOT

        ret.Leg = leg

    return ret


class _StubMisApi(object):
    _initialized_databases = set([])

    def __init__(self, stops_file, stops_field, db_name):
        self._db_session = None
        if not (db_name in self.__class__._initialized_databases):
            create_db(db_name)
            populate_db(db_name, stops_file, stops_field)
            self.__class__._initialized_databases.add(db_name)
        self._db_session = connect_db(db_name)

    def __del__(self):
        if self._db_session:
            self._db_session.close()
            self._db_session.bind.dispose()

    def _generate_detailed_trip(self, departures, arrivals, departure_time, arrival_time):
        return None

    def _generate_summed_up_trip(self, departures, arrivals, departure_time, arrival_time):
        return None

    def get_capabilities(self):
        return MisCapabilities(True, True, [TransportModeEnum.ALL])

    def get_stops(self):
        ret = []
        stops = self._db_session.query(DbStop).all()
        for s in stops:
            ret.append(
                StopPlaceType(
                    id=s.id,
                    quays=[QuayType(
                        id=s.code,
                        Name=s.name,
                        PrivateCode=s.code,
                        Centroid=CentroidType(
                            Location=LocationStructure(
                                Longitude=s.long,
                                Latitude=s.lat)))]))

        return ret

    def get_itinerary(self, departures, arrivals, departure_time, arrival_time,
                      algorithm, modes, self_drive_conditions,
                      accessibility_constraint, language, options):
        return self._generate_detailed_trip(departures, arrivals, departure_time, arrival_time)

    def get_summed_up_itineraries(self, departures, arrivals, departure_time,
                                  arrival_time, algorithm,
                                  modes, self_drive_conditions,
                                  accessibility_constraint,
                                  language, options):
        ret = []
        if departure_time:
            for a in arrivals:
                ret.append(self._generate_summed_up_trip(departures, [a], departure_time, None))
        else:
            for d in departures:
                ret.append(self._generate_summed_up_trip([d], arrivals, None, arrival_time))

        logging.debug("Summed up trips (%s) : %s", len(ret), ret)

        return ret


# Return random itineraries.
class _RandomMisApi(_StubMisApi):
    def _generate_detailed_trip(self, departures, arrivals, departure_time, arrival_time):
        if len(departures) > 1 and len(arrivals) > 1:
            raise Exception("<generate_detailed_trip> only supports 1-n requests")

        ret = TripType()
        ret.id = "detailed_trip_id"
        ret.Duration = timedelta(seconds=randint(0, 36000))
        ret.Distance = randint(0, 10000)
        ret.Disrupted = False
        ret.InterchangeNumber = randint(0, 10)
        ret.sections = []

        if len(departures) > 1:
            departure = departures[randint(0, len(departures) - 1)]
            ret.Departure = location_to_end_point(departure, departure_time, arrival_time)
            ret.Arrival = location_to_end_point(arrivals[0], ret.Departure.DateTime, arrival_time)
        else:
            arrival = arrivals[randint(0, len(arrivals) - 1)]
            ret.Departure = location_to_end_point(departures[0], departure_time, arrival_time)
            ret.Arrival = location_to_end_point(arrival, ret.Departure.DateTime, arrival_time)

        for i in range(0, randint(0, 3)):
            ret.sections.append(generate_section(leg=True if i else False))

        return ret

    def _generate_summed_up_trip(self, departures, arrivals, departure_time, arrival_time):
        if len(departures) > 1 and len(arrivals) > 1:
            raise Exception("<generate_summed_up_trip> only supports 1-n requests")

        ret = SummedUpTripType()
        if len(departures) > 1:
            departure = departures[randint(0, len(departures) - 1)]
            ret.Departure = location_to_end_point(departure, departure_time, arrival_time)
            ret.Arrival = location_to_end_point(arrivals[0], ret.Departure.DateTime, arrival_time)
        else:
            arrival = arrivals[randint(0, len(arrivals) - 1)]
            ret.Departure = location_to_end_point(departures[0], departure_time, arrival_time)
            ret.Arrival = location_to_end_point(arrival, ret.Departure.DateTime, arrival_time)

        ret.InterchangeCount = randint(0, 10)
        ret.InterchangeDuration = randint(0, 1000)

        return ret


# Return itineraries based on "as the crow flies" distance between stops.
class _CrowFliesMisApi(_StubMisApi):
    # Return closest location to loc.
    def _get_earliest_location(self, loc, locations):
        distances = []  # [(LocationContextType, distance to loc (in meters))]

        if loc.PlaceTypeId:
            geog1 = self._db_session.query(metabase.Stop.geog) \
                .filter(metabase.Stop.code == loc.PlaceTypeId) \
                .subquery().c.geog
        else:
            geog1 = StGeogFromText('POINT(%s %s)' % (loc.Position.Longitude, loc.Position.Latitude))

        for l in locations:
            if l.PlaceTypeId:
                geog2 = self._db_session.query(metabase.Stop.geog) \
                    .filter(metabase.Stop.code == l.PlaceTypeId) \
                    .subquery().c.geog
            else:
                geog2 = StGeogFromText('POINT(%s %s)' % (l.Position.Longitude, l.Position.Latitude))

            distance = self._db_session.query(ST_Distance(geog1, geog2)).first()[0]
            duration = timedelta(minutes=distance // 1000)
            time_duration = duration + l.AccessTime
            distances.append((l, distance, duration, time_duration))

        distances.sort(key=lambda x: x[3])

        return distances[0][:3]

    def _generate_detailed_trip(self, departures, arrivals, departure_time, arrival_time):
        if len(departures) > 1 and len(arrivals) > 1:
            raise Exception("<generate_detailed_trip> only supports 1-n requests")

        ret = TripType()
        ret.id = "detailed_trip_id"
        ret.Disrupted = False
        ret.InterchangeNumber = 4
        ret.sections = []

        if len(departures) > 1:
            best_departure, distance, duration = self._get_earliest_location(arrivals[0], departures)
            if departure_time:
                ret.Departure = location_to_end_point(best_departure,
                                                      point_time=departure_time + best_departure.AccessTime)
                ret.Arrival = location_to_end_point(arrivals[0],
                                                    point_time=departure_time + best_departure.AccessTime + duration)
            elif arrival_time:
                ret.Departure = location_to_end_point(best_departure,
                                                      point_time=arrival_time - arrivals[0].AccessTime - duration)
                ret.Arrival = location_to_end_point(arrivals[0],
                                                    point_time=arrival_time - arrivals[0].AccessTime)
        else:
            best_arrival, distance, duration = self._get_earliest_location(departures[0], arrivals)
            if departure_time:
                ret.Departure = location_to_end_point(departures[0],
                                                      point_time=departure_time + departures[0].AccessTime)
                ret.Arrival = location_to_end_point(best_arrival, ret.Departure.DateTime,
                                                    point_time=departure_time + departures[0].AccessTime + duration)
            else:
                ret.Departure = location_to_end_point(departures[0],
                                                      point_time=arrival_time - best_arrival.AccessTime - duration)
                ret.Arrival = location_to_end_point(best_arrival, ret.Departure.DateTime,
                                                    point_time=arrival_time - best_arrival.AccessTime)

        ret.Distance = distance
        ret.Duration = duration
        for i in range(0, 3):
            ret.sections.append(generate_section(leg=True if i else False))
        # logging.debug("Departure %s %s", ret.Departure.TripStopPlace.id, ret.Departure.DateTime)
        # logging.debug("Arrival %s %s", ret.Arrival.TripStopPlace.id, ret.Arrival.DateTime)

        return ret

    def _generate_summed_up_trip(self, departures, arrivals, departure_time, arrival_time):
        if len(departures) > 1 and len(arrivals) > 1:
            raise Exception("<generate_summed_up_trip> only supports 1-n requests")

        ret = SummedUpTripType()

        if len(departures) > 1:
            best_departure, distance, duration = self._get_earliest_location(arrivals[0], departures)
            if departure_time:
                ret.Departure = location_to_end_point(best_departure,
                                                      point_time=departure_time + best_departure.AccessTime)
                ret.Arrival = location_to_end_point(arrivals[0],
                                                    point_time=departure_time + best_departure.AccessTime + duration)
            elif arrival_time:
                ret.Departure = location_to_end_point(best_departure,
                                                      point_time=arrival_time - arrivals[0].AccessTime - duration)
                ret.Arrival = location_to_end_point(arrivals[0],
                                                    point_time=arrival_time - arrivals[0].AccessTime)
        else:
            best_arrival, distance, duration = self._get_earliest_location(departures[0], arrivals)
            if departure_time:
                ret.Departure = location_to_end_point(departures[0],
                                                      point_time=departure_time + departures[0].AccessTime)
                ret.Arrival = location_to_end_point(best_arrival, ret.Departure.DateTime,
                                                    point_time=departure_time + departures[0].AccessTime + duration)
            else:
                ret.Departure = location_to_end_point(departures[0],
                                                      point_time=arrival_time - best_arrival.AccessTime - duration)
                ret.Arrival = location_to_end_point(best_arrival, ret.Departure.DateTime,
                                                    point_time=arrival_time - best_arrival.AccessTime)

        ret.InterchangeCount = randint(0, 10)
        ret.InterchangeDuration = randint(0, 1000)
        # logging.debug("Departure %s %s", ret.Departure.TripStopPlace.id, ret.Departure.DateTime)
        # logging.debug("Arrival %s %s", ret.Arrival.TripStopPlace.id, ret.Arrival.DateTime)

        return ret


# Used by unit test to simulate replies where no itinerary is found for some
# departure/arrival pairs.
class _IncompleteCrowFliesMisApi(_CrowFliesMisApi):
    def get_summed_up_itineraries(self, *args, **kwargs):
        trips = super(_IncompleteCrowFliesMisApi, self).get_summed_up_itineraries(*args, **kwargs)
        if trips:
            i = randint(0, len(trips) - 1)
            logging.debug("Deleting trip %s %s", trips[i].Departure.TripStopPlace.id,
                          trips[i].Arrival.TripStopPlace.id)
            trips.pop(i)

        return trips


# This class is a factory that instantiates a particular MIS API class based on
# the given config. It is useful for unit tests as we can choose what type of stub
# we use depending on test case.
class MisApi(object):
    # Values of these 3 attributes are dummy, they must just be overriden by
    # the "real" stub API.
    _STOPS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "stub_base_stops.json")
    _STOPS_FIELD = "stop_areas"
    _DB_NAME = "stub_base_db"

    def __new__(cls, config, api_key=""):
        global DB_ADMIN_NAME
        global DB_ADMIN_PASS

        # default MisApi class
        mis_api_class = "CrowFlies"

        if config.has_section("Stub"):
            if config.has_option('Stub', 'db_admin_name'):
                DB_ADMIN_NAME = config.get('Stub', 'db_admin_name')
            if config.has_option('Stub', 'db_admin_pass'):
                DB_ADMIN_PASS = config.get('Stub', 'db_admin_pass')
            if config.has_option('Stub', 'stub_mis_api_class'):
                mis_api_class = config.get('Stub', 'stub_mis_api_class')

        return eval("_%sMisApi" % mis_api_class)(cls._STOPS_FILE, cls._STOPS_FIELD, cls._DB_NAME)

    def __init__(self, config, api_key=""):
        pass
