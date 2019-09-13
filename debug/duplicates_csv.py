#!/usr/bin/env
# Kyle Fitzsimmons, 2018
'''
A script to clean duplicate rows from .csv data for loading to SQL tables
with a UNIQUE column constraint or index
'''
import csv

# config
in_csv_fp = './uncleaned/subway_stations/mtlvantor_stations.csv'
out_csv_fp = './cleaned/subway_stations/mtlvantor_stations.csv'


# create a list of unique .csv rows to write to new file
columns_to_check = ['Y', 'X']
seen = []
out_rows = []
headers = None
with open(in_csv_fp, 'r') as in_csv_f:
    reader = csv.DictReader(in_csv_f)
    headers = reader.fieldnames
    for row in reader:
        values = [row[c] for c in columns_to_check]
        if values not in seen:
            seen.append(values)

# write cleaned .csv output
with open(out_csv_fp, 'w') as out_csv_f:
    writer = csv.DictWriter(out_csv_f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(out_rows)
