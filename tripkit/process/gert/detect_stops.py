#!/usr/bin/env python

# Based upon GERT 1.2 (2016-06-03): GIS-based Episode Reconstruction Toolkit
# Ported to itinerum-tripkit by Kyle Fitzsimmons, 2019
from .utils import calc


def detect_stop_by_attributes(coordinates):
    labeled_coordinates = []
    last_c = None
    for idx, c in enumerate(coordinates):
        if not last_c:
            c.status = 'stop'
            labeled_coordinates.append(c)
            last_c = c
            continue

        # Author's note:
        # Minimum speed was determined based on various experiments, which
        # happened to be the sum of the velocity (speed) accuracy of GPS device
        # used (Qstarz BT-Q1000X, see www.qstarz.com) with accuracy of 0.1 m/s
        # for without aid, plus with that of DGPS (WAAS, EGNOS, MSAS) of
        # 0.05 m/s, hence a total of 0.15 m/s. The heading change was also
        # determined based on various experiments with the GPS data.

        # detect stop based on speed and heading change
        if c.speed_ms <= 0.15 or c.delta_heading > 90:
            c.status = 'stop'
        else:
            c.status = 'trip'

        next_c_idx = idx + 1
        next_c_exists = next_c_idx <= len(coordinates) - 1
        if next_c_exists:
            next_c = coordinates[next_c_idx]

            if next_c.speed_ms <= 0.15 or next_c.delta_heading > 90:
                next_c.status = 'stop'
            else:
                next_c.status = 'trip'

            # affirm stop based on previous and next points
            if last_c.status == 'stop' and next_c.status == 'stop':
                if c.status == 'trip' and c.duration_s >= 60:
                    c.status = 'trip'
                else:
                    c.status = 'stop'
            elif last_c.status == 'trip' and next_c.status == 'trip':
                if c.status == 'stop' and c.duration_s >= 120:
                    c.status = 'stop'
                else:
                    c.status = 'trip'
            # remove position jumps or false trips that resulted from movement indoors
            # (usually high-rise buildings)
            elif last_c.status == 'trip' and next_c.status == 'stop':
                # speed should slow down before stop
                if c.status == 'trip':
                    velocity_ratio = (c.speed_ms - last_c.speed_ms) / last_c.speed_ms
                    if velocity_ratio > 1:
                        c.status = 'stop'

        # append updated coordinate with status
        labeled_coordinates.append(c)
        last_c = c

    # last point is always "stop"
    labeled_coordinates[-1].status = 'stop'
    return labeled_coordinates


def summarize_stops(labeled_coordinates):
    # TODO: refactor whatever this is
    latitudes = []
    longitudes = []
    distances = []
    bearings = []
    durations = []
    speeds = []
    delta_headings = []

    first_line = True
    last_status = None

    # NOTE: original updates lat/lon with signs based on N,E,S,W attributes in
    #       .csv row, is this actually necessary? Skipped...

    for c in labeled_coordinates:
        if first_line:
            latitudes.append(c.latitude)
            longitudes.append(c.longitude)
            distances.append(c.distance_m)
            durations.append(c.duration_s)
            bearings.append(c.bearing)
            speeds.append(c.speed_ms)
            delta_headings.append(c.delta_heading)

            last_status = c.status
            first_line = False
            continue

        if last_status != c.status:
            total_duration = sum(durations)
            total_distance = sum(distances)
            num_points = len(durations)
            avg_delta_heading = calc.average(delta_headings)
            avg_speed = calc.average(speeds)

            # # Debug statements
            # print(c.latitude, c.longitude, c.distance_m, c.duration_s, c.bearing, c.speed_ms)
            # print("total duration:", total_duration)
            # print("total distance:", total_distance)
            # print("num points:", num_points)
            # print("avg delta heading:", avg_delta_heading)
            # print("avg speed:", avg_speed)
            # print("---------------------")

            # Author's note:
            # Some background on threshold values:
            # based on 3 feet per second (fps) minimum pedestrian walking speed (LaPlante & Kaeser 2007)
            # or 0.91 m/s and a minimum walk duration of 60 s (Bialostozky 2009)
            # see also MUTCD 2009 Section 4E.06 Pedestrian Intervals and Signal Phases
            trip_rule_1 = last_status == 'trip' and num_points > 3 and avg_delta_heading < 30
            trip_rule_2 = total_distance >= 55 and avg_speed >= 0.91
            stop_rule_1 = last_status == 'stop' and total_duration >= 120

            if trip_rule_1 and trip_rule_2:
                print("HELLO FROM detect_stops.py")
                import sys

                sys.exit()

        last_status = c.status


