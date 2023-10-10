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


class GlobalMassHDF5(loaders_generic.GenericHDF5):

    def __init__(self, data_desc):
        super().__init__(data_desc)

        assert self.desc['DATA_SPEC'].upper() == 'GLOBALMASS_GPS'
        assert self.desc['VERSION'] in ('1.0', '1.1')

    def _loadData(self, stalist, path):

        total_t = time.time()
        loadtime_t = 0.0
        loadother_t = 0.0

        data_dict = {sta: copy.deepcopy(self.data_schema) for sta in stalist}

        for sta in stalist:
            with h5py.File(path, 'r') as h5f:
                data = data_dict[sta]
                h5f_sta = h5f[sta]

                print("Loading %s data..." % sta)

                # Variable = 't', both for time series and profiles
                # Can be common or different for each component
                startt = time.time()
                data['t']['data'] = datetime_tools.decyr2datetime(h5f_sta[data[self.TIME]['path']][:], precise=False) # SLOW!
                data['t']['data'] = datetime_tools.datetime2timestamp(data[self.TIME]['data'])
                loadtime_t += time.time() - startt

                startt = time.time()

                # Components and associated quantities
                data = data_dict[sta]['components']
                for name, comp in data.items():
                    if name in ('t', 'corrections', 'events'):
                        continue

                    # Component itself
                    comp['data'] = h5f_sta[comp['datapath']][:]
                    if 'stdpath' in comp:
                        comp['std'] = h5f_sta[comp['stdpath']][:]
                    else:
                        comp['std'] = np.zeros(comp['data'].shape)

                    # Component-specific time vector
                    if 't' in comp:
                        comp['t']['data'] = datetime_tools.decyr2datetime(h5f_sta[comp[self.TIME]['path']][:])
                        comp['t']['data'] = datetime_tools.datetime2timestamp(comp[self.TIME]['data'])

                    # Component-specific corrections
                    for grp_name, grp_corr in comp.get('corrections', dict()).items():
                        for name, corr in grp_corr.items():
                            corr['data'] = h5f_sta[corr['path']][:]

                            if corr['apply']:
                                # Apply the correction
                                comp['data'] += corr['factor'] * corr['data']
                            else:
                                # Remove the correction
                                comp['data'] -= corr['factor'] * corr['data']

                    # Component-specific events
                    for grp_name, grp_events in comp.get('events', dict()).items():
                        for name, events in grp_events.items():
                            if events['path'] in h5f_sta:
                                tmp = datetime_tools.decyr2datetime(h5f_sta[events['path']][:], precise=False)
                                events['data'] = datetime_tools.datetime2timestamp(tmp)
                            else:
                                events['data'] = np.asarray([])

                # Common corrections
                data = data_dict[sta]['corrections']
                for grp_name, grp_corr in data.items():
                    for name, corr in grp_corr.items():
                        corr['data'] = h5f_sta[corr['path']][:]
                        for name, comp in data_dict[sta]['components'].items():
                            if name in ('t', 'corrections', 'events'):
                                continue

                            if corr['apply']:
                                # Apply the correction
                                comp['data'] += corr['factor'] * corr['data']
                            else:
                                # Remove the correction
                                comp['data'] -= corr['factor'] * corr['data']

                # Common events
                data = data_dict[sta]['events']
                for grp_name, grp_events in data.items():
                    for name, events in grp_events.items():
                        if events['path'] in h5f_sta:
                            tmp = datetime_tools.decyr2datetime(h5f_sta[events['path']][:], precise=False)
                            events['data'] = datetime_tools.datetime2timestamp(tmp)
                        else:
                            events['data'] = np.asarray([])

                loadother_t += time.time() - startt

        total_t = time.time() - total_t
        print('Loading time: {:.3f}s'.format(total_t))
        print(' time vector loading: {:.3f}s ({:.2f}%)'.format(loadtime_t, 100.*loadtime_t/total_t))
        print(' other data loading: {:.3f}s ({:.2f}%)'.format(loadother_t, 100.*loadother_t/total_t))

        return data_dict


class AnrijsNetCDF4(loaders_generic.GenericNetCDF4,
                    loaders_generic.GenericMultiLoader):

    def __init__(self, data_desc):
        super().__init__(data_desc, 'ANRIJS_TIDE_GAUGES', ('1.0', ))

    def _loadData(self, stalist, path):

        data_dict = {sta: copy.deepcopy(self.data_schema) for sta in stalist}

        for sta, ncdf in zip(stalist, path):

            data = data_dict[sta]

            with netCDF4.Dataset(ncdf, "r", format="NETCDF4") as nc4f:

                print("Loading %s data..." % sta)

                # Variable = 't', both for time series and profiles
                data['t'] = nc4f['t'][:]/365.2425

                # Events
                # data['EVENTS'] = dict()
                # for event in self.desc['EVENTS']:
                #     data['EVENTS'][event] = nc4f[event][:]

                # Corrections
                if 'CORRECTIONS' in self.desc:
                    data['CORRECTIONS'] = dict()
                    for correction in self.desc['CORRECTIONS']:
                        data['CORRECTIONS'][correction] = nc4f[correction][:]

                # Components and their uncertainties
                # data['COMPONENTS'] = dict()
                for name, comp in self.desc['COMPONENTS'].items():
                    id_ = comp.get('id', name)
                    # std = comp['std']
                    data[id_] = nc4f[name][:]
                    data['std' + id_] = 0*data[id_] #nc4f[std][:]

                    if 'events' in comp:
                        #TODO: create an event list per component?
                        if yaml2bool(comp.get('merge_events', False)):
                            merged_events = comp['events'][0]
                            data[merged_events] = []
                            for event in comp['events']:
                                data[merged_events] += list(data['EVENTS'][event])
                            data[merged_events].sort()
                            data[merged_events] = np.asarray(data[merged_events])
                        else:
                            for event in comp['events']:
                                data[event] = data['EVENTS'][event]

                    if 'corrections' in comp:
                        for corr_name, correction in comp['corrections'].items():
                            factor = float(correction['factor'])
                            applied = yaml2bool(correction['applied'])
                            apply = yaml2bool(correction['apply'])
                            if apply and not applied:
                                data[id_] += factor * data['CORRECTIONS'][corr_name]

                    # data['t'] = data['t'][~np.isnan(data[id_])]
                    # data[id_] = data[id_][~np.isnan(data[id_])]

                self.timeseries_dict[sta].setAttributes(data)
                self.timeseries_dict[sta].setMainComponent('original_data')

        print('%d GPS time series loaded and corrected.' % self.nsta)

        return self.timeseries_dict
