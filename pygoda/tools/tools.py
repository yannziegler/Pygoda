# coding: utf-8
"""Some handy generic functions used in other scripts"""

import re

import numpy as np

import constants as cst

def yaml2bool(bool_str):
    return True if bool_str.lower() in ('1', 'true') else False


def sizeof_humanize(num, suffix='B'):
    """Convert a size in Bytes to human readable binary format"""

    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi']:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Ei{suffix}"


def to_angle(text, from_rad=False, from_colat=False, east_only=False):
    """Check and convert DMS to decimal angle"""

    text = text.strip().replace(' ', '')

    if text[-1] in 'NSWOE':
        match = [x.group() for x in re.finditer(cst.REGEX['DMS_NSWE'], text)]
        sign = 1. if text[-1] in 'NE' else -1.
    else:
        match = [x.group() for x in re.finditer(cst.REGEX['DMS'], text)]
        sign = 1. if text[0] != '-' else -1.

    if not match:
        #raise TextError(f"{text:s} is not a valid DMS string")
        angle = [x.group() for x in re.finditer(cst.REGEX['DECIMAL_UI'], text)]
        angle = sign * np.float(angle)
        if from_rad:
            angle *= 180./np.pi
        if from_colat:
            angle = 90. - angle
    else:
        dms_str = [x.group() for x in re.finditer(cst.REGEX['DECIMAL_UI'], text)]
        dms = [np.float(v) for v in dms_str]
        angle = sign * (dms[0] + dms[1] / 60. + dms[2] / 3600.)

    if angle < 0. and east_only and not from_colat:
        #TODO: beware, wrong behaviour with latitudes!
        angle += 360.

    return angle

def to_dms(angle,
           plus_sign=True,
           lonlat='',
           leading_zero=True,
           decimals=0,
           encoding='utf8'):
    """Convert an angle to degree, minute, second"""

    if angle >= 0.0:
        sign = '+' if plus_sign else ''
    else:
        sign = '-'

    if lonlat:
        sign = ''
        if 'lon' in lonlat.lower():
            suffix = 'E' if angle >= 0.0 else 'W'
        elif 'lat' in lonlat.lower():
            suffix = 'N' if angle >= 0.0 else 'S'
        else:
            raise ValueError("lonlat must be 'lon' or 'lat'")
    else:
        suffix = ''

    angle = np.abs(angle)
    degree = np.floor(angle)
    angle -= degree
    minute = np.floor(60. * angle)
    angle -= minute / 60.
    second = 3600. * angle

    degfmt = "03.0" if leading_zero else ".0"
    secfmt = "02.0" if decimals <= 0 else f"0{decimals + 3:d}.{decimals:d}"

    if encoding.lower() in ('utf8', 'utf-8'):
        return f"{sign:s}{degree:{degfmt:s}f}°{minute:02.0f}′" \
               f"{second:{secfmt:s}f}″{suffix:s}"
    else:
        if encoding.lower() in ('iso-8859-1', 'latin-1'):
            deg_symb = b'\xb0'.decode('iso-8859-1')
        elif encoding.lower() == 'ascii':
            deg_symb = 'd'
        return f"{sign:s}{degree:{degfmt:s}f}{deg_symb:s}{minute:02.0f}'" \
               f"{second:{secfmt:s}f}\"{suffix:s}"

def middle_ellipsis(s, n):
    """Shorten a string with a middle ellipsis"""
    if len(s) <= n:
        return s

    n_end = int(n)//2 - 3
    n_start = n - n_end - 3

    return '{0}...{1}'.format(s[:n_start], s[-n_end:])
