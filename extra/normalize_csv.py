#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
import csv
import ciso8601
from datetime import datetime
import logging
import mmap
import os
import pytz
import time

# config
min_dt = datetime(1999, 1, 1)
source_dir_name = 'mtltrajet-responses-2016'
output_dir = os.path.join('./cleaned', source_dir_name)

# init--create the new output dir and setup logging
if not os.path.exists(output_dir):
    os.mkdir(output_dir)
logging.basicConfig(level=logging.INFO)


# https://stackoverflow.com/questions/9629179/python-counting-lines-in-a-huge-10gb-file-as-fast-as-possible
# https://stackoverflow.com/questions/32792303/find-all-spaces-newlines-and-tabs-in-a-python-file
def count_lines(filename):
    def _blocks(file, size=65536):
        while True:
            b = file.read(size)
            if not b:
                break
            yield b

    with open(filename, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)
        return sum(bl.count(b'\n') for bl in _blocks(mm))


def format_headers(headers, dt_columns, expected_columns, rename_columns,
                   split_locations=False):
    """
    Rename any datetime columns to `datetime_UTC` and rename any
    other declartions in `rename_colums` map. Add non-existing
    `expected_columns` at the end and split locations columns, if
    applicable.
    """
    normalized_headers = []
    rename_keys = [c[0] for c in rename_columns]
    location_keys = [c for c in headers if c.startswith('location')]
    for h in headers:
        if h in dt_columns:
            h = h + '_UTC'

        if h in rename_keys:
            for orig, rename in rename_columns:
                if h == orig:
                    normalized_headers.append(rename)
        elif h in location_keys:
            normalized_headers.append(h + '_lat')
            normalized_headers.append(h + '_lon')
        else:
            normalized_headers.append(h)
    normalized_headers.extend(set(expected_columns) - 
                              set(normalized_headers))
    return normalized_headers


# @profile
def format_row_datetime(row, dt_columns, tz=None):
    """
    Format the datetimes in a row by column name to UTC. If a tzinfo
    is not given, the timezone will be autodetected from the timestamp. 
    If timestamps are already localized to a naive datetime within the
    source data, a tzinfo object must be provided.
    """
    for col in dt_columns:
        local_dt = row.pop(col)
        col_utc = col + '_UTC'
        if tz:
            if local_dt:
                try:
                    row[col_utc] = (tz.localize(ciso8601.parse_datetime(local_dt))
                                                        .astimezone(pytz.utc)
                                                        .replace(tzinfo=None))
                except ValueError:
                    if local_dt == '0000-00-00 00:00:00':
                        row[col_utc] = min_dt
                    else:
                        raise ValueError
            else:
                row[col_utc] = min_dt
        else:
            row[col_utc] = (ciso8601.parse_datetime(local_dt)
                                    .astimezone(pytz.utc)
                                    .replace(tzinfo=None))
    return row


def format_row_rename(row, rename_columns):
    """
    Renames all keys in column where key is present in `rename_columns`
    map.
    """
    for orig, rename in rename_columns:
        row[rename] = row.pop(orig)
    return row


def format_row_split_locations(row, location_columns):
    """
    Split a grouped location column into two cells for latitude
    and longitude.
    """
    for key in location_columns:
        location = row.pop(key)
        latitude, longitude = None, None
        if location:
            latitude, longitude = location.split(',')
        row[key + '_lat'] = latitude
        row[key + '_lon'] = longitude
    return row


# @profile
def csv_rows_to_UTC(filename, dt_columns, expected_columns, rename_columns,
                    tz=None, split_locations=False):
    """
    Changes a localized datetime to its UTC equivalent and inserts
    blank columns for expected fields when necessary.
    """
    source_csv_fn = os.path.join('./uncleaned', source_dir_name, filename)
    dest_csv_fn = os.path.join('./cleaned', source_dir_name, filename)

    source_line_count = count_lines(source_csv_fn)
    print('Total rows: {}'.format(source_line_count))

    # write new output .csv
    with open(dest_csv_fn, 'w') as out_csv_f:
        with open(source_csv_fn, 'r', encoding='utf-8-sig') as in_csv_f:
            reader = csv.DictReader(in_csv_f)
            headers = reader.fieldnames
            normalized_headers = format_headers(headers,
                                                dt_columns,
                                                expected_columns,
                                                rename_columns,
                                                split_locations)
            
            writer = csv.DictWriter(out_csv_f, fieldnames=normalized_headers)
            writer.writeheader()

            normalized = []
            write_count = 0.
            chunk_size = 50000
            location_columns = [c for c in headers if c.startswith('location')]
            for row in reader:
                row = format_row_datetime(row, dt_columns, tz)
                row = format_row_rename(row, rename_columns)
                if split_locations:
                    row = format_row_split_locations(row, location_columns)
                normalized.append(row)

                # write output in chunks and reset list
                if len(normalized) == chunk_size:
                    write_count += chunk_size
                    progress = write_count / source_line_count * 100
                    print('Processing {fn}: {pct:.1f}%'.format(fn=filename,
                                                               pct=progress))
                    writer.writerows(normalized)
                    normalized = []
            
            # write any remaining rows
            writer.writerows(normalized)


if __name__ == '__main__':
    print('Check whether source data contains tzinfo on timestamp first!')

    start = time.time()
    logging.info('Updating records to UTC for: {dir}/{fn}'.format(dir=source_dir_name,
                                                                  fn='survey_responses.csv'))
    # csv_rows_to_UTC('survey_responses.csv',
    #                 dt_columns=['created_at'],
    #                 expected_columns=['modified_at_UTC'],
    #                 rename_columns=[('version', 'itinerum_version'),
    #                                 ('osversion', 'os_version')],
    #                 tz=pytz.timezone('America/Montreal'),
    #                 split_locations=True)


    # logging.info('Updating records to UTC for: {dir}/{fn}'.format(dir=source_dir_name,
    #                                                               fn='prompt_responses.csv'))
    # csv_rows_to_UTC('prompt_responses.csv',
    #                 dt_columns=['timestamp'],
    #                 expected_columns=['prompt_uuid', 'edited_at_UTC'],
    #                 rename_columns=[('timestamp_UTC', 'displayed_at_UTC')],
    #                 tz=pytz.timezone('America/Montreal'))


    logging.info('Updating records to UTC for: {dir}/{fn}'.format(dir=source_dir_name,
                                                                  fn='coordinates.csv'))
    csv_rows_to_UTC('coordinates.csv',
                    dt_columns=['timestamp'],
                    expected_columns=[],
                    rename_columns=[],
                    tz=pytz.timezone('America/Montreal'))

    end = time.time()
    logging.info('Processing finished in {:.3f} seconds.'.format(end - start))
