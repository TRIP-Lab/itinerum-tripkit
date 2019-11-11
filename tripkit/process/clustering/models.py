#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


class ClusterInfo:
    def __init__(self, group_num=None, label=None):
        self.group_num = group_num
        self.label = label

    def __repr__(self):
        return f"<tripkit.process.clustering.models.ClusterInfo group_num={self.group_num} label={self.label}>"

