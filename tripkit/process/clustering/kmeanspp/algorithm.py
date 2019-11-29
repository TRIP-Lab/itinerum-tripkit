#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
# K-Means++ implementation from: https://github.com/siddheshk/Faster-Kmeans
import numpy as np
import random

from .models import Centroid, Point


class KMeansPlusPlus():
    def __init__(self, data, n_clusters=1):
        self.K = n_clusters
        self.data = data
        self.centroids = []
        self.D2 = []

        self.initialize_centroids()

    def _dist_from_centroids(self):
        D2 = np.array([
            np.linalg.norm(x - self.centroids[-1]) ** 2 for x in self.data
        ])
        if len(self.D2) == 0:
            self.D2 = np.array(D2[:])
        else:
            for i in range(len(D2)):
                if D2[i] < self.D2[i]:
                    self.D2[i] = D2[i]

    def _choose_next_centroid(self):
        self.cumulative_probabilities = (self.D2 / self.D2.sum()).cumsum()
        r = random.random()
        idx = np.where(self.cumulative_probabilities >= r)[0][0]
        return self.data[idx]

    def initialize_centroids(self):
        self.centroids = random.sample(self.data, 1)
        while len(self.centroids) < self.K:
            self._dist_from_centroids()
            self.centroids.append(self._choose_next_centroid())


