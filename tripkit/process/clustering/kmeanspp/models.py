#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


class Point():
    def __init__(self, p, dim=1, id=-1):
        self.id = id
        self.coordinates = []
        self.centroid = None

        for i in range(0, dim):
            self.coordinates.append(p[i])
        
    def __repr__(self):
        return f"<tripkit.process.clustering.kmeanspp.models.Point id={self.id}>"

class Centroid():
    def __init__(self, p):
        self.point = p
        self.cluster_points = []

    def update(self, p):
        self.point = p

    def add_point(self, p):
        self.cluster_points.append(p)

    def remove_point(self, p):
        self.cluster_points.remove(p)

class ClusterInfo:
    def __init__(self, group_num=None, label=None):
        self.group_num = group_num
        self.label = label

    def __repr__(self):
        return f"<tripkit.process.clustering.kmeanspp.models.ClusterInfo group_num={self.group_num} label={self.label}>"