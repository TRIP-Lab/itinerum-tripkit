#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from datetime import datetime, timedelta
import pytz

from .models import DailyGroups
from tripkit.models import DaySummary as LibraryDaySummary
from tripkit.utils import geo


def trips_UTC_to_local(trips, tz):
    localized_trips = []
    for trip in trips:
        trip.start_local = tz.localize(trip.start_UTC)
        trip.end_local = tz.localize(trip.end_UTC)
        localized_trips.append(trip)
    return localized_trips


def find_participation_daterange(trips, min_dt):
    '''
    Determine the time bounds for selecting user trips to remove any trips
    with inproper timestamps from a user's incorrect system clock.
    '''
    first_date, last_date = None, None
    for trip in trips:
        if trip.start_local > min_dt:
            first_date = trip.start_local.date()
            break
    last_date = trips[-1].end_local.date()
    return first_date, last_date


def group_trips_by_day(first_date, last_date, trips, tz):
    '''
    Create a preliminary dict which summarizes just the information we care about
    from trips on every day a user has participated.
    '''
    daily_groups = DailyGroups(first_date, last_date)
    for t in trips:
        min_dt = tz.localize(datetime.combine(first_date, datetime.min.time()))
        if not t.start_local >= min_dt:
            continue
        daily_groups.add_trip(t)
    return daily_groups


def find_complete_days(daily_groups):
    '''
    Create a dictionary to give trip information summarized for a given day as to
    whether it contains any trips and whether the day is complete (i.e., no missing trips)
    '''
    daily_summaries = {}
    for date, group in daily_groups.sorted_by_date():
        if not group.has_trips:
            daily_summaries[date] = {'has_trips': False, 'is_complete': False}
        elif group.contains_missing_trips:
            daily_summaries[date] = {'has_trips': True, 'is_complete': False}
        else:
            daily_summaries[date] = {'has_trips': True, 'is_complete': True}
        daily_summaries[date]['start_point'] = group.start_point
        daily_summaries[date]['end_point'] = group.end_point
    return daily_summaries


def add_inactivity_periods(daily_summaries):
    '''
    Iterate over the daily summaries once forwards and once backwards to supply inactivity information
    to adjacent days to the start and end dates.
    '''
    inactive_days, summary_before, first_inactive_day = None, None, None
    for date, summary in sorted(daily_summaries.items()):
        no_trip_data = not any([summary['has_trips'], summary['is_complete']])
        if no_trip_data:
            if not inactive_days:
                inactive_days = 0
            inactive_days += 1
            if not first_inactive_day:
                first_inactive_day = date
        else:
            inactive_days = None
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
    latest_streak_max = 0
    for date, summary in sorted(daily_summaries.items(), reverse=True):
        if summary['consecutive_inactive_days']:
            latest_streak_max = max(latest_streak_max, summary['consecutive_inactive_days'])
            summary['inactive_day_streak'] = latest_streak_max

        # same as lookahead `summary_before` above but labeled after since order is reversed
        if summary_after is not None:
            summary['after_is_complete'] = summary_after['is_complete'] is True
        else:
            summary['after_is_complete'] = False
        summary_after = summary

    max_inactivity_streak = latest_streak_max if latest_streak_max else None
    for date, summary in daily_summaries.items():
        summary['max_inactivity_streak'] = max_inactivity_streak
    return daily_summaries


def find_explained_inactivity_periods(daily_summaries, daily_groups):
    '''
    Label completely inactive days (no trips) as complete days when there are complete days adjacent
    (up to 2 day maximum).
    '''
    for date, summary in sorted(daily_summaries.items()):
        no_trip_data = not any([summary['has_trips'], summary['is_complete']])
        if no_trip_data:
            # test whether day is included within a missing 1 or 2-day data streak
            if summary['inactive_day_streak'] <= 2:
                prev_active_day = summary['first_inactive_day'] - timedelta(days=1)
                next_active_day = summary['first_inactive_day'] + timedelta(days=summary['inactive_day_streak'])

                prev_complete_day = None
                if prev_active_day in daily_summaries and daily_summaries[prev_active_day]['is_complete']:
                    prev_complete_day = prev_active_day

                next_complete_day = None
                if next_active_day in daily_summaries and daily_summaries[next_active_day]['is_complete']:
                    next_complete_day = prev_active_day

                if prev_complete_day and next_complete_day:
                    last_end_point = daily_groups.get_end_point(prev_active_day)
                    next_start_point = daily_groups.get_second_point(next_active_day)
                    inactivity_distance = geo.haversine_distance_m(last_end_point, next_start_point)

                    if inactivity_distance < 750.0:
                        summary['is_complete'] = True
    return daily_summaries


def wrap_for_tripkit(tz, complete_days):
    tripkit_complete_days = []
    for date, day_summary in complete_days.items():
        tk_summary = LibraryDaySummary(
            timezone=tz.zone,
            date=date,
            has_trips=day_summary['has_trips'],
            is_complete=day_summary['is_complete'],
            start_point=day_summary['start_point'],
            end_point=day_summary['end_point'],
            consecutive_inactive_days=day_summary['consecutive_inactive_days'],
            inactivity_streak=day_summary['max_inactivity_streak'],
        )
        tripkit_complete_days.append(tk_summary)
    return tripkit_complete_days


def run(trips, timezone):
    if not trips:
        return None

    tz = pytz.timezone(timezone)

    min_dt = tz.localize(datetime(1999, 6, 1))
    localized_trips = trips_UTC_to_local(trips, tz)

    first_date, last_date = find_participation_daterange(localized_trips, min_dt)
    daily_groups = group_trips_by_day(first_date, last_date, localized_trips, tz)

    daily_summaries = find_complete_days(daily_groups)
    daily_summaries = add_inactivity_periods(daily_summaries)

    complete_days = find_explained_inactivity_periods(daily_summaries, daily_groups)
    return wrap_for_tripkit(tz, complete_days)
