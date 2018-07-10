#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import datetime
import pytz


def find_participation_daterange(summaries, min_dt):
    for dt in sorted([t['start'] for t in summaries]):
        if dt > min_dt:
            first_date = dt.date()
            break
    last_date = dt.date()
    return first_date, last_date


def count_complete_days(summaries):
    min_dt = datetime(2017, 6, 1, tzinfo=pytz.utc)
    first_date, last_date = find_participation_daterange(summaries, min_dt)
    group_trips_by_day(first_date, last_date, summaries)