# # ---- classes
# class GPSLine():
#     """
#     Create an object for each GPS line in the list.

#     This class simplifies retrieval of GPS point attributes: change in heading,
#     speed, duration, and status.
#     """
#     def __init__(self, deltahead, speed, dursec, status=None):
#         self.deltahead = deltahead  # change in heading in degrees
#         self.speed = speed  # meters per second
#         self.dursec = dursec  # duration in seconds
#         self.status = status  # stop or trip


# def predetect_stop_orig(filterlist):
#     # Local variables
#     refinelist = []
#     firstline = True

#     for i in range(2, len(filterlist)):
#         f_tripkit = filterlist[i]
#         f = f_tripkit.DEBUG_csv_row()
#         future = GPSLine(f_tripkit.delta_heading, f_tripkit.speed_ms, f_tripkit.duration_s)

#         if firstline:
#             p_tripkit = filterlist[i - 2]
#             p = p_tripkit.DEBUG_csv_row()
#             past = GPSLine(p_tripkit.delta_heading, p_tripkit.speed_ms, p_tripkit.duration_s, status='stop')

#             c_tripkit = filterlist[i - 1]
#             c = c_tripkit.DEBUG_csv_row()
#             current = GPSLine(c_tripkit.delta_heading, c_tripkit.speed_ms, c_tripkit.duration_s)
#             firstline = False

#         # Minimum speed was determined based on various experiments, which
#         # happened to be the sum of the velocity (speed) accuracy of GPS device
#         # used (Qstarz BT-Q1000X, see www.qstarz.com) with accuracy of 0.1 m/s
#         # for without aid, plus with that of DGPS (WAAS, EGNOS, MSAS) of
#         # 0.05 m/s, hence a total of 0.15 m/s. The heading change was also
#         # determined based on various experiments with the GPS data.

#         # Detect stop based on speed and heading change.
#         if current.speed <= 0.15 or current.deltahead > 90:
#             current.status = 'stop'
#         else:
#             current.status = 'trip'

#         if future.speed <= 0.15 or future.deltahead > 90:
#             future.status = 'stop'
#         else:
#             future.status = 'trip'

#         # Affirm stop based on previous and next points.
#         if past.status == 'stop' and future.status == 'stop':
#             if current.status == 'trip' and current.dursec >= 60:
#                 current.status == 'trip'
#             else:
#                 current.status == 'stop'
#         elif past.status == 'trip' and future.status == 'trip':
#             if current.status == 'stop' and current.dursec >= 120:
#                 current.status = 'stop'
#             else:
#                 current.status = 'trip'
#         # Remove position jumps or false trips that resulted from
#         # movements indoors (usually in high rise buildings).
#         elif past.status == 'trip' and future.status == 'stop':
#             if current.status == 'trip':  # speed should slow down before stop
#                 velocity_ratio = (current.speed - past.speed) / past.speed
#                 if velocity_ratio > 1:
#                     current.status = 'stop'
#                 else:
#                     pass
#             else:
#                 pass
#         # Remove erroneous GPS readings caused by multipath errors;
#         # observed behavior of significant gaps (duration or distance)
#         # and a statistical descriptor may be a solution...
#         # perhaps need to determine single-mode segments to isolate
#         # impossible speeds or use standard deviation for duration...
#         else:
#             pass

#         # Append status.
#         if not refinelist:
#             p.append(past.status)
#             c.append(current.status)
#             past_line = ','.join(p)
#             current_line = ','.join(c)
#             refinelist.append(past_line)
#             refinelist.append(current_line)
#         else:
#             c.append(current.status)
#             current_line = ','.join(c)
#             refinelist.append(current_line)

#         # Store values for forward comparison.
#         c = f
#         past = current
#         current = future
#     else:  # end of 'for loop'
#         current.status = 'stop'
#         c.append(current.status)
#         current_line = ','.join(c)
#         refinelist.append(current_line)
#     return refinelist


def run(coordinates):
    if len(coordinates) < 3:
        return []

    # preliminary classification
    labeled_coordinates = detect_stop_by_attributes(coordinates)

    summarize_stops(labeled_coordinates)
    print(f"total labeled coordinates: {len(labeled_coordinates)}")

    # stops = predetect_stop_orig(coordinates)
    # for s in stops:
    #     print(s)
