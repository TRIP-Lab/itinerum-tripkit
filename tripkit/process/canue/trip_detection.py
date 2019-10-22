#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from tripkit.models import Trip as LibraryTrip, TripPoint as LibraryTripPoint

from .utils import geo


def _nearest_location(c, locations, buffer_m=100):
    for location in locations:
        if geo.calculate_distance_m(c, location) <= buffer_m:
            return location.label


def _common_centroid(stop_points, locations):
    split_stop_label = {sp.stop_label for sp in stop_points}
    assert len(split_stop_label) == 1
    split_stop_label = list(split_stop_label)[0]
    for location in locations:
        if location.label == split_stop_label:
            return location


def _truncate_trace(coordinates, location, reverse=False):
    last_c = None
    last_dist_m = 10E16
    truncate_idx = None
    if reverse:
        coordinates = list(reversed(coordinates))
    for idx, c in enumerate(coordinates):
        if not last_c and location and geo.calculate_distance_m(c, location) > 200:
            continue
        if not last_c:
            last_c = c
            continue
        dist_m = geo.calculate_distance_m(last_c, c)
        if dist_m < last_dist_m:
            last_dist_m = dist_m
        else:
            truncate_idx = idx
            break
    truncated = coordinates[:truncate_idx]
    if reverse:
        return list(reversed(truncated))
    return truncated


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


# determines which points labeled as stop points constitute a valid end of a trip
# and return points to append to the existing split segment
def _append_to_split(last_point, stop_points, stop_centroid, period_s):
    half = round(len(stop_points) / 2)
    append_candidates = _truncate_trace(stop_points[:half], stop_centroid)
    append_points = []
    for ap in append_candidates:
        if ap.timestamp_epoch - last_point.timestamp_epoch <= period_s:
            append_points.append(ap)
    return append_points


# determines which points labeled as stop points constitute a valid beginning of a trip
# and return points to prepend to a new split segment
def _prepend_to_split(current_point, stop_points, stop_centroid, period_s):
    half = round(len(stop_points) / 2)
    prepend_candidates = _truncate_trace(stop_points[half:], stop_centroid, reverse=True)
    prepend_points = []
    for pp in prepend_candidates:
        if current_point.timestamp_epoch - pp.timestamp_epoch <= period_s:
            prepend_points.append(pp)
    return prepend_points


# Temporarily collect coordinates continuously within test range (60m) of a stop. When a coordinate beyond
# range of stop is re-detected, test the temporary list if the entrance and exit points are greater than a
# minimum stop time--if so, filter the points and split segment into two. Otherwise, the trip is considered
# just passing by a stop and no action is taken (temporarily collected points are re-joined to existing split
# as normal).
def split_by_stop_locations(segments, locations, period_s=300):
    split_segments = []
    for segment in segments:
        splits = [ [] ]
        stop_points = []
        for c in segment:
            stop_label = _nearest_location(c, locations, buffer_m=60)
            # stop location is detected--point is added to stop points
            if stop_label:
                c.stop_label = stop_label
                stop_points.append(c)
            # stop location not detected, stop points exist from previous iterations--
            #   1. If no points exist in the current split, traverse stop points in reverse time order to find
            #      the start location and the last "closest point" to the stop. In this context, that is the point
            #      that measures closest to the location before the distance increases again.
            #   2. Check whether the time difference between points entering and exiting the stop location constitute
            #      a stop with the device running. If this condition is met, disregard the stop points and create a
            #      new segment split.
            elif stop_points:
                diff_s = stop_points[-1].timestamp_epoch - stop_points[0].timestamp_epoch
                if diff_s >= period_s:
                    stop_centroid = _common_centroid(stop_points, locations)

                    # append to current split the stop points tracked to the stop location centroid until reached
                    current_segment = splits[-1]
                    if current_segment:
                        last_point = current_segment[-1]
                        append_points = _append_to_split(last_point, stop_points, stop_centroid, period_s)
                        splits[-1].extend(append_points)

                    # prepend to new split the stop points backtracked to the stop location centroid until reached
                    prepend_points = _prepend_to_split(c, stop_points, stop_centroid, period_s)
                    next_split = prepend_points + [c]
                    splits.append(next_split)
                else:
                    splits[-1].extend(stop_points)
                stop_points = []
            # stop location not detected, no stop points exist
            else:
                splits[-1].append(c)
        # leftover stop points at the end of segments are considered valid
        if stop_points:
            is_last_segment = segment == segments[-1]
            if not is_last_segment:
                splits[-1].extend(stop_points)
                stop_points = []
            else:
                stop_centroid = _common_centroid(stop_points, locations)
                current_segment = splits[-1]
                if current_segment:
                    last_point = current_segment[-1]                
                    append_points = _append_to_split(last_point, stop_points, stop_centroid, period_s)
                    splits[-1].extend(append_points)                
        split_segments.extend(splits)
    return split_segments


def filter_too_short_segments(segments):
    for segment in segments:
        if not segment:
            continue
        centroid = geo.create_centroid(segment)
        
        segment_is_valid = False
        for c in segment:
            if geo.calculate_distance_m(c, centroid) > 200:
                segment_is_valid = True
                break
        
        if segment_is_valid:
            yield segment


def gert_rules(segments):
    # GERT author's note:
    #   Some background on threshold values:
    #   based on 3 feet per second (fps) minimum pedestrian walking speed (LaPlante & Kaeser 2007)
    #   or 0.91 m/s and a minimum walk duration of 60 s (Bialostozky 2009)
    #   see also MUTCD 2009 Section 4E.06 Pedestrian Intervals and Signal Phases
    last_segment = None
    for segment in segments:
        if not last_segment:
            last_segment = segment
            continue
        last_point = last_segment[-1]
        next_point = segment[0]

        time_gap_s = next_point.timestamp_epoch - last_point.timestamp_epoch
        last_segment = segment
        

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
    time_segments = split_by_time_gap(coordinates, period_s=300)
    location_segments = split_by_stop_locations(time_segments, locations, period_s=300)
    
    # condensed_segments = condense_stop_points(location_segments, locations)
    filtered_segments = filter_too_short_segments(location_segments)
    # gert_rules(location_segments)
    
    trips = wrap_for_tripkit(filtered_segments)
    return trips
