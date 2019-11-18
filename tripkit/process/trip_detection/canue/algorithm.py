#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from .location_split import split_by_stop_locations
from tripkit.models import Trip as LibraryTrip, TripPoint as LibraryTripPoint
from tripkit.utils import geo


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
    if segment:
        segments.append(segment)
    return segments


# def gert_rules(segments):
#     # GERT author's note:
#     #   Some background on threshold values:
#     #   based on 3 feet per second (fps) minimum pedestrian walking speed (LaPlante & Kaeser 2007)
#     #   or 0.91 m/s and a minimum walk duration of 60 s (Bialostozky 2009)
#     #   see also MUTCD 2009 Section 4E.06 Pedestrian Intervals and Signal Phases
#     last_segment = None
#     for segment in segments:
#         if not last_segment:
#             last_segment = segment
#             continue
#         last_point = last_segment[-1]
#         next_point = segment[0]
#         time_gap_s = next_point.timestamp_epoch - last_point.timestamp_epoch
#         last_segment = segment


def filter_too_short_segments(segments, min_distance_m=250):
    for segment in segments:
        if not segment:
            continue
        centroid = geo.centroid(segment)

        segment_is_valid = False
        for c in segment:
            if geo.distance_m(c, centroid) > min_distance_m:
                segment_is_valid = True
                break

        if segment_is_valid:
            yield segment


def detect_missing_segments(segments, missing_segment_m=250):
    ''' 
    Returns a list of missing segments consisting of the last valid segment end point
    and the next valid segment start point.
    '''
    missing_segments = []
    last_segment = None
    for segment in segments:
        if not last_segment:
            last_segment = segment
            continue
        segments_gap = geo.distance_m(last_segment[-1], segment[0])
        if segments_gap > missing_segment_m:
            missing_segments.append([last_segment[-1], segment[0]])
        last_segment = segment
    return missing_segments


def make_trips_diary(valid_segments, missing_segments):
    '''
    Zips together lists of valid segments and missing segments in timestamp order
    into continuous trip diary.
    '''
    if not missing_segments:
        return valid_segments

    trips = []
    missing_iter = iter(missing_segments)
    missing_test_segment = next(missing_iter)
    trip_idx = 0
    missing_idxs = []
    for valid_segment in valid_segments:
        # occurs when `next(missing_iter, None)` returns None: append remaining valid segments as normal
        if not missing_test_segment:
            trips.append(valid_segment)
            trip_idx += 1
        # append existing valid segments when they occur before a missing segment
        elif missing_test_segment and valid_segment[0].timestamp_UTC < missing_test_segment[0].timestamp_UTC:
            trips.append(valid_segment)
            trip_idx += 1
        # append the last available "missing segment" before a valid segment and continue
        else:
            trips.append(missing_test_segment)
            missing_idxs.append(trip_idx)
            trip_idx += 1

            trips.append(valid_segment)
            trip_idx += 1

            missing_test_segment = next(missing_iter, None)
    diary = {'trips': trips, 'missing': missing_idxs}
    return diary


def wrap_for_tripkit(diary):
    tripkit_trips = []

    for idx, detected_trip in enumerate(diary['trips']):
        trip_num = idx + 1
        if idx in diary['missing']:
            trip = LibraryTrip(num=trip_num, trip_code=101)
            start, end = detected_trip
            p1 = LibraryTripPoint(
                database_id=None,
                latitude=start.latitude,
                longitude=start.longitude,
                h_accuracy=0.0,
                distance_before=0.0,
                trip_distance=0.0,
                period_before=0,
                timestamp_UTC=start.timestamp_UTC,
            )
            trip.points.append(p1)
            p2 = LibraryTripPoint(
                database_id=None,
                latitude=end.latitude,
                longitude=end.longitude,
                h_accuracy=0.0,
                distance_before=geo.distance_m(*detected_trip),
                trip_distance=geo.distance_m(*detected_trip),
                period_before=geo.duration_s(start, end),
                timestamp_UTC=end.timestamp_UTC,
            )
            trip.points.append(p2)
        else:
            trip = LibraryTrip(num=trip_num, trip_code=1)
            trip_distance = 0.0
            for point in detected_trip:
                p = LibraryTripPoint(
                    database_id=None,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    h_accuracy=0.0,
                    distance_before=point.distance_m,
                    trip_distance=trip_distance,
                    period_before=point.duration_s,
                    timestamp_UTC=point.timestamp_UTC,
                )
                trip.points.append(p)
                trip_distance += point.distance_m
        tripkit_trips.append(trip)
    return tripkit_trips


def run(cfg, coordinates, locations):
    time_segments = split_by_time_gap(coordinates, period_s=cfg.TRIP_DETECTION_BREAK_INTERVAL_SECONDS)
    location_segments = split_by_stop_locations(
        time_segments, locations, period_s=cfg.TRIP_DETECTION_BREAK_INTERVAL_SECONDS
    )
    # gert_rules(location_segments)

    valid_segments = list(filter_too_short_segments(location_segments, min_distance_m=250))
    missing_segments = detect_missing_segments(valid_segments, missing_segment_m=250)
    trips_diary = make_trips_diary(valid_segments, missing_segments)
    return wrap_for_tripkit(trips_diary)
