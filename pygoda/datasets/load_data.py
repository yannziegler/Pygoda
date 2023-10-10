# coding: utf-8

import numpy as np
import scipy as sp
import h5py
import functools

from . import loaders_common
from . import loaders_custom


class LoaderInterface():

    LOADERS = {'GLOBALMASS_GPS': loaders_custom.GlobalMassHDF5,
               'RIVERLEVELS.UK': loaders_common.MultiCSV, # for backward compatibility
               'MULTI_CSV': loaders_common.MultiCSV,
               'ANRIJS_TIDE_GAUGES': loaders_custom.AnrijsNetCDF4}

    def __init__(self, data_descriptor):

        self.data_type = data_descriptor['DATA_SPEC'].upper()
        self.data_desc = data_descriptor

        self.loader = self.LOADERS[self.data_type](self.data_desc)

    def getLoader(self):

        return self.loader

    # def loadData(self, data_path, **kwargs):
    #     return self.LOADERS_FUNC[self.data_type](data_path, self.data_desc, **kwargs)
