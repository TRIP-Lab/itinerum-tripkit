#!/usr/bin/env python

# Based upon GERT 1.2 (2016-06-03): GIS-based Episode Reconstruction Toolkit
# Ported to itinerum-datakit by Kyle Fitzsimmons, 2019

# NOTE: placeholder, possibly unneeded


def detect_stop_by_attributes(coordinates):
    next_coordinates = iter(coordinates)
    next(next_coordinates)  # advance one ahead of test coordinate (c)

    last_c = None
    for c in coordinates:
        next_c = next(next_coordinates)
        if not last_c:
            last_c = c
            continue
        print(dir(c))
        import sys; sys.exit()

def run(coordinates):
    if len(coordinates) < 3:
        return []

    stops = detect_stop_by_attributes(coordinates)
