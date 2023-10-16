# coding: utf-8

import copy
import datetime
import os
# from dataclasses import dataclass

import numpy as np

import constants as cst
import config as cfg
from tools import tools

class Scalar(float):

    def __new__(cls, value, *args, **kwargs):
       return super().__new__(cls, value)

    def __init__(self,
                 value,
                 name='',
                 unit='',
                 signed=False,
                 accuracy=None,
                 digits=None,
                 decimals=None,
                 exp_threshold_max=1.e5,
                 exp_threshold_min=1.e-3,
                 **kwargs):
        float.__init__(value)

        self.name = name
        self.unit = unit

        if np.isnan(value):
            return

        self.signed = signed
        self.exp_threshold_max = exp_threshold_max
        self.exp_threshold_min = exp_threshold_min
        self.ignore_decimals = False

        if value == 0.0:
            # Will show 0.0
            self.digits = 2
            self.accuracy = 0.1
            self.decimals = 1
            return

        if accuracy is not None and digits is not None:
            raise ValueError("You cannot set both the accuracy and the " \
                             "number of significant digits in a Scalar.")

        if accuracy == 0.0:
            accuracy = None
            raise ValueError("Accuracy was ignored because it cannot be set " \
                             "to 0 in a Scalar, did you mean 10^0 (= 1.0)?")

        if accuracy is not None and accuracy > np.abs(value):
            # Accuracy is bigger than the number itself, just ignore it
            accuracy = None

        # Accuracy given as a power of ten
        #  e.g. 123.456 with accuracy of 1e-2 becomes '123.45'
        #         0.012 with accuracy of 1e-4 becomes '0.0120'.
        #       -47.098 with accuracy of  10  becomes '-50'.
        self.accuracy = accuracy

        # Number of significant digits, excluding leading 0.s
        #  e.g. 123.456 with 5 digits becomes '123.45'
        #         0.012 with 3 digits becomes '0.0120'.
        #       -47.098 with 1 digit becomes '-50'.
        self.digits = digits

        # Number of decimals, excluding leading 0's
        #  e.g. 123.456 with 2 decimals becomes '123.45'
        #         0.012 with 4 decimals becomes '0.0120'.
        #       -47.098 with 0 decimal  becomes '-50'.
        # If the number of digits is set, self.decimals is ignored:
        #  e.g. 12.34 with 3 significant digits and 2 decimals becomes '12.3'.
        # If the accuracy is set, self.decimals may result in trailing 0's:
        #  e.g. 12.34 with accuracy of 1e-1 and 2 decimals becomes '12.30'.
        self.decimals = decimals

        if self.accuracy is None and \
           self.digits is None and \
           self.decimals is None:
            return

        # Order of magnitude with a twist, handy to know (see below)
        mag = int(np.ceil(np.log10(np.abs(value))))
        if self.accuracy is not None and self.digits is None:
            # Compute number of significant digits from accuracy
            mag_acc = int(np.round(np.log10(self.accuracy)))
            if mag >= 0:
                self.digits = mag - mag_acc
            else:
                # We compute the number of decimals first, it's helpful
                decimals = -mag_acc if self.accuracy < 1.0 else 0
                # decimals += np.abs(mag) if np.abs(value) < 1.0 else 0
                self.digits = decimals + 1 # decimals + leading 0
            self.ignore_decimals = False
        elif self.digits is not None and self.accuracy is None:
            # Compute accuracy from number of significant digits
            self.accuracy = np.power(10., mag - self.digits)
            # Ignore decimals if number of significant digits is specified
            self.ignore_decimals = True

        if self.decimals is None and \
           self.accuracy is not None and \
           not self.ignore_decimals:
            # Compute number of decimals from accuracy
            if self.accuracy < 1.0:
                self.decimals = -int(np.round(np.log10(self.accuracy)))
            else:
                self.decimals = 0

        if self.decimals is not None and \
           self.accuracy is None and \
           np.abs(value) < 1.0:
            # Number of decimals was provided directly,
            # we need to add the trailing 0's
            self.decimals += np.abs(mag)

        if self.decimals is not None and \
             self.accuracy is None and \
             self.digits is None:
            # Compute accuracy and number of significant digits from number of
            # decimals, but only if neither the accuracy nor the number of
            # significant digits were set.
            self.accuracy = np.power(10., -self.decimals)
            if mag >= 0:
                self.digits = mag - int(np.round(np.log10(self.accuracy)))
            else:
                self.digits = self.decimals + 1 # decimals + leading 0


    def __repr__(self):


        if np.isnan(self):
            return 'NaN'

        sign = '+' if self.signed else ''
        unit = ' ' + self.unit if self.unit else ''

        if self.digits is not None:
            p = self.digits # precision
            if self.decimals is not None and not self.ignore_decimals:
                str_val = f'{{:{sign}.{self.decimals}f}}'.format(self)
            else:
                # See documentation for g formatter
                if self.digits <= 6:
                    significant_val = float(f'{{:.{p}g}}'.format(self))
                    str_val = f'{{:{sign}g}}'.format(significant_val)
                else:
                    significant_val = float(f'{{:.{p}g}}'.format(self))
                    str_val = f'{{:{sign}.{p}g}}'.format(significant_val)
        else:
            if self.exp_threshold_min < np.abs(self) < self.exp_threshold_max:
                formatter = 'G'
            else:
                formatter = 'e'
            str_val = f'{{:{sign:s}{formatter:s}}}'.format(self)

        return str_val + unit # + str(self.accuracy) + ' ' + str(self.decimals)


