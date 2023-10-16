# coding: utf-8

import copy
import functools
import glob
import os
import pathlib
import re
import time

import numpy as np
import scipy as sp

#import netCDF4
import h5py

import constants as cst
from tools import tools
from tools import datetime_tools
from tools import yaml2bool
from . import timeseries as ts


class GenericLoader():

    def __init__(self, data_desc, file_type, data_type):

        self.desc = data_desc

        assert self.desc['FILE_TYPE'].upper() == file_type
        assert self.desc['DATA_TYPE'].upper() == data_type

        # Attributes (metadata)
        self.LONGITUDE = self.desc['MAPPING']['LONGITUDE']
        self.LATITUDE = self.desc['MAPPING']['LATITUDE']
        self.ELEVATION = self.desc['MAPPING'].get('ELEVATION', None)
        assert self.LONGITUDE in self.desc['ATTRIBUTES']
        assert self.LATITUDE in self.desc['ATTRIBUTES']
        if self.ELEVATION:
            assert self.ELEVATION in self.desc['ATTRIBUTES']

        # Variables
        self.TIME = self.desc['MAPPING']['TIME']
        # assert self.TIME in self.desc['VARIABLES'] # only if common to all

        # Float conversion for 'accuracy' parameter
        for field in (self.LONGITUDE, self.LATITUDE, self.ELEVATION):
            if not field:
                continue
            value = self.desc['ATTRIBUTES'][field].get('accuracy', 0.0)
            self.desc['ATTRIBUTES'][field]['accuracy'] = np.float(value)

    def getTimeVectorSchema(self, t, component_name=''):

        t_desc = dict()
        t_desc['name'] = t.get('name', self.TIME)
        t_desc['field'] = t.get('field', self.TIME)
        #t_desc['missing'] = t.get('missing', '')
        t_desc['format'] = t.get('format', '')
        t_desc['dt_min'] = t.get('dt_min', 0.0)
        t_desc['dt_unit'] = t.get('dt_unit', '')
        t_desc['index'] = int(t.get('index', -1)) # column in CSV-like

        if not t.get('path', ''):
            if t_desc['index'] >= 0:
                t_desc['path'] = t_desc['index']
            else:
                if component_name:
                    t_desc['path'] = component_name + '/' + t_desc['field']
                else:
                    t_desc['path'] = t_desc['field']
        else:
            t_desc['path'] = t['path']

        return t_desc

    def getCorrectionSchema(self, corrections, details, component_name=''):

        # Corrections details
        corr_details = dict()
        corr_details[''] = dict() # default group
        for name, corr in details.items():
            if 'name' in corr:
                # This is a correction
                corr_details[''][corr.get('id', name)] = corr
                corr_details[''][corr.get('id', name)]['key'] = name
            else:
                # This is actually a group of corrections
                grp_name, grp = name, corr
                corr_details[grp_name] = dict()
                for name, corr in grp.items():
                    corr_details[grp_name][corr.get('id', name)] = corr
                    corr_details[grp_name][corr.get('id', name)]['key'] = name

        # Correction description
        corr_by_group = dict()
        corr_by_group[''] = dict() # default group
        corr_desc = dict()
        corr_desc[''] = dict()
        for name, corr in corrections.items():
            if 'factor' in corr:
                # This is a correction
                corr_by_group[''][name] = corr
            else:
                # This is a group of corrections
                corr_by_group[name] = corr
                corr_desc[name] = dict()

        for grp_name, grp in corr_by_group.items():
            for name, corr in grp.items():
                corr_desc[grp_name][name] = dict()
                corr_d = corr_desc[grp_name][name] # shorthand

                if component_name:
                    corrpath = component_name + '/'
                else:
                    corrpath = ''
                corrpath += '' if not grp_name else grp_name + '/'

                corr_d['factor'] = float(corr['factor'])
                corr_d['applied']= yaml2bool(corr['applied'])
                corr_d['apply'] = yaml2bool(corr['apply'])
                if corr_d['apply']:
                    if not corr_d['applied']:
                        # We will apply the correction in any case
                        corr_d['applied'] = True
                else:
                    if corr_d['applied']:
                        # We will remove the correction in any case
                        corr_d['applied'] = False

                if grp_name in corr_details and name in corr_details[grp_name]:
                    details = corr_details[grp_name][name]
                    corr_d['name'] = details.get('name', '')
                    corr_d['comment'] = details.get('comment', '')
                    corr_d['unit'] = details.get('unit', '')
                    corr_d['path'] = details.get('path', corrpath + details['key'])
                else:
                    corr_d['path'] = corrpath + name

        return corr_desc

    def getEventSchema(self, events, details, component_name=''):

        # Events details
        events_details = dict()
        events_details[''] = dict() # default group
        for name, event in details.items():
            if 'name' in event:
                # This is a set of events_details
                events_details[''][event.get('id', name)] = event
                events_details[''][event.get('id', name)]['key'] = name
            else:
                # This is a group of events_details
                grp_name, grp = name, event
                events_details[grp_name] = dict()
                for name, event in grp.items():
                    events_details[grp_name][event.get('id', name)] = event
                    events_details[grp_name][event.get('id', name)]['key'] = name

        # Events description
        events_by_group = dict()
        events_by_group[''] = dict() # default group
        events_desc = dict()
        events_desc[''] = dict()
        if isinstance(events, list):
            # This is a set of events
            events_by_group[''] = events
        else:
            # This is a group of set of events
            for grp_name, events_set in events.items():
                events_by_group[grp_name] = events_set
                events_desc[grp_name] = dict()

        for grp_name, grp in events_by_group.items():
            for name in grp:
                events_desc[grp_name][name] = dict()
                events_d = events_desc[grp_name][name] # shorthand
                # if yaml2bool(comp.get('merge_events', False)):
                #     merged_events = comp['events'][0]
                #     data[merged_events] = []
                #     data[merged_events] += list(data['events'].get(event, []))
                #     data[merged_events].sort()
                #     data[merged_events] = np.asarray(data[merged_events])
                # else:
                if component_name:
                    eventpath = component_name + '/'
                else:
                    eventpath = ''
                eventpath += '' if not grp_name else grp_name + '/'

                if grp_name in events_details and name in events_details[grp_name]:
                    details = events_details[grp_name][name]
                    events_d['name'] = details.get('name', '')
                    events_d['comment'] = details.get('comment', '')
                    events_d['path'] = details.get('path',  eventpath + details['key'])
                else:
                    events_d['path'] = eventpath + name

        return events_desc

    def getDataSchema(self):

        print("Getting data schema...")

        # Time vector
        common_t = dict()
        if self.TIME in self.desc['VARIABLES']:
            t = self.desc['VARIABLES'][self.TIME]
            common_t = self.getTimeVectorSchema(t)

        # Components and associated quantities
        components = dict()
        id_first = ''
        for comp_name, comp in self.desc['COMPONENTS'].items():
            if comp_name[0] == '_':
                continue
            id_ = comp.get('id', comp_name)
            if not id_first:
                id_first = id_
            components[id_] = dict()
            comp_desc = components[id_] # shorthand

            # Component itself
            comp_desc['name'] = comp.get('name', comp_name)
            comp_desc['field'] = comp.get('field', comp_name)
            comp_desc['comment'] = comp.get('comment', '')
            comp_desc['unit'] = comp.get('unit', '')
            comp_desc['accuracy'] = float(comp.get('accuracy', -1))
            try:
                comp_desc['missing'] = float(comp.get('missing', 'notafloat'))
            except ValueError:
                comp_desc['missing'] = comp.get('missing', '')
            comp_desc['index'] = int(comp.get('index', -1)) # column in CSV-like
            if not comp_desc.get('datapath', ''):
                if comp_desc['index'] >= 0:
                    comp_desc['datapath'] = comp_desc['index']
                elif 'field' in comp_desc:
                    comp_desc['datapath'] = comp_desc['field']
                else:
                    comp_desc['datapath'] = comp_name
            if 'std' in comp:
                std_desc = comp['std']
                if isinstance(std_desc, dict):
                    if std_index := int(std_desc.get('index', -1)):
                        comp_desc['stdpath'] = std_index
                    elif 'field' in std_desc:
                        comp_desc['stdpath'] = std_desc['field']
                else:
                    comp_desc['stdpath'] = comp['std']

            # Component-specific time vector
            if 't' in comp:
                comp_desc['t'] = self.getTimeVectorSchema(comp['t'],
                                                          comp_name)

            # Component-specific corrections
            corrections = comp.get('corrections', dict())
            details = self.desc.get('CORRECTIONS', dict())
            comp_desc['corrections'] = self.getCorrectionSchema(corrections,
                                                                details,
                                                                comp_name)

            # Component-specific events
            events = comp.get('events', dict())
            details = self.desc.get('EVENTS', dict())
            comp_desc['events'] = self.getEventSchema(events,
                                                      details,
                                                      comp_name)

        # Component-independent corrections
        corrections = self.desc['COMPONENTS'].get('_corrections', dict())
        details = self.desc.get('CORRECTIONS', dict())
        common_corrections = self.getCorrectionSchema(corrections, details)

        # Component-independent events
        events = self.desc['COMPONENTS'].get('_events', dict())
        details = self.desc.get('EVENTS', dict())
        common_events = self.getEventSchema(events, details)

        # Components general options
        comp_options = self.desc['COMPONENTS'].get('_options', dict())
        main_comp = comp_options.get('main_component', id_first)

        schema = {'t': common_t,
                  'components': components,
                  'corrections': common_corrections,
                  'events': common_events}

        self.data_schema = schema
        self.main_component = main_comp

        return self.data_schema, self.main_component

    def configureLoader(self, data_path, stalist=[], nsta_max=0):

        # Set self.stalist, self.timeseries_dict
        self.getStationList(data_path, stalist, nsta_max)
        # Set self.data_schema, self.main_component
        self.getDataSchema()

        missing_metadata = []
        for ista, sta in enumerate(self.stalist):
            if isinstance(self.path, list):
                # One path per station
                path = self.path[ista]
            else:
                path = self.path

            loc = self.getMetadata(sta, path)
            if not loc:
                missing_metadata.append(sta)
                continue

            coordinates = ts.Coordinates((loc[0], loc[1]))
            position = ts.GeographicPosition(coordinates, loc[2])

            loader = functools.partial(self.loadStationData, sta)
            self.timeseries_dict[sta] = ts.TimeSeries(sta,
                                                      position,
                                                      loader=loader)
            self.timeseries_dict[sta].setMainComponent(self.main_component)

        print('Stations with missing metadata (ignored):')
        for sta in missing_metadata:
            print(sta)
            ista = self.stalist.index(sta)
            del self.stalist[ista]
            del self.path[ista]
            del self.timeseries_dict[sta]
            self.nsta = len(self.stalist)

        return self.stalist

    def loadData(self, stalist):

        if isinstance(self.path, list):
            path = ['']*len(stalist)
            for i, sta in enumerate(stalist):
                ista = self.stalist.index(sta)
                path[i] = self.path[ista]
        else:
            path = self.path

        startt = time.time()
        data = self._loadData(stalist, path)
        endt = time.time()

        for sta in stalist:
            self.timeseries_dict[sta].setAttributes(data[sta])
            self.timeseries_dict[sta].setMainComponent(self.main_component)

        print('{:d} time series loaded in memory in {:.3f}s.'.\
              format(len(stalist), endt - startt))

        return self.timeseries_dict

    def loadAllData(self):

        data = self._loadData(self.stalist, self.path)

        for sta in self.stalist:
            self.timeseries_dict[sta].setAttributes(data[sta])
            self.timeseries_dict[sta].setMainComponent(self.main_component)

        print('%d time series loaded in memory.' % self.nsta)

        return self.timeseries_dict

    def loadStationData(self, staname):

        ista = self.stalist.index(staname)
        if isinstance(self.path, list):
            path = self.path[ista]
        else:
            path = self.path
        data = self._loadData([staname], path)

        return data[staname]

    def getStationList(self, data_path, stalist, nsta_max):

        # Defined in generic subclasses
        return list(), dict()

    def getMetadata(self, handle):

        # Defined in generic subclasses
        return list()

    def _loadData(self, infile, stalist):

        # Only method which is written by the USER
        return dict()


