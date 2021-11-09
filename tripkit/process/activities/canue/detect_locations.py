#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import math
import networkx
from tripkit import utils

from tripkit.models import ActivityLocation as TripkitActivityLocation
from tripkit.utils import geo

CENTROID_OVERLAP_M = 150


def condense_overlaps(centroids):
    G = networkx.Graph()
    connected = set()
    for ce1 in centroids:
        for ce2 in centroids:
            if ce1 == ce2:
                continue
            if geo.distance_m(ce1, ce2) <= CENTROID_OVERLAP_M:
                G.add_edge(ce1, ce2)
                connected.update((ce1, ce2))
    unconnected = set(centroids) - connected

    condensed = [geo.centroid(cc) for cc in networkx.connected_components(G)]
    for ce in unconnected:
        condensed.append(ce)
    return condensed


def _intersects(point, iterpoints, dist_m=50):
    for test_point in iterpoints:
        if geo.distance_m(point, test_point) <= dist_m:
            return test_point


def merge_known_locations(locations, known_locations, dist_m=1000):
    merged = {}
    for label, loc in locations.items():
        matched_known_location = _intersects(loc, known_locations, dist_m)
        if matched_known_location:
            merged[matched_known_location.label] = matched_known_location
        else:
            merged[label] = loc
    
    # add remaining non-matched known locations
    for loc in known_locations:
        if loc.label not in merged:
            merged[loc.label] = loc
    return merged


def wrap_for_tripkit(locations):
    tripkit_locations = []

    for label, centroid in locations.items():
        tripkit_locations.append(
            TripkitActivityLocation(
                label=label,
                latitude=centroid.latitude,
                longitude=centroid.longitude,
                easting=centroid.easting,
                northing=centroid.northing,
                zone_num=centroid.zone_num,
                zone_letter=centroid.zone_letter,
            )
        )
    return tripkit_locations


def run(kmeans_groups, stdev_groups, known_locations=None):
    kmeans_centroids = []
    for idx in kmeans_groups['stops']:
        stop_cluster = kmeans_groups['clusters'][idx]
        kmeans_centroids.append(geo.centroid(stop_cluster))
    kmeans_centroids = condense_overlaps(kmeans_centroids)

    stdev_centroids = [geo.centroid(stop_cluster) for stop_cluster in stdev_groups]
    stdev_centroids = condense_overlaps(stdev_centroids)

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

    # include known locations within detected clusters if available
    if known_locations:
        known_locations = utils.qstarz.create_activity_locations(known_locations)
        locations = merge_known_locations(locations, known_locations, dist_m=400)
    tripkit_locations = wrap_for_tripkit(locations)
    return tripkit_locations