class Date(Scalar):

    def __new__(cls, value, *args, **kwargs):
        return super().__new__(cls, value)

    def __init__(self,
                 value,
                 date_fmt="%d-%m-%Y",
                 time_fmt="%H:%M:%S",
                 show_time=True,
                 **kwargs):
        Scalar.__init__(self, value, unit='sec', signed=False, **kwargs)

        self.date_fmt = date_fmt
        self.time_fmt = time_fmt
        self.show_time = show_time

    def __repr__(self):

        if np.isnan(self):
            return ''

        date = datetime.datetime.utcfromtimestamp(int(np.round(self)))

        fmt = self.date_fmt
        if self.show_time:
            fmt += " " + self.time_fmt

        return date.strftime(fmt)


class Duration(Scalar):

    def __new__(cls, value, unit='sec', to_day=True, *args, **kwargs):
        if unit == 'sec' and to_day:
            return super().__new__(cls, value / 86400.)
        else:
            return super().__new__(cls, value)

    def __init__(self,
                 value,
                 unit='sec',
                 time_fmt="%H:%M:%S",
                 show_time=False,
                 to_day=True,
                 **kwargs):
        Scalar.__init__(self, value, unit=unit, **kwargs)
        if unit == 'sec' and to_day:
            self.unit = 'day'
            #TODO: check consistency with decimals and digits
            if self.accuracy is not None:
                self.accuracy /= 86400.
                # self.digits = int(np.ceil(-np.log10(self.accuracy)))
                # if np.abs(value) >= 1.0:
                #     self.digits += int(np.ceil(np.log10(np.abs(value))))

        self.time_fmt = time_fmt
        self.show_time = show_time


class Angle(Scalar):

    def __new__(cls, value, unit='deg', to_degree=True, *args, **kwargs):
        if unit == 'rad' and to_degree:
            return super().__new__(cls, value * 180./np.pi,)
        else:
            return super().__new__(cls, value)

    def __init__(self,
                 value,
                 unit='deg',
                 signed=False,
                 dms=True,
                 to_degree=True,
                 lonlat='',
                 **kwargs):
        Scalar.__init__(self, value, unit=unit, signed=signed, **kwargs)
        if unit == 'rad' and to_degree:
            self.unit = 'deg'
            #TODO: check consistency with decimals and digits
            if self.accuracy is not None:
                self.accuracy *= 180./np.pi
                # self.digits = int(np.ceil(-np.log10(self.accuracy)))
                # if np.abs(value) >= 1.0:
                #     self.digits += int(np.ceil(np.log10(np.abs(value))))

        assert self.unit in ('deg', 'rad')
        self.dms = dms
        self.lonlat = lonlat

    def __repr__(self):

        if self.dms:
            decimals = self.decimals if self.decimals is not None else 0
            return tools.to_dms(self,
                                plus_sign=self.signed,
                                lonlat=self.lonlat,
                                leading_zero=False,
                                decimals=decimals,
                                encoding='utf8')
        else:
            super().__repr__(self)


class Coordinates(tuple):

    def __init__(self, lonlat):
        tuple.__init__(self)

        self.lon: Angle = lonlat[0]
        self.lat: Angle = lonlat[1]
        assert self.lon.unit == self.lat.unit
        self.unit = self.lon.unit # == lat.unit


class GeographicPosition():

    def __init__(self, coordinates, elevation=None):

        self.coord: Coordinates = coordinates
        self.lon: Angle = self.coord.lon # shortcut
        self.lat: Angle = self.coord.lat # shortcut
        self.elevation: Scalar = elevation

    def distanceTo(self, position):
        if self.coord.unit == 'deg':
            lam_1, phi_1 = np.radians((self.lon, self.lat))
        if position.coord.unit == 'deg':
            lam_2, phi_2 = np.radians(position)
        h = (np.sin(.5*(phi_2 - phi_1))**2
             + np.cos(phi_1) * np.cos(phi_2) * np.sin(.5*(lam_2 - lam_1))**2)
        return 2 * 6371 * np.arcsin(np.sqrt(h))


