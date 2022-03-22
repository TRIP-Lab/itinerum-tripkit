#!/usr/bin/env python
# Kyle Fitzsimmons, 2022
#
# Truncates trips to the centroids of the start and destinations if known. This
# is to help mitigate the tangles that tail the ends of trips.
from audioop import reverse
import logging
import pytz
from tripkit.models.Trip import Trip

from tripkit.process.activities.canue.tally_times import label_trip_points
from tripkit.utils import geo


def run(user, locations, proximity_m=50):
    """
    Truncates trips to the centroids of the start and destinations if known. This
    is to help mitigate the tangles that tail the ends of trips.

    :param trips: A list of py:class:`tripkit.models.Trip` objects.
    :param locations: A list of py:class:`tripkit.models.ActivityLocation` objects.

    :type trips: list
    :type locations: list
    """
    truncated_trips = []
    for t in user.trips:
        label_trip_points(locations, t, proximity_m)

        start_location = None
        for p in t.points:
            if p.label:
                start_location = p.label
                break

        end_location = None
        for p in reversed(t.points):
            if p.label:
                end_location = p.label
                break

        if start_location and end_location:
            start_idx = 0
            for idx, p in enumerate(reversed(t.points)):
                if p.label == start_location:
                    start_idx = len(t.points) - idx
                    break

            end_idx = 0
            for idx, p in enumerate(t.points):
                if p.label == end_location:
                    end_idx = idx
                    break

            new_t = Trip(num=t.num, trip_code=t.trip_code)
            new_t.points = t.points[start_idx:end_idx]
            truncated_trips.append(new_t)
        else:
            truncated_trips.append(t)
    return truncated_trips
