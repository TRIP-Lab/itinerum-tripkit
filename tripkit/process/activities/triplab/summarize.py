#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from tripkit.utils.datetime import localize


def _tally_commutes_all(activity):
    commutes = {'total': 0}
    for start_UTC, end_UTC, label in activity.commute_times:
        duration = (end_UTC - start_UTC).total_seconds()
        commutes['total'] += duration
        commutes.setdefault(label, 0)
        commutes[label] += duration
    return commutes


def _tally_dwells_all(activity):
    dwells = {'total': 0}
    for start_UTC, end_UTC, label in activity.dwell_times:
        duration = (end_UTC - start_UTC).total_seconds()
        dwells['total'] += duration
        dwells.setdefault(label, 0)
        dwells[label] += duration
    return dwells


# returns rows for a .csv summary of activity and complete days
def run_condensed(user_activity, day_summaries, timezone):
    # aggregate survey tallies
    tallies = {
        'uuid': user_activity.uuid,
        'start_timestamp_UTC': user_activity.first_seen_UTC.isoformat(),
        'start_timestamp': localize(user_activity.first_seen_UTC, timezone).isoformat(),
        'end_timestamp_UTC': user_activity.last_seen_UTC.isoformat(),
        'end_timestamp': localize(user_activity.last_seen_UTC, timezone).isoformat(),
        'complete_days': 0,
        'incomplete_days': 0,
        'inactive_days': 0,
        'commute_time_work_s': 0,
        'commute_time_study_s': 0,
        'dwell_time_home_s': 0,
        'dwell_time_work_s': 0,
        'dwell_time_study_s': 0,
        'num_trips': 0,
        'total_trips_duration_s': 0,
        'total_trips_distance_m': 0,
        'avg_trips_per_day': 0,
        'avg_trip_distance_m': 0,
    }

    # tally days by complete or incomplete
    for summary in day_summaries:
        if summary.has_trips:
            if summary.is_complete:
                tallies['complete_days'] += 1
            else:
                tallies['incomplete_days'] += 1
        else:
            tallies['inactive_days'] += 1

    # tally commute durations
    commutes = _tally_commutes_all(user_activity)
    tallies['commute_time_work_s'] = commutes.get('work')
    tallies['commute_time_study_s'] = commutes.get('study')
    # tally dwell durations (time spent staying at a semantic location)
    dwells = _tally_dwells_all(user_activity)
    tallies['dwell_time_home_s'] = dwells.get('home')
    tallies['dwell_time_work_s'] = dwells.get('work')
    tallies['dwell_time_study_s'] = dwells.get('study')
    # sums
    tallies['num_trips'] = len(user_activity.commute_times)
    tallies['total_trips_duration_s'] = commutes['total']
    tallies['total_trips_distance_m'] = sum(dist for _, dist in user_activity.distances)
    # avgs
    active_days = tallies['complete_days'] + tallies['incomplete_days']
    tallies['avg_trips_per_day'] = tallies['num_trips'] / active_days
    tallies['avg_trip_distance_m'] = tallies['total_trips_distance_m'] / tallies['num_trips']
    return tallies


def run_full(user_activity, timezone):
    activities_by_date = user_activity.group_by_date(timezone)

    records = []
    for date, activities in activities_by_date.items():
        # TODO: create tally function
        trips_duration = 0
        commute_study, commute_work = 0, 0
        for label, durations in activities['commutes'].items():
            trips_duration += sum(durations)
            if label == 'study':
                commute_study += sum(durations)
            elif label == 'work':
                commute_work += sum(durations)
        dwell_home, dwell_study, dwell_work = 0, 0, 0
        for label, durations in activities['dwells'].items():
            if label == 'home':
                dwell_home += sum(durations)
            elif label == 'study':
                dwell_study += sum(durations)
            elif label == 'work':
                dwell_work += sum(durations)

        start_time = None
        if activities['start_UTC']:
            start_time = localize(activities['start_UTC'], timezone)
        end_time = None
        if activities['end_UTC']:
            end_time = localize(activities['end_UTC'], timezone)

        records.append(
            {
                'uuid': user_activity.uuid,
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'num_trips': activities['num_trips'],
                'num_points': activities['num_points'],
                'trips_distance_m': activities['distance'],
                'trips_duration_s': trips_duration,
                'dwell_time_home_s': dwell_home,
                'dwell_time_work_s': dwell_work,
                'dwell_time_study_s': dwell_study,
                'commute_time_study_s': commute_study,
                'commute_time_work_s': commute_work,
            }
        )
    return records