class GenericMultiLoader(GenericLoader):

    def __init__(self, data_desc, file_type, data_type):
        super().__init__(data_desc, file_type, data_type)

    def getStationList(self, data_path, stalist=[], nsta_max=0):

        self.path = data_path
        self.stalist = stalist
        self.nsta_max = nsta_max

        # One or several data files?
        if isinstance(self.path, str) and '*' in self.path:
            if not stalist:
                file_list = glob.glob(self.path)
                if not file_list:
                    raise ValueError("No data file found " \
                                     "with pattern %s" % self.path)
                stalist = [pathlib.Path(f).stem for f in file_list]
                #TODO: remove common prefix/suffix
            else:
                file_list = [self.path.replace('*', staname) for
                             staname in stalist]
            self.path = file_list # same order as (self.)stalist
        self.stalist = stalist

        # Not needed
        if not isinstance(self.path, list):
            self.path = [self.path]

        if nsta_max > 0:
            self.stalist = self.stalist[:min(nsta_max, len(self.stalist))]
            self.path = self.path[:min(nsta_max, len(self.stalist))]
        self.nsta = len(self.stalist)
        self.timeseries_dict = {sta: None for sta in self.stalist}

        return self.stalist, self.timeseries_dict


class GenericTextLoader(GenericLoader):

    def __init__(self, data_desc, file_type, data_type):
        super().__init__(data_desc, file_type, data_type)

        self.comment = self.desc.get('COMMENT', '#')
        self.desc['COMMENT'] = self.comment # required later
        self.header_size = int(self.desc.get('HEADER_SIZE', -1))
        self.desc['HEADER_SIZE'] = self.header_size # required later
        self.header_sep = self.desc.get('HEADER_SEP', ':')
        self.desc['HEADER_SEP'] = self.header_sep # required later
        self.column_header = yaml2bool(self.desc.get('COLUMN_HEADER', False))
        self.desc['COLUMN_HEADER'] = self.column_header # required later
        self.delimiter = self.desc.get('DELIMITER', ',')
        self.desc['DELIMITER'] = self.delimiter # required later
        self.encoding = self.desc.get('ENCODING', 'ascii')
        self.desc['ENCODING'] = self.encoding # required later

    def extractHeader(self,
                      textfile,
                      raw=False,
                      split_fields=False,
                      split_char=''):

        fsize = os.path.getsize(textfile)
        if not fsize:
            if raw:
                return ""
            if split_fields:
                return dict()
            else:
                return list()

        with open(textfile, mode='r', encoding=self.encoding) as f:
            header = []
            i = 0
            for line in f:
                line = line.rstrip().strip()
                i += 1
                if self.header_size > 0 and i > self.header_size:
                    break # end of header (size)
                if not line:
                    continue # empty line
                if line[0] != self.comment:
                    break # end of header (not a comment)
                while line and line[0] == self.comment:
                    line = line[1:].strip()
                if line:
                    header.append(line)

        if raw:
            return '\n'.join(header)

        if split_fields:
            header_dict = dict()
            if not split_char:
                split_char = self.header_sep
            for line in header:
                try:
                    field, value = line.split(split_char, 1)
                    header_dict[field.strip()] = value.strip()
                except ValueError:
                    if '' not in header_dict:
                        header_dict[''] = ''
                    header_dict[''] += '\n' + line
            return header_dict
        else:
            return header

    def getMetadata(self, sta, path):

        header = self.extractHeader(path,
                                    split_fields=True,
                                    split_char=self.header_sep)
        if not header:
            return list()

        loc = [0.0, 0.0, 0.0]
        i = 0
        for field in (self.LONGITUDE, self.LATITUDE, self.ELEVATION):
            if not field:
                continue
            field_desc = self.desc['ATTRIBUTES'][field]
            if 'infile' not in field_desc:
                # Field name must be the key
                try:
                    value = np.float(header[field])
                except KeyError:
                    raise KeyError(f"{sta:s}: unable to get '{field:s}'" \
                                   f"from the header of {path:s}")
            else:
                # We have info to access the value
                field_name = field_desc['infile']['field']
                field_regex = field_desc['infile']['regex']
                field_regex = cst.REGEX[field_regex]
                field_index = int(field_desc['infile']['index'])
                line = header[field_name]
                values = [x.group() for x in re.finditer(field_regex, line)]
                try:
                    # Decimal value already
                    value = float(values[field_index])
                except ValueError:
                    # DMS, must be converted to angle
                    value = tools.to_angle(values[field_index])

            if field == self.ELEVATION:
                ScalarType = ts.Scalar
            else:
                ScalarType = ts.Angle
            loc[i] = ScalarType(value, signed=True, **field_desc)
            i += 1

        return loc


