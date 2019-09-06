#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
#
# DBSCAN clustering reference implementation to detect stops when testing for gaps in distance and
# timestamps between points does not catch them
# https://github.com/chrisjmccormick/dbscan/blob/master/dbscan.py
from geopy.distance import distance


EPS = 20  # threshold distance, meters
MIN_PTS = 10  # minimum number of points to consider as a cluster


def region_query(points, p_idx):
    # find all points within points that occur within distance `EPS` of the current point
    p = points[p_idx]
    neighbor_idxs = []
    for n_idx, n in enumerate(points):
        if distance((p.latitude, p.longitude), (n.latitude, n.longitude)).meters < EPS:
            neighbor_idxs.append(n_idx)
    return neighbor_idxs


def grow_cluster(points, labels, p_idx, neighbor_idxs, cluster_id):
    # assign the cluster label to the seed point
    labels[p_idx] = cluster_id

    # look at each neighbor of the current test point (p_idx) as a FIFO queue
    # for the number of points to search. The FIFO queue is implemented by using
    # while-loop instead of a for-loop. In neighbor points, the points are represented
    # by their index in the original dataset.
    i = 0
    while i < len(neighbor_idxs):
        # get the next point from the queue
        neighbor_idx = neighbor_idxs[i]

        # if neighbor_p was labeled as noise during the seed search, it will not
        # be a branch point (not enough neighbors). Make this a leaf point of the cluster
        # and move on.
        if labels[neighbor_idx] == -1:
            labels[neighbor_idx] = cluster_id
        # otherwise if the neighbor point isn't already claimed, claim it as part of the current cluster
        elif labels[neighbor_idx] == 0:
            labels[neighbor_idx] = cluster_id

            # find all the neighbors of this neighbor
            neighbors_neighbor_idxs = region_query(points, neighbor_idx)

            # if neighbors_neighbor_idxs has at least the the required minimum points, it's a branch point
            # and all its neighbors are added to the FIFO queue to searched
            if len(neighbors_neighbor_idxs) >= MIN_PTS:
                neighbor_idxs = neighbor_idxs + neighbors_neighbor_idxs
            # if neighbors_neighbor_idxs does not have MIN_PTS, then it is a leaf point and nothing is done

        # advance to the next point in the FIFO queue
        i += 1


def run(coordinates):
    points = list(coordinates)

    # Stores a cluster label for each point in a list of equal size to the number of points;
    # initially each point as a label of 0 (no cluster)
    # Reserved labels: 0 (no cluster), -1 (noise)
    labels = [0] * len(points)

    cluster_id = 0

    # iterate through the points as looking for new seed points to attempt to grow new clusters
    for p_idx, p in enumerate(points):
        print("Clustering: {:.2f}%".format((p_idx + 1) / len(points) * 100))

        # points already belonging to a cluster cannot be new seed points and are skipped
        if not (labels[p_idx] == 0):
            continue

        neighbor_idxs = region_query(points, p_idx)

        # if the number of neighbor points is below the minimum number of points for a cluster,
        # this point is noise. Noise indicates the point is not a valid seed point, but it may
        # still be picked up in another cluster as a boundary point.
        if len(neighbor_idxs) < MIN_PTS:
            labels[p_idx] = -1
        # otherwise if there are at least MIN_PTS nearby, use this point as a seed for a new cluster
        else:
            cluster_id += 1
            grow_cluster(points, labels, p_idx, neighbor_idxs, cluster_id)
    return labels
