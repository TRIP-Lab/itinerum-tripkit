#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from tripkit.models import Trip as LibraryTrip, TripPoint as LibraryTripPoint

from .utils import geo


def _nearest_location(c, locations, buffer_m=100):
    for stop_centroid in locations.values():
        if geo.calculate_distance_m(c, stop_centroid) <= buffer_m:
            return stop_centroid


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
    return segments


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
            stop_location = _nearest_location(c, locations, buffer_m=60)
            # stop location is detected--point is added to stop points
            if stop_location:
                stop_points.append(c)
            # stop location not detected, stop points exist from previous iterations--
            #   1. If no points exist in the current split, traverse stop points in reverse time order to find
            #      the start location and the last "closest point" to the stop. In this context, that is the point
            #      that measures closest to the location before the distance increases again.
            #   2. Check whether the time difference between points entering and exiting the stop location constitute
            #      a stop with the device running. If this condition is met, disregard the stop points and create a
            #      new segment split.
            elif stop_points:
                # if not splits[0]:
                #     last_stop_c = stop_points[-1]
                #     last_stop_location = _nearest_location(last_stop_c, locations, buffer_m=60)
                #     if last_stop_location:
                #         print(len(stop_points), len(_truncate_trace(stop_points, last_stop_location, reverse=True)))
                #         splits[-1].extend(_truncate_trace(stop_points, last_stop_location, reverse=True))
                #     else:
                #         splits[-1].extend(stop_points)
                # else:
                diff_s = stop_points[-1].timestamp_epoch - stop_points[0].timestamp_epoch
                print(diff_s)
                if diff_s >= period_s:
                    splits.append([c])
                else:
                    splits[-1].extend(stop_points)
                stop_points = []
            # stop location not detected, no stop points exist
            else:
                splits[-1].append(c)
        # leftover stop points at the end of segments are considered valid
        if stop_points:
            splits[-1].extend(stop_points)
            stop_points = []
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
