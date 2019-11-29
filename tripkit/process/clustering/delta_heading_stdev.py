#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import numpy as np

from .models import ClusterInfo


def group_by_stdev(coordinates, cutoff=1):
    avg_delta_headings = [c.avg_delta_heading for c in coordinates if c.avg_delta_heading]
    min_bounds, max_bounds = min(avg_delta_headings), max(avg_delta_headings)
    offset = round((max_bounds - min_bounds) / 2)
    threshold = np.std(avg_delta_headings) * cutoff + offset

    stdev_groups, group = [], []
    for c in coordinates:
        if not c.avg_delta_heading:
            c.stdev = ClusterInfo()
            continue

        if c.avg_delta_heading >= threshold:
            num = len(stdev_groups) + 1
            c.stdev = ClusterInfo(group_num=num, label='stop')
            group.append(c)
        else:
            c.stdev = ClusterInfo(label='trip')

        if group and c.avg_delta_heading < threshold:
            stdev_groups.append(group)
            group = []
    return stdev_groups


def run(coordinates, stdev_cutoff=1):
    avg_delta_heading_stdev_groups = group_by_stdev(coordinates, cutoff=stdev_cutoff)
    return avg_delta_heading_stdev_groups