class TimeVector(np.ndarray):

    # From https://numpy.org/doc/stable/user/basics.subclassing.html
    def __new__(cls,
                input_array,
                name='',
                missing='',
                fmt='',
                dt_min=0.0,
                dt_unit='',
                **kwargs):
        # Input array is an already formed ndarray instance
        # We first cast to be our class type
        obj = np.asarray(input_array).view(cls)
        # add the new attribute to the created instance
        obj.name = name
        obj.missing = missing
        obj.fmt = fmt
        obj.dt_min = dt_min
        obj.dt_unit = dt_unit
        # Finally, we must return the newly created object:
        return obj

    def __array_finalize__(self, obj):
        # see InfoArray.__array_finalize__ for comments
        if obj is None: return
        self.name = getattr(obj, 'name', '')
        self.missing = getattr(obj, 'missing', '')
        self.fmt = getattr(obj, 'fmt', '')
        self.dt_min = getattr(obj, 'dt_min', 0.0)
        self.dt_unit = getattr(obj, 'dt_unit', '')


class TSComponent(np.ndarray):

    # From https://numpy.org/doc/stable/user/basics.subclassing.html
    def __new__(cls,
                input_array,
                std=0.0,
                name='',
                unit='',
                accuracy=-1,
                **kwargs):
        # Input array is an already formed ndarray instance
        # We first cast to be our class type
        obj = np.asarray(input_array).view(cls)
        # Add the new attributes to the created instance
        obj.std = std
        obj.name = name
        obj.unit = unit
        obj.accuracy = float(accuracy)
        obj.ndigits = -1 if accuracy == -1 else int(np.ceil(-np.log10(obj.accuracy)))
        # Specific to corrections
        obj.correction_factor = kwargs.get('factor', -1.)
        obj.correction_applied = kwargs.get('applied', False)

        # Finally, we must return the newly created object:
        return obj

    def __array_finalize__(self, obj):
        # see InfoArray.__array_finalize__ for comments
        if obj is None: return
        # print('obj', type(obj))
        # if not isinstance(obj, TSComponent): return

        self.std = getattr(obj, 'std', 0.0)
        self.name = getattr(obj, 'name', '')
        self.unit = getattr(obj, 'unit', '')
        self.accuracy = getattr(obj, 'accuracy', -1)
        self.ndigits = getattr(obj, 'ndigits', -1)
        # Specific to corrections
        self.correction_factor = getattr(obj, 'correction_factor', -1.)
        self.correction_applied = getattr(obj, 'correction_applied', False)


