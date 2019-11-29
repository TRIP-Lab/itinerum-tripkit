#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
#
# Using the scikit-learn K-Means requires a large (6GB) download of the
# Visual Studio w/ C++ compiler, so the purpose of this implementation is
# to avoid requiring scikit-learn to use the itinerum-tripkit library.
import numpy as np

from .algorithm import KMeansPlusPlus, KMeans
from .models import ClusterInfo


MAX_AVG_DISTANCE = 50
MIN_STOP_TIME = 120


def format_kmeans_values(coordinates):
    values = []
    for c in coordinates:
        dist = c.avg_distance_m if c.avg_distance_m else 0
        dist = dist if dist < MAX_AVG_DISTANCE else MAX_AVG_DISTANCE
        values.append(np.array([dist]))
    return values


def label_coordinate_clusters(coordinates, kmeans):
    center1, center2 = kmeans.centroids
    if center1.point.coordinates > center2.point.coordinates:
        labels = ['trip', 'stop']
    else:
        labels = ['stop', 'trip']
    for idx, point in enumerate(kmeans.points):
        coordinates[idx].kmeans = ClusterInfo(label=labels[point.centroid])      


# group clusters sequentially by their occurance in the user's travel diary
def group_sequentially(coordinates):
    last_label = None
    group_num = -1
    cluster_groups = {}
    stop_groups = set()
    for c in coordinates:
        if last_label != c.kmeans.label:
            group_num += 1
            c.kmeans.group_num = group_num
            last_label = c.kmeans.label
        cluster_groups.setdefault(group_num, []).append(c)
        if c.kmeans.label == 'stop':
            stop_groups.add(group_num)
    return cluster_groups, stop_groups


# check if stop cluster meets minimum stop threshold
def relabel_by_stop_time(cluster_groups, stop_groups, min_time):
    converted = set()
    for group_num in stop_groups:
        start_c = cluster_groups[group_num][0]
        end_c = cluster_groups[group_num][-1]
        if end_c.timestamp_epoch - start_c.timestamp_epoch < min_time:
            for c in cluster_groups[group_num]:
                c.kmeans.label = 'trip'
            converted.add(group_num)
    stop_groups = stop_groups - converted
    return cluster_groups, stop_groups


def run(coordinates):
    cluster_values = format_kmeans_values(coordinates)
    kpp = KMeansPlusPlus(cluster_values, n_clusters=2)

    km = KMeans(cluster_values, seed_centroids=kpp.centroids).fit()
    label_coordinate_clusters(coordinates, km)
    cluster_groups, stop_groups = group_sequentially(coordinates)
    cluster_groups, stop_groups = relabel_by_stop_time(cluster_groups, stop_groups, min_time=MIN_STOP_TIME)

    groups = {'clusters': cluster_groups, 'stops': stop_groups}
    return groups
