# coding: utf-8

import copy
import functools
import glob
import pathlib
import time

import numpy as np
import netCDF4
import scipy as sp
import h5py

from tools import yaml2bool
from tools import datetime_tools
from . import timeseries as ts
from . import loaders_generic

class MultiCSV(loaders_generic.GenericCSV):

    def __init__(self, data_desc):
        super().__init__(data_desc)

        # RIVERLEVELS.UK kept for backward compatibility
        assert self.desc['DATA_SPEC'].upper() in ('RIVERLEVELS.UK', 'MULTI_CSV')
        assert self.desc['VERSION'] in ('1.0', )

    def _loadData(self, stalist, path):

        total_t = time.time()
        loadtime_t = 0.0
        loadother_t = 0.0

        data_dict = {sta: copy.deepcopy(self.data_schema) for sta in stalist}
        no_data = []

        # Get the date format (default is YYYYMMDD)
        if date_format := self.data_schema['t'].get('format', ''):
            date_format = date_format.upper()
            mm, dd = None, None
            yy = date_format.find('Y'), date_format.rfind('Y') + 1
            if 'M' in date_format:
                mm = date_format.find('M'), date_format.rfind('M') + 1
            if 'D' in date_format:
                dd = date_format.find('D'), date_format.rfind('D') + 1

        # Link components in data schema with CSV columns before reading
        csvpath = path[0]
        headers, n_cols = self.getColumnsHeader(csvpath)
        #print(n_cols, headers)

        index_to_comp = self.identifyColumns(headers)
        #print(index_to_comp)

        dtype_desc = []
        missing_values = []
        for icol, column_info in index_to_comp.items():
            comp_id, data_type, missing_value = column_info
            if comp_id == self.TIME:
                dtype_desc.append((self.TIME, '|S10'))
                missing_values.append(None)
            else:
                suffix = '_' + data_type if data_type != 'data' else ''
                dtype_desc.append((comp_id + suffix, np.float))
                missing_values.append(missing_value)
        #print(dtype_desc, missing_values)

        #for comp_name in self.data_schema['components'].keys():
        #    if comp_name in ('t', 'corrections', 'events'):
        #        continue
        #    dtype_desc.append((comp_name, np.float))

        for sta, csv in zip(stalist, path):

            data = data_dict[sta]

            csv_data = np.genfromtxt(csv,
                                     encoding=self.desc['ENCODING'],
                                     dtype=dtype_desc,
                                     delimiter=self.desc['DELIMITER'],
                                     # skip_header=1,
                                     missing_values=missing_values)
            #print(csv_data.dtype.names)

            if not csv_data.shape:
                print(f"No data for {sta:s}!")
                no_data.append(sta)
                dates = np.asarray([np.datetime64('2010-01-01 12:00:00Z'),
                                    np.datetime64('2011-01-01 12:00:00Z')])
                data['t']['data'] = datetime_tools.datetime2timestamp(dates)
                data = data_dict[sta]['components']
                for name, comp in data.items():
                    if name in ('t', 'corrections', 'events'):
                        continue
                    comp['data'] = np.asarray([0.0, 0.0])
                    comp['std'] = np.asarray([0.0, 0.0])
                continue

            if self.column_header:
                csv_data = csv_data[1:]

            print("Loading data for %s..." % sta)

            startt = time.time()
            dates = [date.decode('ascii') for date in csv_data[self.TIME]]
            if date_format:
                for i, date in enumerate(dates):
                    YY = date[yy[0]:yy[1]]
                    MM = date[mm[0]:mm[1]] if mm else '01'
                    DD = date[dd[0]:dd[1]] if dd else '01'
                    dates[i] = YY + MM + DD
            dates = [date.replace('-', '').replace('/', '') for date in dates] # for backward compatibility
            dates = datetime_tools.ymd2datetime(dates)
            data['t']['data'] = datetime_tools.datetime2timestamp(dates)
            loadtime_t += time.time() - startt

            startt = time.time()

            # Components and associated quantities
            for comp_grp in ('components', 'corrections', 'events'):
                for comp_id, comp in data[comp_grp].items():
                    if comp_id in ('t', 'corrections', 'events', ''):
                        #TODO: handle corrections and events properly
                        continue

                    # Component itself
                    comp['data'] = csv_data[comp_id][:]
                    if 'stdpath' in comp:
                        comp['std'] = csv_data[comp_id + '_std'][:]
                    else:
                        comp['std'] = np.zeros(comp['data'].shape)

            loadother_t += time.time() - startt

        # print('Summary of stations with no data (ignored):')
        # for sta in no_data:
        #     print(sta)
        #     del data_dict[sta]

        total_t = time.time() - total_t
        print('Loading time: {:.3f}s'.format(total_t))
        print(' time vector loading: {:.3f}s ({:.2f}%)'.format(loadtime_t, 100.*loadtime_t/total_t))
        print(' other data loading: {:.3f}s ({:.2f}%)'.format(loadother_t, 100.*loadother_t/total_t))

        return data_dict
