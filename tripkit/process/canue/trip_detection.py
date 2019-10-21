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
            elif stop_points:
                if not splits[0]:
                    # traverse stop points in reverse time order to find the start location and the last "closest point"
                    # to the stop. In this context, that is the point that measures closest to the location before
                    # the distance increases again
                    last_stop_c = stop_points[-1]
                    last_stop_location = _nearest_location(last_stop_c, locations, buffer_m=60)
                    if last_stop_location:
                        print(len(stop_points), len(_truncate_trace(stop_points, last_stop_location, reverse=True)))
                        splits[-1].extend(_truncate_trace(stop_points, last_stop_location, reverse=True))
                    else:
                        splits[-1].extend(stop_points)
                        # splits[-1].extend(stop_points[-3:])
                    # splits[-1].extend(stop_points)
                else:
                    diff_s = stop_points[-1].timestamp_epoch - stop_points[0].timestamp_epoch
                    if diff_s >= period_s:
                        splits.append([c])
                    else:
                        splits[-1].extend(stop_points)
                stop_points = []
            else:
                splits[-1].append(c)
        # leftover stop points at the end of segments are considered valid
        if stop_points:
            splits[-1].extend(stop_points)
        split_segments.extend(splits)
    return split_segments


# def condense_stop_points(segments, locations):
#     # starting halfway through a trip, check 
#     condensed_segments = []
#     for segment in segments:
#         # get stop locations closest to detected trip ends
#         start_location, end_location = None, None
#         len_tenth = round(len(segment) / 10)
#         for c in segment[:len_tenth]:
#             start_location = _nearest_location(c, locations, buffer_m=100)
#             if start_location:
#                 break
#         for c in reversed(segment[len_tenth:]):
#             end_location = _nearest_location(c, locations, buffer_m=100)
#             if end_location:
#                 break

#         first_chunk = segment[:len_tenth]
#         second_chunk = segment[len_tenth*-1:]
#         middle_chunk = segment[len_tenth:len_tenth*-1]
#         # the segment should be traversed backwards from the latest point of the first chunk,
#         # assumed to be a valid part of a trip's trajectory. Tangles are expected to occur at the
#         # end of a trip trace.
#         truncated_first_chunk = _truncate_trace(first_chunk, start_location, reverse=True)
#         truncated_second_chunk = _truncate_trace(second_chunk, end_location)
#         truncated_segment = truncated_first_chunk + middle_chunk + truncated_second_chunk
#         condensed_segments.append(truncated_segment)
#     return condensed_segments


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

        # first_c = segment[0]
        # last_c = segment[-1]

        # get segment centroid

        # check if all points are within 100m of centroid and remove if true
        

        # segment_distance_m = 0.
        # for c in segment:
        #     segment_distance_m += c.distance_m
        # segment_time_gap_s = last_c.timestamp_epoch - first_c.timestamp_epoch
        # print(f'segment {idx}: {segment_distance_m} m (in {segment_time_gap_s} s)')
        # segment_mps = segment_distance_m / segment_time_gap_s
        # print(f'avg velocity: {segment_mps:.2f} m/s | {segment_mps * 3.6:.2f} km/h')
        # direct_distance_m = geo.calculate_distance_m(last_c, first_c)
        # implied_mps = direct_distance_m / segment_time_gap_s
        # print(f'direct distance: {direct_distance_m:.2f} m | implied velocity {implied_mps:.2f} m/s')
        # print(f'start: {first_c.timestamp_UTC.isoformat()} -> end: {last_c.timestamp_UTC.isoformat()}')
        # print()

        # if idx == 0:
        #     import sys; sys.exit()


def gert_rules(segments):
    # Author's note:
    # Some background on threshold values:
    # based on 3 feet per second (fps) minimum pedestrian walking speed (LaPlante & Kaeser 2007)
    # or 0.91 m/s and a minimum walk duration of 60 s (Bialostozky 2009)
    # see also MUTCD 2009 Section 4E.06 Pedestrian Intervals and Signal Phases
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
