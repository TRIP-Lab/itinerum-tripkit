#!/usr/bin/env python
# Kyle Fitzsimmons, 2019
from tripkit.utils.datetime import localize



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

        records.append({
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
            'commute_time_work_s': commute_work
        })
    return records