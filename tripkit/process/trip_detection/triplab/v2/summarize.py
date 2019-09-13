#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import pytz
import utm

from .algorithm import distance_m


def run(user, timezone=None):
    '''
    Summarizes detected trips information as dictionary records for writing to .csv
    with each trip condensed to a single row.

    :param user: A py:class:`tripkit.models.User` object with detected trip information.
    :param tz:   (Optional) A pytz timezone object for localizing the trip start and
                 end times for UTC to the survey region's timezone.

    :type user: class:`tripkit.models.User`
    :type tz: datetime.tzinfo
    '''
    if timezone:
        tz = pytz.timezone(timezone)

    records = []
    for t in user.trips:
        t.start.easting, t.start.northing, _, _ = utm.from_latlon(t.start.latitude, t.start.longitude)
        t.end.easting, t.end.northing, _, _ = utm.from_latlon(t.end.latitude, t.end.longitude)

        r = {
            'uuid': user.uuid,
            'trip_id': t.num,
            'start_UTC': t.start_UTC,
            'end_UTC': t.end_UTC,
            'trip_code': t.trip_code,
            'olat': t.start.latitude,
            'olon': t.start.longitude,
            'dlat': t.end.latitude,
            'dlon': t.end.longitude,
            'direct_distance': distance_m(t.start, t.end),
            'cumulative_distance': t.distance,
        }
        if timezone:
            r['start'] = pytz.utc.localize(t.start_UTC).astimezone(tz)
            r['end'] = pytz.utc.localize(t.end_UTC).astimezone(tz)
        records.append(r)
    return records
