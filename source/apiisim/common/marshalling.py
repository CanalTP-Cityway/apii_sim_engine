from flask_restful import fields, marshal as flask_marshal

from apiisim.common import timedelta_to_xsd_duration

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

"""
    Custom float marshaller as stock Flask float marshaller is buggy, it outputs
    float numbers as quoted strings (ex: "1.321" instead of 1.321).
    See https://github.com/twilio/flask-restful/pull/219.
"""


class _Float(fields.Raw):
    def format(self, value):
        try:
            return float(value)
        except ValueError as ve:
            raise fields.MarshallingException(ve)


"""
    Custom marshaller that converts Timedelta object to XSD duration string.
"""


class _Duration(fields.String):
    def format(self, value):
        try:
            return timedelta_to_xsd_duration(value)
        except Exception as e:
            raise fields.MarshallingException(e)


"""
    Custom DateTime marshaller that converts DateTime object to a DATE_FORMAT 
    formatted string.
"""


class _DateTime(fields.DateTime):
    def format(self, value):
        try:
            return value.strftime(DATE_FORMAT)
        except AttributeError as ae:
            raise fields.MarshallingException(ae)


"""
    Ignore null elements when marshalling.
    Note that it only works when using our customized flask library. When using stock
    flask library, this is equivalent to fields.Nested (null elements will 
    therefore still be there after marshalling).
"""


class NonNullNested(fields.Nested):
    def __init__(self, *args, **kwargs):
        super(NonNullNested, self).__init__(*args, allow_null=True, **kwargs)
        self.display_null = False


"""
    Ignore null elements when marshalling.
    Note that it only works when using our customized flask library. When using stock
    flask library, this is equivalent to fields.List (null elements will 
    therefore still be there after marshalling).
"""


class NonNullList(fields.List):
    def __init__(self, *args, **kwargs):
        super(NonNullList, self).__init__(*args, **kwargs)
        self.display_empty = False


"""
    Ignore None attributes. Note that this is not recursive, only top-level
    attributes will be filtered, attributes in nested objects won't. 
    Use NonNullNested class to filter nested objects.
"""


def marshal(obj, f):
    if isinstance(obj, list):
        return [marshal(x, f) for x in obj]

    ret = flask_marshal(obj, f)
    items = ret.iteritems()
    for k, v in items:
        if v is None:
            del ret[k]
    return ret


location_structure_type = {
    'Latitude': _Float,
    'Longitude': _Float
}

location_context_type = {
    'PlaceTypeId': fields.String,
    'Position': NonNullNested(location_structure_type),
    'AccessTime': _Duration,
}

self_drive_condition_type = {
    'TripPart': fields.String,
    'SelfDriveMode': fields.String,
}

multi_departures_type = {
    'Departure': fields.List(NonNullNested(location_context_type)),
    'Arrival': NonNullNested(location_context_type),
}

multi_arrivals_type = {
    'Departure': NonNullNested(location_context_type),
    'Arrival': fields.List(NonNullNested(location_context_type)),
}

itinerary_request_type = {
    'id': fields.String,
    'multiDepartures': NonNullNested(multi_departures_type),
    'multiArrivals': NonNullNested(multi_arrivals_type),
    'DepartureTime': _DateTime,
    'ArrivalTime': _DateTime,
    'Algorithm': fields.String,
    'modes': fields.List(fields.String),
    'selfDriveConditions': fields.List(NonNullNested(self_drive_condition_type)),
    # 'selfDriveConditions' : fields.List(NonNullNested(self_drive_condition_type)),
    'AccessibilityConstraint': fields.Boolean,
    'Language': fields.String,
}

summed_up_itineraries_request_type = {
    'id': fields.String,
    'departures': fields.List(NonNullNested(location_context_type)),
    'arrivals': fields.List(NonNullNested(location_context_type)),
    'DepartureTime': _DateTime,
    'ArrivalTime': _DateTime,
    'Algorithm': fields.String,
    'modes': fields.List(fields.String),
    'selfDriveConditions': fields.List(NonNullNested(self_drive_condition_type)),
    'AccessibilityConstraint': fields.Boolean,
    'Language': fields.String,
    'options': fields.List(fields.String),
}

location_point_type = {
    'PlaceTypeId': fields.String,
    'Position': NonNullNested(location_structure_type),
}

place_type = {
    'id': fields.String,
    'Position': NonNullNested(location_structure_type),
    'Name': fields.String,
    'CityCode': fields.String,
    'CityName': fields.String,
    'TypeOfPlaceRef': fields.String,
}

trip_stop_place_type = place_type.copy()
# Parent attribute is currently not implemented and is therefore
# always empty, so ignore it for now.
# trip_stop_place_type['Parent'] = NonNullNested(place_type)

end_point_type = {
    'TripStopPlace': NonNullNested(trip_stop_place_type),
    'DateTime': _DateTime
}

provider_type = {
    'Name': fields.String,
    'Url': fields.String,
}

plan_trip_existence_notification_response_type = {
    'RequestId': fields.String,
    'ComposedTripId': fields.String,
    'DepartureTime': _DateTime,
    'ArrivalTime': _DateTime,
    'Duration': _Duration,
    'Departure': NonNullNested(location_point_type),
    'Arrival': NonNullNested(location_point_type),
    'providers': fields.List(NonNullNested(provider_type)),
}

step_end_point_type = {
    'TripStopPlace': NonNullNested(trip_stop_place_type),
    'DateTime': _DateTime,
    'PassThrough': fields.Boolean
}

