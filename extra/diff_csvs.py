#!/usr/bin/env
# Kyle Fitzsimmons, 2018
import ciso8601
import csv
import dateutil.parser
import pytz

csv1_fp = './diffs/cfsm-original-trip_summaries.csv'
csv2_fp = './diffs/cfsm-new-trip_summaries.csv'
csv_diff_fp = './diffs/cfsm-diff-trip_summaries.csv'


# create a {uuid: {start: end} } dictionary for
# looking up each csv2 row
csv1_headers = None
csv1_lookup = {}
with open(csv1_fp, 'r', encoding='utf-8-sig') as csv1_f:
    reader = csv.DictReader(csv1_f)
    csv1_headers = reader.fieldnames

    for row in reader:
        uuid = row['user_id'].lower()

        if uuid != '0035f6cf-de8a-49b2-baeb-83d6e044b6a9':
            continue

        start = dateutil.parser.parse(row['start']).astimezone(pytz.utc).replace(tzinfo=None)
        end = dateutil.parser.parse(row['end']).astimezone(pytz.utc).replace(tzinfo=None)
        csv1_lookup.setdefault(uuid, {})[start] = end



csv2_diff_rows = []
csv2_headers = None
with open(csv2_fp, 'r') as csv2_f:
    reader = csv.DictReader(csv2_f)
    csv2_headers = reader.fieldnames
    for row in reader:
        csv2_uuid = row['uuid'].lower()

        if csv2_uuid != '0035f6cf-de8a-49b2-baeb-83d6e044b6a9':
            continue

        csv2_start = ciso8601.parse_datetime(row['start']).replace(tzinfo=None)
        csv2_end = ciso8601.parse_datetime(row['end']).replace(tzinfo=None)

        if csv2_uuid in csv1_lookup:
            csv1_end = csv1_lookup[csv2_uuid].get(csv2_start)
            if not csv1_end:
                row['match'] = -1
            elif csv1_end == csv2_end:
                row['match'] = True
            else:
                row['match'] = False
        else:
            row['match'] = -2
        csv2_diff_rows.append(row)

# write the csv2 trips to a file the boolean flag indicating whether
# there is a found matched trip from the original dataset
csv2_headers.append('match')
with open(csv_diff_fp, 'w') as csv_diff_f:
    writer = csv.DictWriter(csv_diff_f, fieldnames=csv2_headers)
    writer.writeheader()
    writer.writerows(csv2_diff_rows)
