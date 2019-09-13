#!/usr/bin/env python
# Kyle Fitzsimmons, 2015
'''Labels points and trips based upon their merging characteristics'''


def metro(segments, keys):
    key1, key2 = keys
    segment1 = segments[key1]
    segment2 = segments[key2]
    segment1[-1]['merge_codes'].append('metro')
    segment2[0]['merge_codes'].append('metro')
    return segments


def velocity(trip1, trip2):
    trip1[-1]['merge_codes'].append('velocity')
    trip2[0]['merge_codes'].append('velocity')


def single_point(point, trip, merge_type):
    if merge_type == 'insert':
        point['merge_codes'].append('single point - before')
        trip[0]['merge_codes'].append('single point - before')
    elif merge_type == 'append':
        point['merge_codes'].append('single point - after')
        trip[-1]['merge_codes'].append('single point - after')
