#!/usr/bin/env python
# Kyle Fitzsimmons, 2019


class DaySummary(object):
    '''
    :param str timezone:                  String representation of the timezone as listed in the IANA tz
                                          database (e.g., America/Montreal).
                                          See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    :param datetime.Date date:            The naive date used for determining a complete trip day.
    :param bool has_trips:                Boolean value to indicate whether a date contains any trips.
    :param bool is_complete:              Boolean value to indicate whether a date with trips is considered
                                          complete or not.
    :param object start_point:            The database point for the first available GPS coordinate on a localized date.
    :param object end_point:              The database point for the last available GPS coordinate on a localized date.
    :param int consecutive_inactive_days: The total number of days in the latest inactivity streak (reset on any
                                          complete day).
    :param int inactivity_streak:         The longest streak of consecutively inactive days for a user.
    '''

    def __init__(
        self,
        timezone,
        date,
        has_trips,
        is_complete,
        start_point,
        end_point,
        consecutive_inactive_days,
        inactivity_streak,
    ):
        self.timezone = timezone
        self.date = date
        self.has_trips = has_trips
        self.is_complete = is_complete
        self.start_point = start_point
        self.end_point = end_point
        self.consecutive_inactive_days = consecutive_inactive_days
        self.inactivity_streak = inactivity_streak

    def __repr__(self):
        return f"<tripkit.models.DaySummary date={self.date.isoformat()} has_trips={self.has_trips} is_complete={self.is_complete}>"
