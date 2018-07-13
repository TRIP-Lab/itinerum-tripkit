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


def csv_rows_to_UTC(filename, dt_columns, expected_columns, rename_columns, tz=None):
    '''
    Changes a localized datetime to its UTC equivalent and inserts blank
    columns for expected fields when necessary.
    '''
    source_csv_fn = os.path.join('./uncleaned', source_dir_name, filename)
    dest_csv_fn = os.path.join('./cleaned', source_dir_name, filename)

    source_line_count = count_lines(source_csv_fn)
    print('Total rows: {}'.format(source_line_count))

    # write new output .csv
    with open(dest_csv_fn, 'w') as out_csv_f:
        with open(source_csv_fn, 'r', encoding='utf-8-sig') as in_csv_f:
            reader = csv.DictReader(in_csv_f)
            headers = reader.fieldnames
            
            # rename any datetime columns to `datetime_UTC`
            normalized_headers = []
            rename_keys = [c[0] for c in rename_columns]
            for h in headers:
                if h in dt_columns:
                    h = h + '_UTC'
                if h in rename_keys:
                    for orig, rename in rename_columns:
                        if h == orig:
                            normalized_headers.append(rename)
                else:
                    normalized_headers.append(h)

            # add any missing columns
            normalized_headers.extend(set(expected_columns) - set(normalized_headers))
            writer = csv.DictWriter(out_csv_f, fieldnames=normalized_headers)
            writer.writeheader()

            # load datetime from string, convert to UTC format and replace as csv row entry
            normalized = []
            write_count = 0.
            chunk_size = 50000
            for row in reader:
                for col in dt_columns:
                    local_dt = row.pop(col)
                    col_utc = col + '_UTC'
                    if tz:
                        if local_dt:
                            row[col_utc] = tz.localize(ciso8601.parse_datetime(local_dt)).astimezone(pytz.utc).replace(tzinfo=None)
                        else:
                            row[col_utc] = min_dt
                    else:
                        row[col_utc] = ciso8601.parse_datetime(local_dt).astimezone(pytz.utc).replace(tzinfo=None)
                for orig, rename in rename_columns:
                    row[rename] = row.pop(orig)
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
    csv_rows_to_UTC('survey_responses.csv',
                    dt_columns=['created_at'],
                    expected_columns=['modified_at_UTC'],
                    rename_columns=[],
                    tz=pytz.timezone('America/Montreal'))


    logging.info('Updating records to UTC for: {dir}/{fn}'.format(dir=source_dir_name,
                                                                  fn='prompt_responses.csv'))
    csv_rows_to_UTC('prompt_responses.csv',
                    dt_columns=['timestamp'],
                    expected_columns=['prompt_uuid', 'edited_at_UTC'],
                    rename_columns=[('timestamp_UTC', 'displayed_at_UTC')],
                    tz=pytz.timezone('America/Montreal'))


    logging.info('Updating records to UTC for: {dir}/{fn}'.format(dir=source_dir_name,
                                                                  fn='coordinates.csv'))
    csv_rows_to_UTC('coordinates.csv',
                    dt_columns=[],
                    expected_columns=[],
                    rename_columns=[],
                    tz=pytz.timezone('America/Montreal'))

    end = time.time()
    logging.info('Processing finished in {:.3f} seconds.'.format(end - start))
