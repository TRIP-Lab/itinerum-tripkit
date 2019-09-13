#!/usr/bin/env python
# Based upon GERT 1.2 (2016-06-03): GIS-based Episode Reconstruction Toolkit
# Ported to itinerum-tripkit by Kyle Fitzsimmons, 2019
import math


def average(nums):
    '''
    Return the simple average of a list of numeric values. If the list is empty, None is returned.

    :param list nums: List of numeric values
    '''
    if nums:
        try:
            return sum(nums) / len(nums)
        except TypeError:
            raise TypeError(f"all elements of input list must be numeric: {nums}")
