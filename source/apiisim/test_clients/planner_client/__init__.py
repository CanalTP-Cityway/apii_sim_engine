from apiisim.common import AlgorithmEnum, TransportModeEnum
from apiisim.common.plan_trip import PlanTripRequestType, LocationPointType, LocationStructure, \
    PlanTripCancellationRequest, EndingSearch, PlanTripNotificationResponseType, \
    PlanTripExistenceNotificationResponseType, PlanTripResponse, StartingSearch
from apiisim.common.mis_plan_trip import LocationContextType
from random import randint
import datetime


class TripCollection:
    def __init__(self):
        pass

    @staticmethod
    def _new_location(place_id, longitude, latitude):
        ret = LocationContextType()
        ret.PlaceTypeId = place_id
        l = LocationStructure()
        l.Longitude = longitude
        l.Latitude = latitude
        ret.Position = l

        return ret

    @staticmethod
    def _new_request(departure, arrival, req_time=None, clockwise=True):
        ret = PlanTripRequestType()

        ret.clientRequestId = "request_" + str(randint(0, 60000))
        now = req_time if req_time else datetime.datetime.now() - datetime.timedelta(days=10)

        if clockwise:
            ret.DepartureTime = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=now.hour,
                                                  minute=now.minute)
            ret.ArrivalTime = None
        else:
            ret.DepartureTime = None
            ret.ArrivalTime = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=now.hour,
                                                minute=now.minute)

        ret.Departure = departure
        ret.Arrival = arrival

        ret.MaxTrips = 10
        ret.Algorithm = AlgorithmEnum.CLASSIC
        ret.modes = [TransportModeEnum.ALL]
        ret.selfDriveConditions = []
        ret.AccessibilityConstraint = False
        ret.Language = ""

        return ret

    @staticmethod
    def paris_reims(req_time=None, clockwise=True):
        return TripCollection._new_request(
            TripCollection._new_location(None, 2.348294, 48.858108),  # Chatelet (IDF)
            TripCollection._new_location(None, 4.034720, 49.262780),  # Reims (Champagne)
            req_time, clockwise)

    @staticmethod
    def orly_reims(req_time=None, clockwise=True):
        return TripCollection._new_request(
            TripCollection._new_location(None, 2.369208, 48.729012),  # Orly (IDF)
            TripCollection._new_location(None, 5.051595, 47.332904),  # Reims (Champagne)
            req_time, clockwise)

    @staticmethod
    def bergson_vieville(req_time=None, clockwise=True):
        return TripCollection._new_request(
            TripCollection._new_location(None, 2.181307, 48.841171),  # Begson (IDF)
            TripCollection._new_location(None, 5.135272, 48.239439),  # Vieville (Champagne)
            req_time, clockwise)

    @staticmethod
    def paris_reims(req_time=None, clockwise=True):
        return TripCollection._new_request(
            TripCollection._new_location(None, 2.3467106, 48.8594808),  # Begson (IDF)
            TripCollection._new_location(None, 4.0225421, 49.2334403),  # Vieville (Champagne)
            req_time, clockwise)