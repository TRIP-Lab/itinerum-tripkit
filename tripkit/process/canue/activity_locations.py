#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import math
import networkx

from tripkit.models import ActivityLocation as TripkitActivityLocation
from .utils import geo

CENTROID_OVERLAP_M = 150


def detect_overlaps(centroids):
    G = networkx.Graph()
    connected = set()
    for ce1 in centroids:
        for ce2 in centroids:
            if ce1 == ce2:
                continue
            edge = (ce1, ce2)
            if geo.calculate_distance_m(*edge) <= CENTROID_OVERLAP_M:
                G.add_edge(*edge)
                connected.update(edge)
    unconnected = set(centroids) - connected

    condensed = [geo.create_centroid(cc) for cc in networkx.connected_components(G)]
    for ce in unconnected:
        condensed.append(ce)
    return condensed


def _intersects(point, iterpoints, dist_m=50):
    for test_point in iterpoints:
        if geo.calculate_distance_m(point, test_point) <= 50:
            return test_point


def wrap_for_tripkit(locations):
    tripkit_locations = []

    for label, centroid in locations.items():
        tripkit_locations.append(TripkitActivityLocation(
            label=label,
            latitude=centroid.lat,
            longitude=centroid.lon,
            easting=centroid.easting,
            northing=centroid.northing,
            zone_num=centroid.zone_num,
            zone_letter=centroid.zone_letter
        ))
    return tripkit_locations



def run(kmeans_groups, stdev_groups):
    kmeans_centroids = []
    for idx in kmeans_groups['stops']:
        stop_cluster = kmeans_groups['clusters'][idx]
        kmeans_centroids.append(geo.create_centroid(stop_cluster))
    kmeans_centroids = detect_overlaps(kmeans_centroids)

    stdev_centroids = []
    for stop_cluster in stdev_groups:
        centroid = geo.create_centroid(stop_cluster)
        stdev_centroids.append(centroid)
    stdev_centroids = detect_overlaps(stdev_centroids)
    
    # check which kmeans centroids exist within 50-100m intersection of stdev centroids,
    # these will be stop locations with relatively good confidence. The centroid coordinate
    # of the stdev cluster is more precise so these will be used for the position of overlapping
    # possible stop locations
    locations = {}
    idx = 0
    for kmeans_ce in kmeans_centroids:
        match = _intersects(kmeans_ce, stdev_centroids)
        if match:
            idx += 1
            label = f'location_{idx}'
            locations[label] = match
    tripkit_locations = wrap_for_tripkit(locations)
    return tripkit_locations
