#!/usr/bin/env python
# Kyle Fitzsimmons, 2015
import itertools
import utm

from .modules import labels, tools
from .modules.trip_codes import trip_codes


def filter_accuracy(points, cutoff=30):
    '''Filter out points with high reported horizontal accuracy values'''
    for p in points:
        if p['h_accuracy'] <= cutoff:
            yield p


def filter_erroneous_distance(points, check_speed=60):
    '''Filter out points with unreasonably fast speeds where next point is closer
       than erroneous point'''
    points, points_copy = itertools.tee(points)
    next(points_copy)  # push ahead for lookup

    last_p = None
    for p in points:
        try:
            next_p = next(points_copy)
        except StopIteration:
            yield p
            return

        # do not test first point but save for testing next point
        if not last_p:
            last_p = p
            yield p

        # find the distance and time passed since last point collected
        distance_from_last_point = tools.pythagoras(
            (last_p['easting'], last_p['northing']), (p['easting'], p['northing'])
        )
        seconds_since_last_point = (p['timestamp'] - last_p['timestamp']).total_seconds()

        # toss the point if the speed is greater than `check_speed` and the distance between
        # the previous and next point is less than the distance from the last point to this one
        if distance_from_last_point and seconds_since_last_point:
            kph_since_last_point = (distance_from_last_point / seconds_since_last_point) * 3.6
            distance_between_adjacent_points = tools.pythagoras(
                (last_p['easting'], last_p['northing']), (next_p['easting'], next_p['northing'])
            )
            if kph_since_last_point >= check_speed and distance_between_adjacent_points < distance_from_last_point:
                continue
        last_p = p
        yield p


def break_by_timegap(points, timegap=360):
    '''Break into trip segments when time recorded between points is
       > timegap variable and group points by segment number in a dictionary'''
    trips = []
    group = 1
    for idx, row in enumerate(points):
        dt = row['timestamp']
        if idx == 0:
            previous_row = row
            period = 0
        else:
            period = int((dt - previous_row['timestamp']).total_seconds())
            if period > timegap:
                group += 1
            previous_row = row

        row['segment_group'] = group
        row['break_period'] = period
        row['note'] = ''
        row['merge_codes'] = []
        trips.append(dict(row))

    # group trips by segments in a lookup dictionary
    segment_groups = {}
    for t in trips:
        segment_groups.setdefault(t['segment_group'], []).append(t)
    return segment_groups


def metro_stations_utm(metro_stations):
    '''Get UTM coordinates for metro stations supplied by database lat/lngs'''
    stations = []
    for station in metro_stations:
        northing, easting, _, _ = utm.from_latlon(station['latitude'], station['longitude'])
        stations.append((northing, easting))
    return stations


def metro_buffer(stations, point, distance):
    '''Return a boolean indicating whether a point is within a specified distance of
       of a dictionary of metro stations'''
    for station in stations:
        if tools.pythagoras(station, point) <= distance:
            return True, station
    return False, None


def find_metro_transfers(stations, segment_groups, buffer_m):
    '''Create a list of tuples containing two consecutive segment numbers. Test the last (end) point
        of the first segment and the first (start) point of the second segment to identify a transfer'''
    # create a list of tuples container pairs of overlapping segment IDs in order to test
    # for missing underground trips between each
    potential_transfers, last_segment_num = [], None
    for segment_num in segment_groups:
        if last_segment_num:
            potential_transfers.append((last_segment_num, segment_num))
        last_segment_num = segment_num

    # create a list of transfers found by intersecting the last and first segments
    # with each available metro station
    found_transfers = []
    for pt in potential_transfers:
        seg1_num, seg2_num = pt
        segment1, segment2 = segment_groups[seg1_num], segment_groups[seg2_num]
        segment1_end_p = (segment1[-1]['easting'], segment1[-1]['northing'])
        segment2_start_p = (segment2[0]['easting'], segment2[0]['northing'])

        intersect1, station1 = metro_buffer(stations, segment1_end_p, buffer_m)
        intersect2, station2 = metro_buffer(stations, segment2_start_p, buffer_m)

        # check for transfer and ensure it is not at same station
        if intersect1 and intersect2 and station1 != station2:
            # test that metro trip does not take longer than 80 minutes between stops
            # and that the user is travelling at least 0.1m/s on average
            interval = (segment2[0]['timestamp'] - segment1[-1]['timestamp']).total_seconds()
            distance = tools.pythagoras(segment1_end_p, segment2_start_p)
            segment_speed = distance / interval
            if interval < 4800 and segment_speed > 0.1:
                segment_groups = labels.metro(segment_groups, pt)
                found_transfers.append(pt)

    # merge tuples with overlapping transfers to a single trip
    transfers = []
    for ft in found_transfers:
        # test whether first transfer num is included in the last found transfer
        if transfers and ft[0] in transfers[-1]:
            transfers[-1].append(ft[1])
        else:
            transfers.append(list(ft))
    transfers = [tuple(t) for t in transfers]

    # link segments that have be indentified as having a metro transfer
    counter = 0
    linked_trips = {}
    transfer_end_ids = [t[1] for t in transfers]
    for num, segments in segment_groups.items():
        # append to previous segment if indentified as a transfer
        if num in transfer_end_ids:
            linked_trips[counter].extend(segments)
            for segment in linked_trips[counter]:
                segment['note'] = 'trip with metro transfer'
        # otherwise create a new trip
        else:
            counter += 1
            linked_trips[counter] = segments
    return linked_trips


