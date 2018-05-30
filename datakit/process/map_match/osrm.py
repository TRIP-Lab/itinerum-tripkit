#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import datetime
import requests

from . import config


API_URLS = {
    'BIKING': config.MAP_MATCHING_BIKING_API_URL,
    'DRIVING': config.MAP_MATCHING_DRIVING_API_URL,
    'WALKING': config.MAP_MATCHING_BIKING_API_URL
}


class MapMatcherAPI:
    @staticmethod
    def match(coordinates, matcher='DRIVING'):
        latlngs = []
        radiuses = []
        timestamps = []
        last_ts = None
        for c in coordinates:
            latlngs.append('{lon},{lat}'.format(lat=c.latitude, lon=c.longitude))
            radiuses.append('{radius}'.format(radius=c.h_accuracy))
            # timestamps represented as seconds integers from UNIX epoch
            timestamp_epoch = int((c.timestamp_UTC - datetime(1970, 1, 1)).total_seconds())
            timestamps.append(str(timestamp_epoch))
            
        latlngs_str = ';'.join(latlngs)
        radiuses_str = ';'.join(radiuses)
        timestamps_str = ';'.join(timestamps)

        parameters = {
            'overview': 'full',
            'radiuses': radiuses_str,
            'timestamps': timestamps_str,
            'gaps': 'ignore',
            'tidy': 'true'
        }
        if not API_URLS[matcher].endswith('/'):
            API_URLS[matcher] += '/'
        r = requests.post(API_URLS[matcher] + latlngs_str, data=parameters)
        return r.json()
