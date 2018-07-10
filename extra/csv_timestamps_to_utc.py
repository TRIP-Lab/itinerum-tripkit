#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
import csv
import dateutil.parser
import os
import pytz

source_dir_name = 'mobilité-responses-2017'

output_dir = os.path.join('./cleaned', source_dir_name)
if not os.path.exists(output_dir):
    os.mkdir(output_dir)


def csv_rows_to_UTC(filename, dt_columns):
    source_csv_fn = os.path.join('./uncleaned', source_dir_name, filename)
    normalized = []
    headers = None
    with open(source_csv_fn, 'r', encoding='utf-8-sig') as csv_f:
        reader = csv.DictReader(csv_f)
        headers = reader.fieldnames
        for row in reader:
            for col in dt_columns:
                local_dt = row.pop(col)
                col_utc = col + '_UTC'
                row[col_utc] = dateutil.parser.parse(local_dt).astimezone(pytz.utc)
            normalized.append(row)

    normalized_headers = []
    for h in headers:
        if h in dt_columns:
            normalized_headers.append(h + '_UTC')
        else:
            normalized_headers.append(h)

    dest_csv_fn = os.path.join('./cleaned', source_dir_name, filename)
    with open(dest_csv_fn, 'w') as csv_f:
        writer = csv.DictWriter(csv_f, fieldnames=normalized_headers)
        writer.writeheader()
        writer.writerows(normalized)

print('Updating records to UTC for:', source_dir_name)
csv_rows_to_UTC('survey_responses.csv', ['created_at'])
csv_rows_to_UTC('prompt_responses.csv', ['displayed_at', 'recorded_at'])
csv_rows_to_UTC('coordinates.csv', ['timestamp'])