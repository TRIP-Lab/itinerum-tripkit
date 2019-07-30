#!/usr/bin/env python3
# Kyle Fitzsimmons, 2019
from datakit.models import Trip as DatakitTrip, TripPoint as DatakitTripPoint


def v1_wrap_for_datakit(detected_trips):
    """
    Return result as the same type of object (list of TripPoints) as returned
    by `itinerum-datakit/datakit/database.py`.
    """
    datakit_trips = []
    for trip_num, detected_trip in detected_trips.items():
        trip_codes = {pt['trip_code'] for pt in detected_trip}
        if len(trip_codes) > 1:
            raise Exception(f"Trip {trip_num}: trip_codes not internally consistent (expecting len(1)). ({trip_codes})")
        trip_code = list(trip_codes)[0]
        is_missing_trip = 100 <= trip_code < 200

        if not is_missing_trip:
            trip = DatakitTrip(num=trip_num,
                               trip_code=trip_code)
            for point in detected_trip:
                p = DatakitTripPoint(latitude=point['latitude'],
                                     longitude=point['longitude'],
                                     h_accuracy=point['h_accuracy'],
                                     timestamp_UTC=point['timestamp_UTC'],
                                     database_id=point['id'])
                trip.points.append(p)
            datakit_trips.append(trip)
        else:
            trip = DatakitTrip(num=trip_num, trip_code=trip_code)
            p1 = DatakitTripPoint(database_id=None,
                                  latitude=detected_trip[0]['latitude'],
                                  longitude=detected_trip[0]['longitude'],
                                  h_accuracy=-1.,
                                  timestamp_UTC=detected_trip[0]['timestamp_UTC'])
            p2 = DatakitTripPoint(database_id=None,
                                  latitude=detected_trip[-1]['latitude'],
                                  longitude=detected_trip[-1]['longitude'],
                                  h_accuracy=-1.,
                                  timestamp_UTC=detected_trip[-1]['timestamp_UTC'])
            trip.points = [p1, p2]
            datakit_trips.append(trip)
    return datakit_trips