def connect_by_velocity(linked_trips):
    velocity_connections = {}
    last_trip = None
    for num, trip in linked_trips.items():
        if not last_trip:
            velocity_connections[num] = trip
            last_trip = trip
            continue
        prev_pt = (last_trip[-1]['easting'], last_trip[-1]['northing'])
        next_pt = (trip[0]['easting'], trip[0]['northing'])
        period = int((trip[0]['timestamp'] - last_trip[-1]['timestamp']).total_seconds())
        last_num = sorted(velocity_connections.keys())[-1]
        if tools.velocity_check(prev_pt, next_pt, period) is True:
            # label end and start points of segments before combining as a single trip
            labels.velocity(velocity_connections[last_num], trip)
            velocity_connections[last_num].extend(trip)
        else:
            velocity_connections[num] = trip
        last_trip = trip
    return velocity_connections


def filter_single_points(linked_trips):
    '''Detects single points and attaches to nearest to/from trip within 20 minute
       time period and 150 meter radius'''

    test_trips = tools.quick_deepcopy(linked_trips)
    cleaned_trips = {}
    offset = 0
    max_time = 20
    max_dist = 150
    for idx, (num, trip) in enumerate(test_trips.items()):
        # check for single points that have been isolated from other segments and
        # calculate the time since the previous trips and until the next trip
        if (idx != 0) and (num + 1 in linked_trips) and (num - 1 in linked_trips) and (len(trip) == 1):
            # skip first and last points
            point = trip[0]
            point['note'] = 'single point'
            point_loc = (point['easting'], point['northing'])
            point_dt = point['timestamp']

            last_trip_num = num - 1
            last_trip_end = linked_trips[last_trip_num][-1]
            last_trip_pt = (last_trip_end['easting'], last_trip_end['northing'])
            last_trip_dist = tools.pythagoras(last_trip_pt, point_loc)

            next_trip_num = num + 1
            next_trip_start = linked_trips[next_trip_num][0]
            next_trip_pt = (next_trip_start['easting'], next_trip_start['northing'])
            next_trip_dist = tools.pythagoras(point_loc, next_trip_pt)

            if last_trip_dist <= next_trip_dist:
                point['timestamp'] = last_trip_end['timestamp']
                labels.single_point(point, cleaned_trips[num - offset - 1], 'append')
                cleaned_trips[num - offset - 1].append(point)
            else:
                point['timestamp'] = next_trip_start['timestamp']
                labels.single_point(point, test_trips[num + 1], 'insert')
                test_trips[num + 1].insert(0, point)
            offset += 1
        else:
            cleaned_trips[num - offset] = trip
    return cleaned_trips


