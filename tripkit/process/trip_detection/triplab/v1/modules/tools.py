#!/usr/bin/env python
# Kyle Fitzsimmons, 2016
import math
import time
import utm

# python 2 cPickle import speedup
try:
    import cPickle as pickle
except ImportError:
    import pickle


def timeit(func):
    def timed(*args, **kwargs):
        t0 = time.time()
        result = func(*args, **kwargs)
        t1 = time.time()

        print(f"{func.__name__}(args, kwargs): {t1-t0} sec")
        return result

    return timed


# @timeit
def process_utm(points):
    '''Convert WGS84 lat/lon points to UTM for performing spatial queries'''
    out_points = []
    for p in points:
        try:
            p['latitude'], p['longitude'] = float(p['latitude']), float(p['longitude'])
            p['easting'], p['northing'], _, _ = utm.from_latlon(p['latitude'], p['longitude'])
            p['speed'] = float(p['speed'])
            p['h_accuracy'] = float(p['h_accuracy'])
            p['v_accuracy'] = float(p['v_accuracy'])
            out_points.append(p)
        except utm.error.OutOfRangeError:
            pass
    return out_points


# hackish way to copy a dictionary faster than deepcopy
# @timeit
def quick_deepcopy(dictionary):
    return pickle.loads(pickle.dumps(dictionary, -1))


def pythagoras(point1, point2):
    '''Calculate the distance in meters between two UTM points'''
    a = point2[0] - point1[0]
    b = point2[1] - point1[1]
    d = math.sqrt(a ** 2 + b ** 2)
    return d


def velocity_check(point1, point2, period):
    '''Check if a missing period is above a minimum velocity threshold to indicate that
       an unusually large time gap is a movement period and a continuation of a trip'''
    minimum_walking_speed = 15.0 * 1000 / 3600
    if period:
        if (pythagoras(point1, point2) / period) > minimum_walking_speed:
            return True
        else:
            return False
    else:
        return False