class GenericCSV(GenericMultiLoader, GenericTextLoader):

    def __init__(self, data_desc):
        super().__init__(data_desc, 'TEXT', 'CSV')

    def getColumnsHeader(self, csvpath):
        # Get the column number and header from a CSV filepath
        with open(csvpath, mode='r', encoding=self.encoding) as f:
            for line in f:
                line = line.strip()
                if line and line[0] != self.comment:
                    # Column header or first row of data
                    break

        if self.column_header:
            headers = line.split(self.delimiter)
            n_cols = len(headers)
        else:
            values = line.split(self.delimiter)
            n_cols = len(values)
            headers = None

        return headers, n_cols

    def identifyColumns(self, headers=None, n_cols=0):
        if headers:
            n_cols = len(headers)
        index_to_comp = {i: '' for i in range(n_cols)}

        # Use the data schema to identify each column
        t = self.data_schema['t']
        if t.get('index', -1) < 0:
            t_index = self.findColumnIndex(t, 'path', headers)
            t['index'] = t_index
            t['path'] = t_index
        index_to_comp[t['index']] = (self.TIME, 'data', None)

        for comp_grp in ('components', 'corrections', 'events'):
            for comp_id, comp in self.data_schema[comp_grp].items():
                if comp_id in ('t', 'corrections', 'events', ''):
                    #TODO: handle corrections and events properly
                    continue
                if comp.get('index', -1) < 0:
                    col_index = self.findColumnIndex(comp, 'datapath', headers)
                    comp['index'] = col_index
                    comp['datapath'] = col_index
                missing_value = comp.get('missing', None)
                index_to_comp[comp['index']] = (comp_id, 'data', missing_value)
                if 'stdpath' in comp:
                    std_index = self.findColumnIndex(comp, 'stdpath', headers)
                    comp['stdpath'] = std_index
                    missing_value = comp.get('missing', None)
                    index_to_comp[comp['stdpath']] = (comp_id, 'std', missing_value)

        return index_to_comp

    def findColumnIndex(self, comp, path, headers):
        if path not in comp:
            raise ValueError(f"Unknown path/data source for component {comp['name']} in CSV file")

        comp_path = comp[path]
        if isinstance(comp_path, int):
            if comp_path >= len(headers):
                raise ValueError(f"Component {comp['name']} has an invalid column index (index:{comp_path}) in CSV file")
            else:
                return comp_path # already an index
        elif headers:
            if comp_path in headers:
                return headers.index(comp_path)
            else:
                raise ValueError(f"Component {comp['name']} (id:{comp['id']}) doesn't match any column in CSV file")
        else:
            raise ValueError(f"Unable to identify column in CSV file for component {comp['name']} (id:{comp['id']})")


