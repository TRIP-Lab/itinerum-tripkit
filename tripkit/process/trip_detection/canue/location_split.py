#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
#
# Splits segments when entry/exit from detected stop locations is longer than a minimum
# trip duration. This is due to QStarz data collection happening continually without
# interruption at geofences.
import logging

from tripkit.utils import geo

logger = logging.getLogger('itinerum-tripkit.process.trip_detection.canue.location_split')


def _nearest_location(c, locations, buffer_m=100):
    for location in locations:
        if geo.distance_m(c, location) <= buffer_m:
            return location.label


def _common_centroid(stop_points, locations):
    split_stop_label = {sp.stop_label for sp in stop_points}
    if len(split_stop_label) != 1:
        labels = {}
        for sp in stop_points:
            labels.setdefault(sp.stop_label, 0)
            labels[sp.stop_label] += 1
        popular = (None, -1)
        for label, count in labels.items():
            if count > popular[1]:
                popular = (label, count)
        logger.warn(
            f"stop has multiple labels: {split_stop_label}, choosing most popular: {popular}"
        )
        split_stop_label = popular[0]
    else:
        split_stop_label = list(split_stop_label)[0]
    for location in locations:
        if location.label == split_stop_label:
            return location


def _truncate_trace(coordinates, location, reverse=False):
    last_c = None
    last_dist_m = 10e16
    truncate_idx = None
    if reverse:
        coordinates = list(reversed(coordinates))
    for idx, c in enumerate(coordinates):
        if not last_c:
            # only truncate within 200m of stop location
            skip_c = location and geo.distance_m(c, location) > 200
            if not skip_c:
                last_c = c
            continue
        dist_m = geo.distance_m(last_c, c)
        if dist_m < last_dist_m:
            last_dist_m = dist_m
        else:
            truncate_idx = idx
            break
    truncated = coordinates[:truncate_idx]
    if reverse:
        return list(reversed(truncated))
    return truncated


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
        splits = [[]]
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