step_type = {
    'id': fields.String,
    'Departure': NonNullNested(step_end_point_type),
    'Arrival': NonNullNested(step_end_point_type),
    'Duration': _Duration
}

pt_network_type = {
    'id': fields.String,
    'Name': fields.String,
    'RegistrationNumber': fields.String,
}

line_type = {
    'id': fields.String,
    'Name': fields.String,
    'Number': fields.String,
    'PublishedName': fields.String,
    'RegistrationNumber': fields.String,
}

pt_ride_type = {
    'PublicTransportMode': fields.String,
    'Departure': NonNullNested(end_point_type),
    'Arrival': NonNullNested(end_point_type),
    'Duration': _Duration,
    'Distance': fields.Integer,
    'PTNetwork': NonNullNested(pt_network_type),
    'Line': NonNullNested(line_type),
    'StopHeadSign': fields.String,
    'steps': fields.List(NonNullNested(step_type))
}

leg_type = {
    'SelfDriveMode': fields.String,
    'Departure': NonNullNested(end_point_type),
    'Arrival': NonNullNested(end_point_type),
    'Duration': _Duration
}

section_type = {
    'PartialTripId': fields.String,
    'PTRide': NonNullNested(pt_ride_type),
    'Leg': NonNullNested(leg_type)
}

trip_type = {
    'id': fields.String,
    'Departure': NonNullNested(end_point_type),
    'Arrival': NonNullNested(end_point_type),
    'Duration': _Duration,
    'Distance': fields.Integer,
    'InterchangeNumber': fields.Integer,
    'sections': fields.List(NonNullNested(section_type))
}

partial_trip_type = {
    'id': fields.String,
    'Provider': NonNullNested(provider_type),
    'Distance': fields.Integer,
    'Departure': NonNullNested(end_point_type),
    'Arrival': NonNullNested(end_point_type),
    'Duration': _Duration,
}

composed_trip_type = {
    'id': fields.String,
    'Departure': NonNullNested(end_point_type),
    'Arrival': NonNullNested(end_point_type),
    'Duration': _Duration,
    'Distance': fields.Integer,
    'InterchangeNumber': fields.Integer,
    'sections': fields.List(NonNullNested(section_type)),
    'partialTrips': fields.List(NonNullNested(partial_trip_type)),
}

plan_trip_notification_response_type = {
    'RequestId': fields.String,
    'RuntimeDuration': _Duration,
    'ComposedTrip': NonNullNested(composed_trip_type),
}

plan_trip_cancellation_response_type = {
    'RequestId': fields.String,
}

plan_trip_cancellation_request_type = {
    'RequestId': fields.String,
}

status_type = {
    'Code': fields.String,
    'RuntimeDuration': _Duration
}

itinerary_response_type = {
    'RequestId': fields.String,
    'Status': NonNullNested(status_type),
    'DetailedTrip': NonNullNested(trip_type)
}

summed_up_trip_type = {
    'Departure': NonNullNested(end_point_type),
    'Arrival': NonNullNested(end_point_type),
    'InterchangeCount': fields.Integer,
    'InterchangeDuration': fields.Integer
}

summed_up_itineraries_response_type = {
    'RequestId': fields.String,
    'Status': NonNullNested(status_type),
    'summedUpTrips': fields.List(NonNullNested(summed_up_trip_type))
}

plan_trip_request_type = {
    'clientRequestId': fields.String,
    'Departure': NonNullNested(location_context_type),
    'Arrival': NonNullNested(location_context_type),
    'DepartureTime': _DateTime,
    'ArrivalTime': _DateTime,
    'MaxTrips': fields.Integer,
    'Algorithm': fields.String,
    'modes': fields.List(fields.String),
    'selfDriveConditions': fields.List(NonNullNested(self_drive_condition_type)),
    'AccessibilityConstraint': fields.Boolean,
    'Language': fields.String,
}

error_type = {
    'Field': fields.String,
    'Message': fields.String,
}

plan_trip_response_type = {
    'clientRequestId': fields.String,
    'Status': fields.String,
    'errors': fields.List(NonNullNested(error_type)),
}

ending_search_type = {
    'RequestId': fields.String,
    'Status': fields.String,
    'MaxComposedTripSearched': fields.Integer,
    'ExistenceNotificationsSent': fields.Integer,
    'NotificationsSent': fields.Integer,
    'Runtime': _Duration,
}

starting_search_type = {
    'RequestId': fields.String,
    'Status': fields.String,
    'MaxComposedTripSearched': fields.Integer,
}

centroid_type = {
    'Location': NonNullNested(location_structure_type)
}

quay_type = {
    'id': fields.String,
    'Name': fields.String,
    'PrivateCode': fields.String,
    'Centroid': NonNullNested(centroid_type)
}

stop_place_type = {
    'id': fields.String,
    'quays': fields.List(NonNullNested(quay_type))
}

site_frame_type = {
    'stopPlaces': fields.List(NonNullNested(stop_place_type)),
}

frames_type = {
    'SiteFrame': NonNullNested(site_frame_type)
}

composite_frame_type = {
    'frames': NonNullNested(frames_type)
}

data_objects_type = {
    'CompositeFrame': NonNullNested(composite_frame_type)
}

publication_delivery_type = {
    'dataObjects': NonNullNested(data_objects_type)
}

stops_response_type = {
    'Status': NonNullNested(status_type),
    'PublicationDelivery': NonNullNested(publication_delivery_type)
}

capabilities_response_type = {
    'Status': NonNullNested(status_type),
    'MultipleStartsAndArrivals': fields.Integer,
    'GeographicPositionCompliant': fields.Boolean,
    'publicTransportModes': fields.String,
}
