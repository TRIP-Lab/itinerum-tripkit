#!/usr/bin/env python

# Based upon GERT 1.2 (2016-06-03): GIS-based Episode Reconstruction Toolkit
# Stage 1 - GPS Preprocessing Module (gert_1.2/scripts/detect_stop_trial_20150408.py)
# Ported to itinerum-tripkit by Kyle Fitzsimmons, 2019
from tripkit.utils import calc


def detect_stop_by_attributes(coordinates):
    labeled_coordinates = []
    last_c = None
    for idx, c in enumerate(coordinates):
        if not last_c:
            labeled_coordinates.append(c)
            last_c = c
            continue

        # GERT note:
        # Minimum speed was determined based on various experiments, which
        # happened to be the sum of the velocity (speed) accuracy of GPS device
        # used (Qstarz BT-Q1000X, see www.qstarz.com) with accuracy of 0.1 m/s
        # for without aid, plus with that of DGPS (WAAS, EGNOS, MSAS) of
        # 0.05 m/s, hence a total of 0.15 m/s. IGNORED: The heading change was also
        # determined based on various experiments with the GPS data.
        if c.speed_ms <= 0.15:  # or c.delta_heading > 90:
            c.cluster_label = 'stop'
        else:
            c.cluster_label = 'trip'

        next_c_idx = idx + 1
        next_c_exists = next_c_idx + 1 <= len(coordinates)
        if next_c_exists:
            next_c = coordinates[next_c_idx]

            if next_c.speed_ms <= 0.15 or next_c.delta_heading > 90:
                next_c.cluster_label = 'stop'
            else:
                next_c.cluster_label = 'trip'

            # affirm stop based on previous and next points
            if last_c.cluster_label == 'stop' and next_c.cluster_label == 'stop':
                if c.cluster_label == 'trip' and c.duration_s >= 60:
                    c.cluster_label = 'trip'
                else:
                    c.cluster_label = 'stop'
            elif last_c.cluster_label == 'trip' and next_c.cluster_label == 'trip':
                if c.cluster_label == 'stop' and c.duration_s >= 120:
                    c.cluster_label = 'stop'
                else:
                    c.cluster_label = 'trip'
            # remove position jumps or false trips that resulted from movement indoors
            # (usually high-rise buildings)
            elif last_c.cluster_label == 'trip' and next_c.cluster_label == 'stop':
                # speed should slow down before stop
                if c.cluster_label == 'trip':
                    velocity_ratio = (c.speed_ms - last_c.speed_ms) / last_c.speed_ms
                    if velocity_ratio > 1:
                        c.cluster_label = 'stop'

        # append updated coordinate with status
        labeled_coordinates.append(c)
        last_c = c

    # last point is always "stop"
    labeled_coordinates[-1].cluster_label = 'stop'
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
    last_status = None

    # NOTE: original updates lat/lon with signs based on N,E,S,W attributes in
    #       .csv row, is this actually necessary? Skipped...attributes do not
    #       exist in Rainham demo dataset
    segments = []  # replacement for `intermediatelist` in source
    for idx, c in enumerate(labeled_coordinates):
        if last_status != c.cluster_label:
            num_points = len(durations)
            total_duration = sum(durations)
            total_distance = sum(distances)
            avg_delta_heading = calc.average(delta_headings)
            avg_speed = calc.average(speeds)

            # Author's note:
            # Some background on threshold values:
            # based on 3 feet per second (fps) minimum pedestrian walking speed (LaPlante & Kaeser 2007)
            # or 0.91 m/s and a minimum walk duration of 60 s (Bialostozky 2009)
            # see also MUTCD 2009 Section 4E.06 Pedestrian Intervals and Signal Phases
            trip_rule_1 = last_status == 'trip' and num_points > 3 and avg_delta_heading < 30
            trip_rule_2 = total_distance >= 55 and avg_speed >= 0.91
            stop_rule_1 = last_status == 'stop' and total_duration >= 120

            if trip_rule_1 and trip_rule_2:
                print("HELLO FROM detect_stops.py -- first rule")
                import sys

                sys.exit()
            elif stop_rule_1:
                print("HELLO FROM detect_stops.py -- second rule")
                import sys

                sys.exit()
            else:
                print("HELLO FROM detect_stops.py -- none")
        else:
            latitudes.append(c.latitude)
            longitudes.append(c.longitude)
            distances.append(c.distance_m)
            durations.append(c.duration_s)
            bearings.append(c.bearing)
            speeds.append(c.speed_ms)
            delta_headings.append(c.delta_heading)

        last_status = c.cluster_label


def run(coordinates):
    if len(coordinates) < 3:
        return []

    # preliminary classification
    labeled_coordinates = detect_stop_by_attributes(coordinates)
    print(labeled_coordinates)

    # summarize_stops(labeled_coordinates)
    # print(f"total labeled coordinates: {len(labeled_coordinates)}")

    # stops = predetect_stop_orig(coordinates)
    # for s in stops:
    #     print(s)
