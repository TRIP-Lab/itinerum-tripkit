#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from datetime import timedelta
import pytz

from tripkit.utils.datetime import localize, split_at_midnight


def group_activity_by_date(activity, timezone):
    start_date = localize(activity.first_seen_UTC, timezone).date()
    end_date = localize(activity.last_seen_UTC, timezone).date()
    # determine if last trip occurs over midnight and, if so, add an additional day to date range
    last_trip_start_UTC, last_trip_end_UTC, _ = activity.commute_times[-1]
    last_trip_start = localize(last_trip_start_UTC, timezone)
    last_trip_end = localize(last_trip_end_UTC, timezone)
    if len(split_at_midnight(last_trip_start, last_trip_end)) == 2:
        end_date += timedelta(days=1)

    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    by_date = {}
    for d in date_range:
        by_date[d] = {
            'commutes': {},
            'dwells': {},
            'distance': 0,
            'num_trips': 0,
            'num_points': 0,
            'start_UTC': None,
            'end_UTC': None,
        }

    for start_UTC, end_UTC, label in activity.commute_times:
        start = localize(start_UTC, timezone)
        end = localize(end_UTC, timezone)
        for date, duration in split_at_midnight(start, end):
            by_date[date]['commutes'].setdefault(label, []).append(duration)
            by_date[date]['num_trips'] += 1
        if not by_date[date]['start_UTC']:
            by_date[date]['start_UTC'] = start_UTC
        by_date[date]['end_UTC'] = end_UTC

    for start_UTC, end_UTC, label in activity.dwell_times:
        start = localize(start_UTC, timezone)
        end = localize(end_UTC, timezone)
        for date, duration in split_at_midnight(start, end):
            by_date[date]['dwells'].setdefault(label, []).append(duration)

    for timestamp_UTC, distance in activity.distances:
        date = localize(timestamp_UTC, timezone).date()
        by_date[date]['distance'] += distance
        by_date[date]['num_points'] += 1
    return by_date


def run_full(user_activity, timezone):
    activities_by_date = group_activity_by_date(user_activity, timezone)

    all_dwell_labels = user_activity.all_dwell_labels()
    all_commute_labels = user_activity.all_commute_labels()
    duration_keys = []

    records = []
    for date, activities in activities_by_date.items():
        dwell_durations = {}
        for label, durations in activities['dwells'].items():
            dwell_durations.setdefault(label, 0)
            dwell_durations[label] += sum(durations)

        trips_duration = 0
        commute_durations = {}
        for label, durations in activities['commutes'].items():
            commute_durations.setdefault(label, 0)
            commute_durations[label] += sum(durations)
            trips_duration += sum(durations)

        start_time = None
        if activities['start_UTC']:
            start_time = localize(activities['start_UTC'], timezone)
        end_time = None
        if activities['end_UTC']:
            end_time = localize(activities['end_UTC'], timezone)

        # generate and append row record
        r = {
            'uuid': user_activity.uuid,
            'date': date,
            'start_time': start_time,
            'end_time': end_time,
            'num_trips': activities['num_trips'],
            'num_points': activities['num_points'],
            'trips_distance_m': activities['distance'],
            'trips_duration_s': trips_duration,
        }
        for dwell_label in all_dwell_labels:
            key = f'dwell_{dwell_label}_s'
            r[key] = dwell_durations.get(dwell_label)
            if not key in duration_keys:
                duration_keys.append(key)
        for commute_label in all_commute_labels:
            key = f'commute_{commute_label}_s'
            r[key] = commute_durations.get(commute_label)
            if not key in duration_keys:
                duration_keys.append(key)
        records.append(r)
    summaries = {'records': records, 'duration_keys': duration_keys}
    return summaries