def infer_missing_trips(stations, linked_trips):
    '''Determines the missing distance and period between each trip; key is correlated to linked_trips
       where the missing trip key indicates the gap before the linked trip with the same key'''
    missing_trips = {}
    prior_trip = None
    for num, trip in linked_trips.items():
        if not prior_trip:
            prior_trip = trip
            continue

        prior_point = (prior_trip[-1]['easting'], prior_trip[-1]['northing'])
        first_point = (trip[0]['easting'], trip[0]['northing'])
        spatial_gap = tools.pythagoras(prior_point, first_point)
        prior_timestamp = prior_trip[-1]['timestamp']
        timestamp = trip[0]['timestamp']
        period = float((timestamp - prior_timestamp).seconds)

        missing = {
            'id': prior_trip[-1]['id'],
            'latitude': prior_trip[-1]['latitude'],
            'longitude': prior_trip[-1]['longitude'],
            'easting': prior_trip[-1]['easting'],
            'northing': prior_trip[-1]['northing'],
            'timestamp': prior_timestamp,
            'next_time': timestamp,
            'distance': spatial_gap,
            'break_period': period,
            'note': '',
            'merge_codes': [],
        }

        if spatial_gap < 250:
            missing['note'] = 'missing trip - less than 250m'
            missing['merge_codes'].append('missing trip - less than 250m')
            missing_trips[num] = missing
        else:
            # check for missing trips to/from a metro
            intersect1, station1 = metro_buffer(stations, prior_point, 300)
            intersect2, station2 = metro_buffer(stations, first_point, 300)
            if intersect1 and intersect2 and station1 != station2:
                missing['note'] = 'missing trip - metro'
                missing['merge_codes'].append('missing trip - metro')
                missing_trips[num] = missing

            # next, check if missing trip is below the cold start threshold
            elif spatial_gap <= 750:
                missing['note'] = 'cold start'
                missing['prev_time'] = prior_timestamp
                missing['timestamp'] = timestamp
                missing['merge_codes'].append('cold start')
                trip.insert(0, missing)
            # if no criteria is match, mark as a vanilla missing trip
            else:
                missing['note'] = 'missing trip'
                missing['merge_codes'].append('missing trip')
                missing_trips[num] = missing
        prior_trip = trip
    return missing_trips


def merge_trips(trips, missing_trips, stations):
    '''Merge and label trips'''
    rows = []
    offset = 0
    for idx, trip in trips.items():
        note = None
        if idx in missing_trips:
            note = missing_trips[idx]['note']
            p = {
                'id': missing_trips[idx]['id'],
                'latitude': missing_trips[idx]['latitude'],
                'longitude': missing_trips[idx]['longitude'],
                'easting': missing_trips[idx]['easting'],
                'northing': missing_trips[idx]['northing'],
                'break_period': missing_trips[idx]['break_period'],
                'dist_prev': missing_trips[idx]['distance'],
                'trip_distance': '',
                'segment': '',
                'trip': idx + offset,
                'timestamp': None,
                'note': note,
                'merge_codes': missing_trips[idx]['merge_codes'],
            }
            if note == 'missing trip - less than 250m':
                p['timestamp'] = trip[0]['timestamp']
                rows.append(p)
            else:
                p['timestamp'] = missing_trips[idx]['timestamp']
                p['trip'] = idx + offset
                rows.append(p)

                p = {
                    'id': missing_trips[idx]['id'],
                    'latitude': trip[0]['latitude'],
                    'longitude': trip[0]['longitude'],
                    'easting': trip[0]['easting'],
                    'northing': trip[0]['northing'],
                    'break_period': missing_trips[idx]['break_period'],
                    'dist_prev': missing_trips[idx]['distance'],
                    'trip_distance': '',
                    'segment': '',
                    'trip': idx + offset,
                    'timestamp': missing_trips[idx]['next_time'],
                    'note': note,
                    'merge_codes': trip[0]['merge_codes'],
                }
                rows.append(p)
                offset += 1

        # label complete trips segments
        start_pt = (trip[0]['easting'], trip[0]['northing'])
        end_pt = (trip[-1]['easting'], trip[-1]['northing'])

        intersect1, intersect2 = False, False
        station1, station2 = None, None
        intersect1, station1 = metro_buffer(stations, start_pt, 300)
        intersect2, station2 = metro_buffer(stations, end_pt, 300)

        if (intersect1 and intersect2) and station1 != station2:
            note = 'complete trip - metro'
        else:
            note = 'complete trip'

        if len(trip) == 1:
            note = 'single point'

        for point in trip:
            p = point.copy()
            p['trip'] = idx + offset
            if note:
                p['note'] = note
            rows.append(p)
    return rows


