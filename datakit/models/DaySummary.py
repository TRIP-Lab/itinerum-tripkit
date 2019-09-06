#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


class DaySummary(object):
    '''
    ::
    :param str timezone:                  String representation of the timezone as listed in the IANA tz
                                          database (e.g., America/Montreal).
                                          See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    :param datetime.Date date:            The naive date used for determining a complete trip day.
    :param bool has_trips:                Boolean value to indicate whether a date contains any trips.
    :param bool is_complete:              Boolean value to indicate whether a date with trips is considered
                                          complete or not.
    :param int start_point_id:            The database ID for the first available GPS coordinate on a localized date.
    :param int end_point_id:              The database ID for the last available GPS coordinate on a localized date.
    :param float inactivity_distance:     The total distance (m) traveled the two nearest (before and after) complete
                                          activity days.
    '''

    def __init__(self, timezone, date, has_trips, is_complete, start_point_id, end_point_id, inactivity_distance):
        self.timezone = timezone
        self.date = date
        self.has_trips = has_trips
        self.is_complete = is_complete
        self.start_point_id = start_point_id
        self.end_point_id = end_point_id
        self.inactivity_distance = inactivity_distance

    def __repr__(self):
        return f"<DaySummary date={self.date.isoformat()} has_trips={self.has_trips} is_complete={self.is_complete}>"
