#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import datetime, timedelta
import pytz


def find_participation_daterange(trips, min_dt):
    '''Determine the time bounds for selecting user trips
       to remove any trips with inproper timestamps from
       a user's incorrect system clock.
    '''
    first_date, last_date = None, None
    for trip in trips:
        if trip.start_UTC > min_dt:
            first_date = trip.start_UTC.date()
            break
    last_date = trips[-1].end_UTC.date()
    return first_date, last_date


def group_trips_by_day(first_date, last_date, trips):
    '''Create a preliminary dict which summarizes just the
       information we care about from trips on every day a
       user has participated.
    '''
    dates_dict = {}
    delta = last_date - first_date
    min_dt = datetime.combine(first_date, datetime.min.time())
    for i in range(delta.days + 1):
        date = first_date + timedelta(days=i)
        dates_dict[date] = {}
        dates_dict[date]['trip_codes'] = []
        dates_dict[date]['start_loc'] = []
        dates_dict[date]['end_loc'] = []

    for t in trips:
        if not t.start_UTC >= min_dt:
            continue
        date = t.start_UTC.date()
        dates_dict[date]['start_loc'].append(t.start_latlon)
        dates_dict[date]['end_loc'].append(t.end_latlon)
        dates_dict[date]['trip_codes'].append(t.trip_code)
    return dates_dict


def find_complete_days(daily_trip_summaries):
    '''Create a dictionary to give trip information summarized
       for a given day as to whether it contains any trips and
       whether the day is complete (i.e., no missing trips)
    '''
    daily_summaries = {}
    for date, trip_summaries in daily_trip_summaries.items():
        if not trip_summaries['trip_codes']:
            daily_summaries[date] = {
                'has_trips': False,
                'complete': False
            }
        # disallow any days with a `missing` labeled trip
        elif [c for c in trip_summaries['trip_codes'] if (c >= 100 and c < 200)]:
            daily_summaries[date] = {
                'has_trips': True,
                'complete': False
            }
        else:
            daily_summaries[date] = {
                'has_trips': True,
                'complete': True
            }
    return daily_summaries


def find_inactivity_periods(daily_summaries):
    pass


def run(trips):
    min_dt = datetime(2017, 6, 1)
    first_date, last_date = find_participation_daterange(trips, min_dt)
    daily_trip_summaries = group_trips_by_day(first_date, last_date, trips)
    daily_summaries = find_complete_days(daily_trip_summaries)
    from pprint import pprint
    pprint(daily_summaries)



