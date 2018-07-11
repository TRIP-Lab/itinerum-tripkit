#!/usr/bin/env python
# Kyle Fitzsimmons, 2018
import csv
import ciso8601
import logging
import os
import pytz
import time

# config
source_dir_name = 'cfsm-responses-2016'
output_dir = os.path.join('./cleaned', source_dir_name)

# init--create the new output dir and setup logging
if not os.path.exists(output_dir):
    os.mkdir(output_dir)
logging.basicConfig(level=logging.INFO)


def csv_rows_to_UTC(filename, dt_columns, expected_columns, rename_columns, tz=None):
    '''
    Changes a localized datetime to its UTC equivalent and inserts blank
    columns for expected fields when necessary.
    '''
    source_csv_fn = os.path.join('./uncleaned', source_dir_name, filename)
    normalized = []
    normalized_headers = []
    with open(source_csv_fn, 'r', encoding='utf-8-sig') as csv_f:
        reader = csv.DictReader(csv_f)
        headers = reader.fieldnames
        
        # rename any datetime columns to `datetime_UTC`
        rename_keys = [c[0] for c in rename_columns]
        for h in headers:
            if h in dt_columns:
                normalized_headers.append(h + '_UTC')
            elif h in rename_keys:
                for orig, rename in rename_columns:
                    if h == orig:
                        normalized_headers.append(rename)
            else:
                normalized_headers.append(h)

        # add any missing columns
        normalized_headers.extend(set(expected_columns) - set(normalized_headers))


        # load datetime from string, convert to UTC format and replace as csv row entry
        for row in reader:
            for col in dt_columns:
                local_dt = row.pop(col)
                col_utc = col + '_UTC'
                if tz:
                    ciso8601.parse_datetime(local_dt, tzinfo=tz).astimezone(pytz.utc).replace(tzinfo=None)
                else:
                    row[col_utc] = ciso8601.parse_datetime(local_dt).astimezone(pytz.utc).replace(tzinfo=None)
            for orig, rename in rename_columns:
                row[rename] = row.pop(orig)
            normalized.append(row)

    # write new output .csv
    dest_csv_fn = os.path.join('./cleaned', source_dir_name, filename)
    with open(dest_csv_fn, 'w') as csv_f:
        writer = csv.DictWriter(csv_f, fieldnames=normalized_headers)
        writer.writeheader()
        writer.writerows(normalized)


if __name__ == '__main__':
    print('Check whether source data contains tzinfo on timestamp first!')

    start = time.time()
    logging.info('Updating records to UTC for: {dir}/{fn}'.format(dir=source_dir_name,
                                                                  fn='survey_responses.csv'))
    csv_rows_to_UTC('survey_responses.csv',
                    dt_columns=['created_at'],
                    expected_columns=['modified_at_UTC'],
                    rename_columns=[])


    logging.info('Updating records to UTC for: {dir}/{fn}'.format(dir=source_dir_name,
                                                                  fn='prompt_responses.csv'))
    csv_rows_to_UTC('prompt_responses.csv',
                    dt_columns=['displayed_at', 'recorded_at'],
                    expected_columns=['prompt_uuid', 'edited_at_UTC'],
                    rename_columns=[])


    logging.info('Updating records to UTC for: {dir}/{fn}'.format(dir=source_dir_name,
                                                                  fn='coordinates.csv'))
    csv_rows_to_UTC('coordinates.csv',
                    dt_columns=['timestamp'],
                    expected_columns=[],
                    rename_columns=[])

    end = time.time()
    logging.info('Processing finished in {:.3f} seconds.'.format(end - start))
