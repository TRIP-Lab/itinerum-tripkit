#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import math
import logging
import numpy as np
import os
import utm
import warnings

from tripkit.utils.misc import LazyLoader
scipy = LazyLoader('scipy', globals(), 'scipy')
hdbscan = LazyLoader('hdbscan', globals(), 'hdbscan')

logger = logging.getLogger('itinerum-tripkit.process.clustering.hdbscan_ts')


def distance_m(point1, point2):
    '''
    Returns the distance between two points in meters.
    '''
    a = point2[0] - point1[0]
    b = point2[1] - point1[1]
    return math.sqrt(a ** 2 + b ** 2)


def remove_labels_with_uncertainty(probabilities, labels):
    '''
    Iterate through the probabilities matrix and reset to noise any
    cluster label probabilities that are not 1.
    '''
    for idx, p in enumerate(probabilities):
        if p < 1.0:
            labels[idx] = -1
    return labels


# get the initial cluster label for comparison, does not necessarily
# start with 0
def _first_label(labels):
    for label in labels:
        if label != -1:
            return label


def relabel_clusters_by_timeseries(labels):
    '''
    Iterate over clusters in timeseries order and re-label if there is a break of >4 points between cluster
    (a duration of ~30 seconds) or whenever the cluster changes.
    '''
    last_label = _first_label(labels)
    new_label = 0
    incrementing_labels = []
    unlabeled_streak = 0
    for label in labels:
        if label != -1:
            if label != last_label:
                last_label = label
                new_label += 1
            elif unlabeled_streak == 4:
                unlabeled_streak = 0
                new_label += 1
            incrementing_labels.append(new_label)
        else:
            unlabeled_streak += 1
            incrementing_labels.append(-1)
    return incrementing_labels


def create_coordinate_clusters(coordinates, cluster_labels):
    '''
    Create cluster arrays of the input coordinate data from cluster labels.
    '''
    clusters = []
    last_label, cluster = None, None
    for idx, label in enumerate(cluster_labels):
        is_new_cluster = label != -1 and last_label != label
        if is_new_cluster:
            if cluster:
                clusters.append(cluster)
            cluster = []
            last_label = label
        if label != -1:
            cluster.append(coordinates[idx])
    return clusters


def check_min_stop_time(clusters, min_s):
    '''
    Filter to keep only clusters that have meet the minimum stop time criteria.
    '''
    stop_clusters = []
    for cluster in clusters:
        period_s = cluster[-1].timestamp_epoch - cluster[0].timestamp_epoch
        if period_s >= min_s:
            stop_clusters.append(cluster)
    return stop_clusters


def clusters_center_of_gravity(clusters):
    '''
    Get a centroid-like attribute where center is calculated by giving higher weights
    to points with closer neighbors.
    '''
    centers = []
    for cluster in clusters:
        c_points = np.asarray([(c.easting, c.northing) for c in cluster])
        # euclidean distance betweens all points with each other point
        m = scipy.spatial.distance_matrix(c_points, c_points)
        # give any points that share a location an impossibly large distance so they are not selected as weights
        m[m == 0] = 1e16
        # get the closest distance for each point
        closest_points = m.min(axis=0)
        i_closest_points = 1 / closest_points
        avg = np.average(c_points, weights=i_closest_points, axis=0)
        centers.append(avg)
    return centers


def run(min_stop_time_s, coordinates):
    logger.info("Running hdbscan clustering on user points for additional stop locations...")

    # create meter x, y coordinates for euclidean distance calculations
    count = len(coordinates)
    if count <= 10:
        return {}

    points = np.empty([count, 2])
    utm_zone_number, utm_zone_letter = None, None
    for idx, c in enumerate(coordinates):
        easting, northing, utm_zone_number, utm_zone_letter = utm.from_latlon(c.latitude, c.longitude)
        points[idx] = [easting, northing]
        c.easting, c.northing = easting, northing

    jobs = -1
    if os.name == 'nt':
        logger.info("Reduce cluster jobs on Windows to avoid broken multiprocessing pool")
        jobs = 1
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=15, min_samples=20, metric='euclidean', allow_single_cluster=True, core_dist_n_jobs=jobs
    )
    base_labels = clusterer.fit_predict(points)
    raw_labels = remove_labels_with_uncertainty(clusterer.probabilities_, base_labels)
    cluster_labels = relabel_clusters_by_timeseries(raw_labels)
    coordinate_clusters = create_coordinate_clusters(coordinates, cluster_labels)
    stop_location_clusters = check_min_stop_time(coordinate_clusters, min_stop_time_s)
    weighted_centers_utm = clusters_center_of_gravity(stop_location_clusters)

    # return lat/lon centers with named cluster labels
    semantic_locations = {}
    for idx, wc in enumerate(weighted_centers_utm):
        name = f'cluster{idx}'
        easting, northing = wc
        semantic_locations[name] = utm.to_latlon(easting, northing, utm_zone_number, utm_zone_letter)
    return semantic_locations
