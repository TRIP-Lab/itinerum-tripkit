#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
import pytz


# return a naive UTC datetime to a localized datetime with offset tzinfo
def localize(naive_utc, timezone):
    tz = pytz.timezone(timezone)
    return pytz.utc.localize(naive_utc).astimezone(tz)


# TODO: improve docstring
#  get the durations for the trip as either a 1-member (no split at midnight) or a
# 2-member (split at midnight) list of tuples --> [(date, duration_s), ...]
def split_at_midnight(start, end):
    if start.day != end.day:
        midnight = end.replace(hour=0, minute=0, second=0, microsecond=0)
        return [(start.date(), (midnight - start).total_seconds()), (end.date(), (end - midnight).total_seconds())]
    return [(start.date(), (end - start).total_seconds())]
