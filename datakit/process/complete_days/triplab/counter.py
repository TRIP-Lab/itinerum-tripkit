#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
from datetime import datetime, timedelta
from geopy import distance
import pytz


def find_participation_daterange(trips, min_dt):
    """Determine the time bounds for selecting user trips
       to remove any trips with inproper timestamps from
       a user's incorrect system clock.
    """
    first_date, last_date = None, None
    for trip in trips:
        if trip.start_UTC > min_dt:
            first_date = trip.start_UTC.date()
            break
    last_date = trips[-1].end_UTC.date()
    return first_date, last_date


def group_trips_by_day(first_date, last_date, trips):
    """Create a preliminary dict which summarizes just the
       information we care about from trips on every day a
       user has participated.
    """
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
    """Create a dictionary to give trip information summarized
       for a given day as to whether it contains any trips and
       whether the day is complete (i.e., no missing trips)
    """
    daily_summaries = {}
    for date, trip_summaries in daily_trip_summaries.items():
        if not trip_summaries['trip_codes']:
            daily_summaries[date] = {
                'has_trips': False,
                'is_complete': False
            }
        # disallow any days with a `missing` labeled trip
        elif [c for c in trip_summaries['trip_codes'] if (c >= 100 and c < 200)]:
            daily_summaries[date] = {
                'has_trips': True,
                'is_complete': False
            }
        else:
            daily_summaries[date] = {
                'has_trips': True,
                'is_complete': True
            }
    return daily_summaries


def add_inactivity_periods(daily_summaries):
    summary_before = None
    inactive_days = 0
    first_inactive_day = None
    for date, summary in sorted(daily_summaries.items()):
        no_trip_data = not any([summary['has_trips'], summary['is_complete']])
        if no_trip_data:
            inactive_days += 1
            if not first_inactive_day:
                first_inactive_day = date
        else:
            inactive_days = 0
            first_inactive_day = None

        summary['consecutive_inactive_days'] = inactive_days
        summary['first_inactive_day'] = first_inactive_day

        if summary_before is not None:
            summary['before_is_complete'] = summary_before['is_complete'] is True
        else:
            summary['before_is_complete'] = False
        summary_before = summary

    # add the total inactive day tally to each day within the streak of inactive days
    summary_after = None
    latest_streak_max = None
    for date, summary in sorted(daily_summaries.items(), reverse=True):
        if not latest_streak_max and summary['consecutive_inactive_days']:
            latest_streak_max = summary['consecutive_inactive_days']

        if latest_streak_max:
            summary['inactive_day_streak'] = latest_streak_max

        if date == summary['first_inactive_day']:
            latest_streak_max = None

        if summary_after is not None:
            summary['after_is_complete'] = summary_after['is_complete'] is True
        else:
            summary['after_is_complete'] = False
        summary_after = summary

    return daily_summaries


def find_explained_inactivity_periods(daily_summaries, daily_trip_summaries):
    """Label completely inactive days (no trips) as complete days when
       there are complete days adjacent (up to 2 day maximum).
    """
    for date, summary in sorted(daily_summaries.items()):
        summary['inactivity_distance'] = 0.

        no_trip_data = not any([summary['has_trips'], summary['is_complete']])
        if no_trip_data:
            # test whether day is included within a 1-2 missing data streak
            if summary['inactive_day_streak'] <= 2:
                prev_active_day = summary['first_inactive_day'] - timedelta(days=1)
                next_active_day = summary['first_inactive_day'] + timedelta(days=summary['inactive_day_streak'])

                prev_complete_day = None
                if prev_active_day in daily_summaries and daily_summaries[prev_active_day]['is_complete']:
                    prev_complete_day = prev_active_day

                next_complete_day = None
                if prev_active_day in daily_summaries and daily_summaries[prev_active_day]['is_complete']:
                    next_complete_day = prev_active_day

                if prev_complete_day and next_complete_day:
                    last_end_coordinate = daily_trip_summaries[prev_active_day]['end_loc'][-1]
                    next_start_coordinate = daily_trip_summaries[next_active_day]['start_loc'][0]
                    inactivity_distance = distance.distance(last_end_coordinate, next_start_coordinate).meters

                    if inactivity_distance < 750.:
                        summary['is_complete'] = True
                        summary['inactivity_distance'] = inactivity_distance
            else:
                pass  # no change to original data
    return daily_summaries




def run(trips):
    min_dt = datetime(2017, 6, 1)
    first_date, last_date = find_participation_daterange(trips, min_dt)
    daily_trip_summaries = group_trips_by_day(first_date, last_date, trips)
    
    daily_summaries = find_complete_days(daily_trip_summaries)
    daily_summaries = add_inactivity_periods(daily_summaries)
    
    complete_days = find_explained_inactivity_periods(daily_summaries, daily_trip_summaries)
    from pprint import pprint
    pprint(complete_days)

    return complete_days