class GenericHDF5(GenericLoader):

    def __init__(self, data_desc):
        super().__init__(data_desc, 'BINARY', 'HDF5')

    def getStationList(self, data_path, stalist=[], nsta_max=0):

        self.path = data_path
        self.nsta_max = nsta_max

        with h5py.File(self.path, 'r') as h5f:

            # Load basic information for all the stations that we want
            if not stalist:
                stalist = list(h5f.keys())
            self.stalist = stalist

            # Limit the list if required before loading everything
            if nsta_max:
                self.stalist = self.stalist[:min(nsta_max, len(self.stalist))]
            self.nsta = len(self.stalist)

            self.timeseries_dict = {sta: None for sta in self.stalist}

        return self.stalist, self.timeseries_dict

    def getMetadata(self, sta, path):

        loc = [0.0, 0.0, 0.0]
        i = 0
        with h5py.File(path, 'r') as h5f:
            for field in (self.LONGITUDE, self.LATITUDE, self.ELEVATION):
                if not field:
                    continue
                field_desc = self.desc['ATTRIBUTES'][field]
                if field == self.ELEVATION:
                    ScalarType = ts.Scalar
                else:
                    ScalarType = ts.Angle
                loc[i] = ScalarType(h5f[sta].attrs[field],
                                    signed=True,
                                    **field_desc)
                i += 1

        return loc


class GenericNetCDF4(GenericLoader):

    def __init__(self, data_desc):
        super().__init__(data_desc, 'BINARY', 'NETCDF4')

    def getMetadata(self, sta, path):

        loc = [0.0, 0.0, 0.0]
        i = 0
        with netCDF4.Dataset(path, "r", format="NETCDF4") as nc4f:
            for field in (self.LONGITUDE, self.LATITUDE, self.ELEVATION):
                if not field:
                    continue
                field_desc = self.desc['ATTRIBUTES'][field]
                if field == self.ELEVATION:
                    ScalarType = ts.Scalar
                else:
                    ScalarType = ts.Angle
                loc[i] = ScalarType(nc4f.attrs[field],
                                  signed=True,
                                  **field_desc)
                i += 1

        return loc
