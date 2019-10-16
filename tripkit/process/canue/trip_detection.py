#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from tripkit.models import Trip as LibraryTrip, TripPoint as LibraryTripPoint

from .utils import geo


def split_by_time_gap(coordinates, period_s=300):
    segments = []
    segment = []
    last_c = None
    for c in coordinates:
        if not last_c:
            last_c = c
            continue
        assert c.timestamp_epoch > last_c.timestamp_epoch
        diff_s = c.timestamp_epoch - last_c.timestamp_epoch
        if diff_s > period_s:
            segments.append(segment)
            segment = []
        segment.append(c)
        last_c = c
    return segments


def split_by_stop_locations(time_segments, locations, period_s=300):
    print(len(time_segments))
    for segment in time_segments:
        print(len(segment))


def wrap_for_tripkit(segments):
    tripkit_trips = []

    for idx, segment in enumerate(segments, start=1):
        trip = LibraryTrip(num=idx, trip_code=0)
        trip_distance = 0.0
        for point in segment:
            trip_distance += point.distance_m
            p = LibraryTripPoint(
                database_id=None,
                latitude=point.latitude,
                longitude=point.longitude,
                h_accuracy=0.,
                distance_before=point.distance_m,
                trip_distance=trip_distance,
                period_before=point.duration_s,
                timestamp_UTC=point.timestamp_UTC,
            )
            trip.points.append(p)
        tripkit_trips.append(trip)
    return tripkit_trips


def run(coordinates, locations):
    segments = split_by_time_gap(coordinates, period_s=300)
    split_by_stop_locations(segments, locations, period_s=300)
    trips = wrap_for_tripkit(segments)
    return trips
