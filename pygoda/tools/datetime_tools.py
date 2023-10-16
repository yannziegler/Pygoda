# coding: utf-8
"""Handy date and time-related functions"""

# pylint: disable=invalid-name

import csv
import datetime
import os
import shutil
import time
import urllib.request

import h5py
import numpy as np

import constants as cst

MONTHS = ['JAN', 'FEB', 'MAR', 'APR',
          'MAY', 'JUN', 'JUL', 'AUG',
          'SEP', 'OCT', 'NOV', 'DEC']  # yapf: disable
DECYR_URL = 'http://geodesy.unr.edu/NGLStationPages/decyr.txt'
DECYR_FILE_TXT = os.path.join(cst.CONFIG_PATH, 'decyr.txt')
DECYR_FILE_H5 = os.path.join(cst.CONFIG_PATH, 'decyr.h5')
YMD2DECYR = dict()
DECYR2YMD = dict()
DECYR_KEYS = list()
DECYR = np.array([])
UNIX_EPOCH = np.datetime64(0, 's')
ONE_SECOND = np.timedelta64(1, 's')

def _init_decyr():
    """Download (if necessary) and load in memory the decimal year file"""

    global YMD2DECYR, DECYR2YMD, DECYR_KEYS, DECYR

    if not os.path.isfile(DECYR_FILE_TXT):
        # Download the file and save it locally
        try:
            with urllib.request.urlopen(DECYR_URL) as response, \
                 open(DECYR_FILE_TXT, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        except:
            raise FileNotFoundError('Could not download the decyr.txt file, ' \
                                    f'try to get it manually at {DECYR_URL} ' \
                                    f'and put it in {cst.CONFIG_PATH}')

    # Load the YYYYMMDD -> YYYY.YYYY association in memory
    with open(DECYR_FILE_TXT, encoding='ascii') as f:
        next(f)
        decyr_list = csv.reader(f, delimiter=' ', skipinitialspace=True)
        for row in decyr_list:
            year = "{:04d}".format(int(row[2]))
            month = "{:02d}".format(int(row[3]))
            day = "{:02d}".format(int(row[4]))
            ymd = year + month + day
            YMD2DECYR[ymd] = float(row[1])

    # Create the inverse dict, which can be useful too
    # We store decimal years as string to avoid float errors
    DECYR2YMD = {f"{v:09.4f}": k for k, v in YMD2DECYR.items()}

    # Numpy array of decimal years, useful for searching
    DECYR_KEYS = list(DECYR2YMD.keys())
    DECYR = np.float64(DECYR_KEYS)


## Decimal year to YYYYMMDD and back
#TODO: a little bit slow, need improvement later

def decyr2ymd(decyr_date, precise=True):
    """Convert from decimal year YYYY.YYYY to YYYYMMDD date string using NGL file"""

    global DECYR2YMD, DECYR_KEYS, DECYR

    if not DECYR2YMD:
        _init_decyr()

    #startt = time.time()
    #totalt = 0.0
    if isinstance(decyr_date, list) or isinstance(decyr_date, np.ndarray):
        # Skip the test to save time
        ymd_list = [""] * len(decyr_date)
        for i, date in enumerate(decyr_date):
            if precise:
                ymd_list[i] = DECYR2YMD["{:09.4f}".format(date)]
            else:
                #startt = time.time()
                # Reduce time span to just one month to save time
                skip_begin = np.int((date - DECYR[0])*365.25) - 10
                DECYR_SUB = DECYR[skip_begin:skip_begin + 20]
                match_date = np.argmin(np.abs(DECYR_SUB - date))
                match_date += skip_begin
                #match_date2 = np.abs(DECYR_SUB - date) < 0.00136
                #match_date3 = np.argmin(np.abs(DECYR - date))
                #print('DIFF', DECYR[match_date] - DECYR[match_date3])
                #totalt += time.time() - startt
                date_key = DECYR_KEYS[match_date]
                ymd_list[i] = DECYR2YMD[date_key]
        #print('DECYR2YMD time:', totalt)
        return np.asarray(ymd_list)
    else:
        str_date = "{:09.4f}".format(decyr_date)
        if precise:
            if str_date not in DECYR2YMD.keys():
                raise ValueError('The provided date is not a valid '
                                 'decimal year (computed at noon '
                                 'between 1990-01-01 and 2030-01-01).')
            return DECYR2YMD[str_date]
        else:
            match_date = np.argmin(abs(DECYR - decyr_date))
            date_key = DECYR_KEYS[match_date]
            return DECYR2YMD[date_key]


def ymd2decyr_NGL(ymd_date):
    """Convert a YYYYMMDD date string to decimal year YYYY.YYYY using NGL file"""

    global YMD2DECYR

    if not YMD2DECYR:
        _init_decyr()

    if isinstance(ymd_date, list) or isinstance(ymd_date, np.ndarray):
        # Skip the test to save time
        decyr_list = [""] * len(ymd_date)
        for i, date in enumerate(ymd_date):
            decyr_list[i] = YMD2DECYR[date]
        return np.round(np.asarray(decyr_list), 4)
    else:
        if ymd_date not in YMD2DECYR.keys():
                raise ValueError('The provided date is not a valid '
                                 'YYYYMMDD date (between 1990-01-01 '
                                 'and 2030-01-01).')

        return np.round(YMD2DECYR[ymd_date], 4)

def ymd2decyr(ymd_date):
    """Convert a YYYYMMDD date string to decimal year YYYY.YYYY"""

    # Beware! The 'decimal years' used in decyr.txt NGL file are not
    # 'fractional years', there is an additional correction
    # (to take leap years into account?)
    # Even if, *by definition*, each 'decimal year' date refers to
    # noon on that day (or to the entire day, but not to midnight),
    # the actual fraction is usually different.
    # Note: half a day is 0.00136... year (0.0014)
    # E.g.: 1st January 1992 at *noon* is encoded 1992.0000,
    #        not 1992.0014, which is used for 2nd January 1992 (!!)
    #       1st January 1993 at *noon* is (weirdly) 2004.0021
    #       1st January 1994 at *noon* is (correctly) 2004.0014
    #       1st January 1995 at *noon* is (weirdly) 2004.0007
    #       1st January 1996 at *noon* is again 1996.0000
    #       ...and so on, with a 4-year loop
    # That difference observed on 1st January is smoothly evolving
    # from year to year. For example, if the difference is -0.0014
    # the 1st January 1992 and +0.0007 the 1st January 1993, it is
    # about (-0.0014 + 0.0007)/2 mid-year (around end of July 1992).

    # Convert to datetime object
    year, month, day = int(ymd_date[0:4]), int(ymd_date[4:6]), int(ymd_date[6:8])
    date = datetime.datetime(year=year, month=month, day=day, hour=12)

    # Compute the fractional year
    numpy_datetime64_start = np.datetime64(year - 1970, 'Y')
    numpy_datetime64_end = np.datetime64(year - 1970 + 1, 'Y')
    numpy_datetime64 = np.datetime64(date)
    #print(numpy_datetime64_start, numpy_datetime64, numpy_datetime64_end)
    timestamp_start = (numpy_datetime64_start - UNIX_EPOCH)/ONE_SECOND
    timestamp_end = (numpy_datetime64_end - UNIX_EPOCH)/ONE_SECOND
    timestamp = (numpy_datetime64 - UNIX_EPOCH)/ONE_SECOND
    #print(timestamp_start, timestamp, timestamp_end)
    fraction = (timestamp - timestamp_start) / (timestamp_end - timestamp_start)
    #TODO: optimise, denominator is either 365 or 366 * 86400.
    #print(np.round(fraction, 4))

    # Compute the fractional to decimal year correction depending on the year
    # Errors in decimal wrt fractional are: -0.0014, +0.0021, 0.0000, -0.0007
    # (starting from a leap year and repeating ad infinitum)
    half_day = 1/(365*2) # 1/365.25 == 1/365 == 1/366 with 4 decimals
    #corrections = [-0.0014, 0.0007, 0.0000, -0.0007]
    corrections = [-half_day, 0.5*half_day, 0.0, -0.5*half_day]
    # Here is the trick, we smoothly transition from one correction to the next
    correction = corrections[year % 4]*(1 - fraction) + corrections[(year + 1) % 4]*fraction
    #print(np.round(fraction + correction, 4))

    return np.round(year + fraction + correction, 4)


## Decimal year and YYYYMMDD to Numpy datetime64

def decyr2datetime(decyr_date, precise=True):
    """Convert from decimal year YYYY.YYYY to numpy datetime64"""

    ymd_date = decyr2ymd(decyr_date, precise=precise)

    startt = time.time()
    if isinstance(ymd_date, list) or isinstance(ymd_date, np.ndarray):
        datetime_list = [""] * len(ymd_date)
        for i, date in enumerate(ymd_date):
            year, month, day = date[0:4], date[4:6], date[6:8]
            datetime_list[i] = f'{year}-{month}-{day} 12:00:00Z'
        return np.array(datetime_list, dtype='datetime64')
    else:
        year, month, day = ymd_date[0:4], ymd_date[4:6], ymd_date[6:8]
        return np.datetime64(f'{year}-{month}-{day} 12:00:00Z')

def ymd2datetime(ymd_date):
    """Convert from YYYYMMDD date string to numpy datetime64"""

    if isinstance(ymd_date, list) or isinstance(ymd_date, np.ndarray):
        datetime_list = [""] * len(ymd_date)
        for i, date in enumerate(ymd_date):
            year, month, day = date[0:4], date[4:6], date[6:8]
            datetime_list[i] = np.datetime64(f'{year}-{month}-{day} 12:00:00Z')
        return np.asarray(datetime_list)
    else:
        year, month, day = ymd_date[0:4], ymd_date[4:6], ymd_date[6:8]
        return np.datetime64(f'{year}-{month}-{day} 12:00:00Z')


## Numpy datetime64 to UNIX timestamp and back

def datetime2timestamp(numpy_datetime64, integer=False):
    """Convert a numpy datetime64 to UNIX timestamp"""

    timestamp = (numpy_datetime64 - UNIX_EPOCH)/ONE_SECOND

    if integer:
        # One second precision might be enough here
        return np.int_(np.round(timestamp))
    else:
        return timestamp


def timestamp2datetime(unix_timestamp):
    """Convert a UNIX timestamp to numpy datetime64"""

    python_datetime = datetime.datetime.utcfromtimestamp(unix_timestamp)

    return np.datetime64(python_datetime)


def timestamp2str(unix_timestamp, show_hour=True):
    """Convert a UNIX timestamp to date string"""

    date = datetime.datetime.utcfromtimestamp(unix_timestamp)

    if show_hour:
        return date.strftime("%d-%m-%Y %H:%M:%S")
    else:
        return date.strftime("%d-%m-%Y")


# Miscellaneous

def split_date(date, get_time=True, group_datetime=False):
    """Split a numpy datetime64 or timestamp to year, month, day"""

    if isinstance(date, (int, np.int32, np.int64,
                         float, np.float32, np.float64)):
        np_datetime64 = timestamp2datetime(date)
    elif isinstance(date, np.datetime64):
        np_datetime64 = date
    else:
        raise TypeError("date must be a timestamp or np.datetime64")

    years = np_datetime64.astype('datetime64[Y]').astype(int) + 1970
    months = np_datetime64.astype('datetime64[M]').astype(int) % 12 + 1
    days = (np_datetime64 - np_datetime64.astype('datetime64[M]')) # usec
    days = days.astype(float)/(1e6 * 86400) # float days
    if get_time:
        hours = (days - int(days)) * 24.
        minutes = (hours - int(hours)) * 60.
        hours = int(hours)
        seconds = (minutes - int(minutes)) * 60.
        minutes = int(minutes)
        seconds = int(seconds)
    days = int(days) + 1 # integer day

    if get_time:
        if group_datetime:
            return (years, months, days), (hours, minutes, seconds)
        else:
            return years, months, days, hours, minutes, seconds
    else:
        return years, months, days

def match_time_vectors(t_target, t_all):
    """Match two time vectors: return the indices in t_all to match t_target"""

    if t_target[0] < t_all[0]:
        raise ValueError("Target time vector cannot start " \
                         "before t_all[0] = %.4f" % (t_all[0]))
    if t_target[-1] > t_all[-1]:
        raise ValueError("Target time vector cannot end " \
                         "after t_all[-1] = %.4f" % (t_all[-1]))

    _, _, it = np.intersect1d(t_target, t_all, return_indices=True)
    assert np.all(t_target == t_all[it])

    return it


def get_all_decyr():
    """Return all the decimal year dates listed in decyr.txt"""

    if not DECYR:
        _init_decyr()

    return list(DECYR2YMD.keys())


def main():
    """Main function for demonstration"""

    ## Decimal year YYYY.YYYY to YYYY, MM, DD, HH

    # Test with a random (or not) date
    my_date = 2015.7372
    same_date = decyr2ymd(my_date)

    # invalid_date = 2015.7371
    # decyr2ymd(invalid_date) # raises an error

    print('%.4f' % my_date, '==', same_date)

    ## YYMMMDD to decimal year YYYY.YYYY

    my_date = "20160229" #'16FEB29'
    #my_date = "19921231"
    #my_date = "20220630"
    assert my_date == decyr2ymd(ymd2decyr(my_date))
    decyr_date_NGL = ymd2decyr_NGL(my_date)
    decyr_date = ymd2decyr(my_date)
    assert decyr_date_NGL == decyr_date

    # invalid_date = '15FEB29'
    # ymd2decyr(invalid_date) # raises an error

    print(my_date, '==', '%.4f' % decyr_date)


if __name__ == '__main__':
    main()