class KMeans():
    def __init__(self, data, threshold=1000, seed_centroids=None):
        assert isinstance(seed_centroids, list) and len(seed_centroids) > 0

        self.k = len(seed_centroids)  # temp
        self.dim = len(data[0])
        self.kmeans_threshold = threshold
        self.seeds = seed_centroids
        self.centroids = [Centroid(Point(s)) for s in self.seeds]
        
        self.cluster_distances = {}
        self.r = {}  # ? already matched lookup ?
        self.lower_bound = {}
        self.upper_bound = {}
        self.old_centroid = {}
        
        self.points = []
        for idx, d in enumerate(data):
            p = Point(d, id=idx)
            self.points.append(p)
            self.r[p.id] = False
            self.lower_bound[p.id] = [0 for _ in range(self.k)]

        for cluster_idx in range(self.k):
            self.cluster_distances.setdefault(cluster_idx, {
                'neighbors': {},
                'minimum': None
            })

    def _distance(self, point1, point2):
        dist = 0
        for x in range(0, self.dim):
            dist += (point1.coordinates[x] - point2.coordinates[x]) ** 2 
        return dist ** 0.5

    def _initial_centroid(self, point):
        pos = 0
        if point.centroid is not None:
            min_dist = dist = self._distance(point, self.centroids[point.centroid].point)
            closest_centroid = point.centroid
            current_centroid = point.centroid
        else:
            min_dist = dist = self._distance(point, self.centroids[pos].point)
            closest_centroid = pos
            current_centroid = pos
        
        self.lower_bound[point.id][closest_centroid] = min_dist
        for centroid in self.centroids:
            if pos != current_centroid:
                if 0.5 * self.cluster_distances[closest_centroid]['neighbors'][pos] < min_dist:
                    dist = self._distance(point, centroid.point)
                    self.lower_bound[point.id][pos] = dist
                    if min_dist > dist:
                        min_dist = dist
                        closest_centroid = pos
            pos += 1
        self.upper_bound[point.id] = min_dist
        return closest_centroid

    def _get_centroid(self, point):
        if self.r[point.id]:
            min_dist = self._distance(point, self.centroids[point.centroid].point)
            self.upper_bound[point.id] = min_dist
            self.r[point.id] = False
        else:
            min_dist = self.upper_bound[point.id]

        pos = 0
        closest_centroid = point.centroid
        for centroid in self.centroids:
            if pos != point.centroid:
                if self.upper_bound[point.id] > self.lower_bound[point.id][pos]:
                    current_dist = self.cluster_distances[closest_centroid]['neighbors'][pos]
                    if self.upper_bound[point.id] > 0.5 * current_dist:
                        if min_dist > self.lower_bound[point.id][pos] or min_dist > 0.5 * current_dist:
                            dist = self._distance(point, centroid.point)
                            self.lower_bound[point.id][pos] = dist
                            if min_dist > dist:
                                self.upper_bound[point.id] = min_dist = dist
                                closest_centroid = pos
            pos += 1
        return closest_centroid

    def _calculate_cluster_distances(self):
        for i in range(self.k):
            for j in range(i + 1, self.k):
                dist = self._distance(self.centroids[i].point, self.centroids[j].point)
                self.cluster_distances[i]['neighbors'][j] = dist
                self.cluster_distances[j]['neighbors'][i] = dist
                
                i_min, j_min = self.cluster_distances[i]['minimum'], self.cluster_distances[j]['minimum']
                if not i_min or i_min > 0.5 * dist:
                    self.cluster_distances[i]['minimum'] = 0.5 * dist
                if not j_min or j_min > 0.5 * dist:
                    self.cluster_distances[j]['minimum'] = 0.5 * dist

    def _initial_assignment(self):
        self._calculate_cluster_distances()
        for i in range(len(self.points)-1, -1, -1):
            p = self.points[i]
            closest_centroid = self._initial_centroid(p)
            if p.centroid is None:
                p.centroid = closest_centroid
                self.centroids[closest_centroid].add_point(p)

    def _assign_points(self):
        completed = {}
        distances = {}
        self._calculate_cluster_distances()
        for i in range(self.k):
            distances[i] = self._distance(self.old_centroid[i], self.centroids[i].point)
        for i in range(len(self.centroids) - 1, -1, -1):
            centroid1 = self.centroids[i]
            for j in range(len(centroid1.cluster_points) - 1, -1, -1):
                centroid2 = centroid1.cluster_points[j]
                if completed.get(centroid2.id):
                    continue
                for k in range(self.k):
                    bound = self.lower_bound[centroid2.id][k]
                    self.lower_bound[centroid2.id][k] = max(bound - distances[k], 0)
                self.upper_bound[centroid2.id] += distances[centroid2.centroid]
                self.r[centroid2.id] = True
                completed[centroid2.id] = 1
                if self.upper_bound[centroid2.id] > self.cluster_distances[centroid2.centroid]['minimum']:
                    closest_centroid = self._get_centroid(centroid2)
                    if centroid2 != closest_centroid:
                        self.centroids[i].cluster_points[j].centroid = closest_centroid
                        self.centroids[closest_centroid].add_point(centroid2)
                        del self.centroids[i].cluster_points[j]


    def _recalculate_centroid(self):
        pos = 0
        for centroid in self.centroids:
            self.old_centroid[pos] = centroid.point
            zeros = [0] * self.dim
            mean = Point(zeros, self.dim)

            for point in centroid.cluster_points:
                for i in range(0, self.dim):
                    mean.coordinates[i] += point.coordinates[i]
            for i in range(0, self.dim):
                try:
                    mean.coordinates[i] = mean.coordinates[i] / len(centroid.cluster_points)
                except:
                    mean.coordinates[i] = 0
            centroid.update(mean)
            self.centroids[pos] = centroid
            pos += 1

    def _calculate_error(self):
        error = 0
        for centroid in self.centroids:
            for point in centroid.cluster_points:
                error += self._distance(point, centroid.point) ** 2
        return error

    def fit(self):
        error1 = 2 * self.kmeans_threshold + 1
        error2 = 0
        current_error = 1E16
        self._initial_assignment()
        self._recalculate_centroid()
        
        i = 0
        while current_error > self.kmeans_threshold:
            error1 = self._calculate_error()
            self._assign_points()
            self._recalculate_centroid()
            error2 = self._calculate_error()
            current_error = 100 * abs(error1 - error2) / abs(error1)
            i += 1

        self._assign_points()
        self._recalculate_centroid()
        # error = self._calculate_error()
        return self

    def _plot(self):
        import matplotlib.pyplot as plt
        import seaborn as sns
        sns.set()
        
        cmap = ['red', 'blue', 'green', 'yellow', 'orange', 'black']

        sorted_points = []
        for p in self.points:
            while len(sorted_points) - 1 < p.centroid:
                sorted_points.append([])
            sorted_points[p.centroid].append(p)

        for idx, sorts in enumerate(sorted_points):
            data = []
            for p in sorts:
                data.append(p.coordinates)
            plt.plot(data, 'o', c=cmap[idx])    

        while True:
            try:
                plt.show()
                break
            except UnicodeDecodeError:
                continue
            break
