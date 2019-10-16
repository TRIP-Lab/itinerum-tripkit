#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


def average(nums):
    if nums:
        try:
            return sum(nums) / len(nums)
        except TypeError:
            raise TypeError(f"all elements of input list must be numeric: {nums}")


class RollingWindow(object):
    def __init__(self, size=5):
        self.values = []
        self.size = size

    def add(self, v):
        if len(self.values) < self.size:
            self.values.append(v)
        else:
            self.values = self.values[1:] + [v]

    def average(self):
        if len(self.values) >= self.size:
            return sum(self.values) / len(self.values)