def distance_speed(trip_group):
    trip_distance = 0.0
    last_point = None

    # test for the specific case of a single point being attached to a
    # missing trip <250 m
    if len(trip_group) == 2:
        notes = [p['note'] for p in trip_group]
        if 'missing trip - less than 250m' in notes and 'single point' in notes:
            for p in trip_group:
                p['distance'], p['trip_distance'], p['avg_speed'] = 0, 0, 0
            return trip_group

    for idx, p in enumerate(trip_group):
        point = (p['easting'], p['northing'])
        if idx == 0:
            p['distance'], p['trip_distance'], p['avg_speed'] = 0, 0, 0
            last_point = point
        elif last_point:
            p['distance'] = tools.pythagoras(last_point, point)
            trip_distance += p['distance']
            p['trip_distance'] = trip_distance
            if p['break_period'] > 0:
                p['avg_speed'] = p['distance'] / p['break_period']
            else:
                p['avg_speed'] = trip_group[idx - 1]['avg_speed']
        if p['note'] != 'missing trip - less than 250m':
            last_point = point
    return trip_group


def labeling_hierarchy(labels):
    if 'missing trip - less than 250m' in labels:
        if 'complete trip - metro' in labels:
            labels = ['complete trip - metro']
        elif 'complete trip' in labels:
            labels = ['complete trip']
        elif 'single point' in labels:
            labels = ['single point']
    elif 'missing trip' in labels:
        labels = ['missing trip']
    elif 'missing trip - metro' in labels:
        labels = ['missing trip - metro']
    return labels


def summarize(rows):
    '''Condense trip to information from first and last GPS point and add attribute information'''
    # group points into dictionaries by trip id
    trips, group, last_trip_id = {}, [], 1
    for row in rows:
        trip_id = row['trip']
        if trip_id == last_trip_id:
            group.append(row)
        else:
            if group:
                trips[last_trip_id] = distance_speed(group)
                group = [row]
            last_trip_id = trip_id
    if group:
        trips[last_trip_id] = distance_speed(group)

    summaries = {}
    for num, trip in trips.items():
        labels = list(set([p['note'] for p in trip]))
        labels = labeling_hierarchy(labels)
        assert len(labels) == 1
        c = trip_codes[labels[0]]

        start_pt = trip[0]
        end_pt = trip[-1]

        merge_codes = set()
        for segment in trip:
            for mcode in segment['merge_codes']:
                merge_codes.add(mcode)

        direct_distance = tools.pythagoras(
            (start_pt['easting'], start_pt['northing']), (end_pt['easting'], end_pt['northing'])
        )

        if end_pt['trip_distance'] > 250 and c == 103:
            c = 1
        elif end_pt['trip_distance'] == 0:
            c = 201
        elif end_pt['trip_distance'] < 250:
            c = 202

        outrow = {
            'olat': start_pt['latitude'],
            'olon': start_pt['longitude'],
            'dlat': end_pt['latitude'],
            'dlon': end_pt['longitude'],
            'trip_id': num,
            'trip_code': c,
            'start': start_pt['timestamp'],
            'end': end_pt['timestamp'],
            'direct_distance': direct_distance,
            'cumulative_distance': end_pt['trip_distance'],
            'merge_codes': ', '.join(merge_codes),
        }

        summaries[num] = outrow
        for p in trip:
            p['trip_code'] = c

    return trips, summaries


# @tools.timeit
def run(parameters, metro_stations, points):
    stations = metro_stations_utm(metro_stations)
    points = tools.process_utm(points)
    if not points or len(points) < 2:
        return None, None

    high_accuracy_points = filter_accuracy(points, cutoff=parameters['accuracy_cutoff_meters'])
    cleaned_points = filter_erroneous_distance(high_accuracy_points, check_speed=60)
    segment_groups = break_by_timegap(cleaned_points, timegap=parameters['break_interval_seconds'])
    metro_linked_trips = find_metro_transfers(stations, segment_groups, buffer_m=parameters['subway_buffer_meters'])
    velocity_connected_trips = connect_by_velocity(metro_linked_trips)
    cleaned_trips = filter_single_points(velocity_connected_trips)
    missing_trips = infer_missing_trips(stations, cleaned_trips)
    rows = merge_trips(cleaned_trips, missing_trips, stations)
    trips, summaries = summarize(rows)
    return trips, summaries
