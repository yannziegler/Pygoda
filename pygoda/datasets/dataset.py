# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import copy
import numpy as np

import constants as cst
import config as cfg
from . import data_categories
from . import load_data
from . import fit_data
from . import timeseries
from . import timeseries_features

class DataSetObject(QtCore.QObject):

    data_to_gui = QtCore.Signal(dict)

    def __init__(self, data_path, data_desc, load_now=False, **kwargs):
        QtCore.QObject.__init__(self)

        self.id = id(self) # used to 'sign' signals
        self.data_path = data_path
        self.data_desc = data_desc
        self.load_params = kwargs

        self.loader = load_data.LoaderInterface(self.data_desc).getLoader()

        # Create one file per category with a list of stations belonging to the category
        self.category_db = data_categories.CategoryDB(split_category=True)

        self.sta_category = None

        if load_now:
            self.loadData()

    def loadData(self, read_categories=True,
                 load_on_the_fly=False, load_nsta=-1, **kwargs):

        #if 'stalist' in self.data_desc:
        #    self.load_params.update({'stalist': self.data_desc['stalist']})
        if load_on_the_fly and not load_nsta:
            raise ValueError("'load_nsta' must be specified if 'load_on_the_fly' is True")
        self.load_params.update(kwargs)

        stalist = self.loader.configureLoader(self.data_path, **self.load_params)
        nsta = len(stalist)

        if load_nsta > nsta:
            load_nsta = nsta

        if load_on_the_fly:
            if load_nsta == nsta:
                # More efficient
                dataset_dict = self.loader.loadAllData()
            else:
                dataset_dict = self.loader.loadData(stalist[:load_nsta])
        else:
            dataset_dict = self.loader.loadAllData()

        self.dataset = DataSet(dataset_dict)
        self.getData = self.dataset.getData
        self.hasData = self.dataset.hasData
        stalist = self.dataset.getStationsList()

        if isinstance(self.dataset[stalist[0]], timeseries.TimeSeries):
            # (1) Prepare corresponding Models objects
            self.models = dict()
            for name in fit_data.timeseries_models_names:
                self.models[name] = fit_data.timeseries_models[name](self.dataset)
            # (2) Create corresponding Features object (uses models)
            self.features = timeseries_features.TimeSeriesFeatures(self.dataset, self.models)
        # elif isinstance(self.dataset, profiles.Profiles):
        #     pass

        if read_categories:
            self.readCategories()

    def readCategories(self):

        self.sta_category = self.category_db.readCategories(self.dataset.getStationsList())

    def getCategories(self):

        if not self.sta_category:
            self.readCategories()

        return self.sta_category

    def createConfigShortcuts(self):

        # Shortcuts for CONSTANT properties

        # cfg.data = copy.deepcopy(self) # What a deep thought.
        cfg.data = self.dataset
        cfg.stalist_all = self.dataset.getStationsList()
        cfg.nsta_all = len(cfg.stalist_all)

        # Categories
        #cfg.sta_category_all = self.sta_category

        # Features
        cfg.features = self.features

        # Models
        cfg.models = self.models

    # def sortByFeature(self, feature, order):
    #     sorted_feat = {k: v for k, v in sorted(cfg.sta_features[feature].items(), key=lambda item: item[1])}
    #     sorted_feat = list(sorted_feat.keys())
    #     if not order:
    #         sorted_feat.reverse()
    #     cfg.stalist_all = sorted_feat

    #     # For now, reset the other filters
    #     cfg.stalist = cfg.stalist_all
    #     cfg.nsta = cfg.nsta_all

    @QtCore.Slot(dict)
    def updateDataset(self, sta_events):
        if 'CATEGORY_CHANGED' in sta_events:
            for staname, group, new_category in sta_events['CATEGORY_CHANGED']:
                cfg.sta_category_all[staname][group] = new_category
                cfg.sta_category[staname][group] = new_category

            self.category_db.writeAllCategories()
            self.data_to_gui.emit(sta_events)

    def send(self, message, sender=None):
        if not sender:
            sender = self.id
        message['FROM'] = sender
        self.data_to_gui.emit(message)


class DataSet(dict):

    def __init__(self, dataset):
        dict.__init__(self, dataset)

    def getStationsList(self):

        return list(self.keys())

    def getData(self, staname=None):

        if staname is None:
            return self
        else:
            if isinstance(staname, list):
                return {sta: self[sta] for sta in staname}
            else:
                return self[staname]
                
    def hasData(self, staname):

        if isinstance(staname, list):
            return {sta: self[sta].isLoaded() for sta in staname}
        else:
            return self[staname].isLoaded()