# @dataclass(frozen=True)
class TimeSeries():

    def __init__(self, name, position, loader=None, **attrs):

        self.name = name
        self.setPosition(position)
        self.t = np.asarray([])

        self.loader = loader

        self.main_component = ''
        self.components = dict()
        self.n_components = 0

        self.corrections = dict()
        self.n_corrections = 0
        self.pending_corrections = dict()

        self.events = dict()
        self.all_events = np.asarray([])
        self.n_events = 0

        self.data = np.asarray([])
        self.std_data = np.asarray([])

        if attrs:
            self.setAttributes(**attrs)

    @property
    def t(self):
        if not len(self.__t):
            self.loadData()
        return self.__t

    @t.setter
    def t(self, t):
        self.__t = t

    @property
    def data(self):
        if not len(self.__data):
            self.loadData()
        return self.__data

    @data.setter
    def data(self, data):
        self.__data = data

    @property
    def std_data(self):
        if not len(self.__data):
            self.loadData()
        return self.__std_data

    @std_data.setter
    def std_data(self, std_data):
        self.__std_data = std_data

    def loadData(self):
        attrs = self.loader()
        self.setAttributes(attrs)
        # self.setMainComponent(main_comp)
        self.__data = getattr(self, self.main_component)
        self.__std_data = self.__data.std
        if self.pending_corrections:
            self.applyCorrections(self.pending_corrections)

    def isLoaded(self):
        return True if len(self.__t) else False

    def setPosition(self, position):

        self.position = position
        self.lon = self.position.lon
        self.lat = self.position.lat
        self.h = self.position.elevation

    def setAttributes(self, attrs):

        if 't' in attrs:
            t_attrs = attrs['t']
            self.t = TimeVector(attrs['t']['data'], **t_attrs)

        # Components specific
        for name, comp in attrs.get('components', dict()).items():
            setattr(self, name, TSComponent(comp['data'], **comp))
            new_comp = getattr(self, name)
            # Sometimes it's convenient to access the components through a dict:
            self.components[name] = new_comp
            if 't' in comp:
                t_attrs = comp['t']
                setattr(new_comp, 't',
                        TimeVector(comp['t']['data'], **t_attrs))
            new_comp.corrections = dict()
            for grp_name, grp_corr in comp.get('corrections', dict()).items():
                new_comp.corrections[grp_name] = dict()
                for corr_name, corr in grp_corr.items():
                    new_comp.corrections[grp_name][corr_name] = TSComponent(corr['data'], **corr)
            new_comp.events = dict()
            for grp_name, grp_events in comp.get('events', dict()).items():
                new_comp.events[grp_name] = dict()
                for events_name, events in grp_events.items():
                    data = events.get('data', [])
                    new_comp.events[grp_name][events_name] = TimeVector(data, **events)
                    self.n_events += len(data)
        self.n_components = len(self.components)
        # For testing
        #name = 'fake'
        #setattr(self, name, TSComponent(np.log(np.abs(comp['data'])), **comp))
        #new_comp = getattr(self, name)
        #self.components[name] = new_comp
        #self.n_components += 1

        # Common
        for grp_name, grp_corr in attrs.get('corrections', dict()).items():
            for corr_name, corr in grp_corr.items():
                self.corrections[corr_name] = TSComponent(corr['data'], **corr)
        self.n_corrections = len(self.corrections)

        for grp_name, grp_events in attrs.get('events', dict()).items():
            for events_name, events in grp_events.items():
                data = events.get('data', [])
                self.events[events_name] = TimeVector(data, **events)
                self.all_events = list(self.events[events_name]) + list(self.all_events)
                self.all_events.sort()
                self.all_events = np.asarray(self.all_events)
        self.n_events += len(self.all_events)

        for k, v in attrs.items():
            if k in ('t', 'components', 'corrections', 'events'):
                continue
            setattr(self, k, v)

    def setMainComponent(self, target):

        # if target not in self.components.keys():
        #     raise ValueError("%s is not a component of this TimeSeries instance" % target)
        # self.data = getattr(self.__dict__['components'], target)
        self.main_component = target
        try:
            self.__data = getattr(self, self.main_component)
            self.__std_data = self.__data.std
        except AttributeError:
            # Will be done when loading the data (by loadData)
            pass
        #TODO: see what to do with time vectors


    def applyCorrections(self, corrections, component=''):

        if not component:
            component = self.main_component

        try:
            comp = getattr(self, component)
            self.pending_corrections = dict()
        except AttributeError:
            # Will be done when loading the data (by loadData)
            self.pending_corrections = copy.deepcopy(corrections)
            return

        # Component-independent corrections
        for grp_name, grp_corr in getattr(self, 'corrections', {}).items():
            if grp_name not in corrections:
                continue
            for corr_name, corr in grp_corr.items():
                if corr_name in corrections[grp_name] and not corr.correction_applied:
                    comp += corr.correction_factor * corr
                    corr.correction_applied = True
                elif corr_name not in corrections[grp_name] and corr.correction_applied:
                    comp -= corr.correction_factor * corr
                    corr.correction_applied = False

        # Component-specific corrections
        for grp_name, grp_corr in comp.corrections.items():
            if grp_name not in corrections:
                continue
            for corr_name, corr in grp_corr.items():
                if corr_name in corrections[grp_name] and not corr.correction_applied:
                    comp += corr.correction_factor * corr
                    corr.correction_applied = True
                elif corr_name not in corrections[grp_name] and corr.correction_applied:
                    comp -= corr.correction_factor * corr
                    corr.correction_applied = False


if __name__ == '__main__':

    # Comment out Pygoda imports to use this

    N = [1234, 0.12, 0.00012, 6253, 1999, -3.14, 0., -48.01, 0.75, 123456.789]

    N1 = [Scalar(n, accuracy=1e-2) for n in N]
    N2 = [Scalar(n, decimals=2) for n in N]
    N3 = [Scalar(n, digits=3) for n in N]
    N4 = [Scalar(n, digits=10) for n in N]
    for Nx in [N1, N2, N3, N4]:
        print('NEXT SET:')
        for i, n in enumerate(Nx):
            print(f' {N[i]} = {n}')
            print('  accuracy:', n.accuracy)
            print('  digits:', n.digits)
            print('  decimals:', n.decimals)
            print('  ignore_decimals:', n.ignore_decimals)
        print('')
