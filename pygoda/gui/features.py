# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import os, copy, functools

import numpy as np

import constants as cst
import config as cfg
from . import features_plots as feat_plot
from . import features_widgets as feat_widgets


class FeaturesPlotPanel(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self, feat_id1=cfg.sort_by, feat_id2=None, multi=False):
        QtWidgets.QWidget.__init__(self)

        self.overrideWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle('Features plot')

        self.id = id(self) # used to 'sign' signals

        self.ithreshold = None
        self.feat_id1 = feat_id1
        self.selected_sta = None

        self.layout = QtWidgets.QVBoxLayout()
        self.top_layout = QtWidgets.QHBoxLayout()
        self.bottom_layout = QtWidgets.QHBoxLayout()

        if not multi:
            self.feature_plot = feat_plot.SingleFeaturePlot(xaxis='percent',
                                                       threshold_sig=self.changeThreshold)

            self.feature1 = feat_widgets.FeaturesMenu('Select feature', exclude_names=True)
            self.feature1_button = self.feature1.getButton()
            self.feature1_actions = self.feature1.getQActions()
            for feat_id in self.feature1_actions.keys():
                select_feature = functools.partial(self.selectFeature, feat_id, 'x-axis')
                self.feature1_actions[feat_id].triggered.connect(select_feature)
            self.top_layout.addWidget(self.feature1_button)

            self.sort_order = QtWidgets.QCheckBox("Decreasing order")
            self.sort_order.setCheckState(QtCore.Qt.Unchecked)
            self.sort_order.stateChanged.connect(self.sortOrder)
            self.top_layout.addWidget(self.sort_order)

            self.show_most_stations = QtWidgets.QPushButton("Show 99%")
            self.show_most_stations.clicked.connect(self.showMostStations)
            self.top_layout.addWidget(self.show_most_stations)

            self.goto_station = QtWidgets.QPushButton("Goto station")
            self.goto_station.clicked.connect(self.gotoStation)
            self.top_layout.addWidget(self.goto_station)
        else:
            self.feature1 = FeaturesMenu('Select X-axis feature', exclude_names=True)
            self.feature1_button = self.feature1.getButton()
            self.feature1_actions = self.feature1.getQActions()
            for feat_id in self.feature1_actions.keys():
                select_feature = functools.partial(self.selectFeature, feat_id, 'x-axis')
                self.feature1_actions[feat_id].triggered.connect(select_feature)
            self.top_layout.addWidget(self.feature1_button)

            self.top_layout.addWidget(self.feature1)
            self.feature2 = FeaturesMenu('Select Y-axis feature', exclude_names=True)
            self.feature2_button = self.feature2.getButton()
            self.feature2_actions = self.feature2.getQActions()
            for feat_id in self.feature2_actions.keys():
                select_feature = functools.partial(self.selectFeature, feat_id, 'y-axis')
                self.feature2_actions[feat_id].triggered.connect(select_feature)
            self.top_layout.addWidget(self.feature2_button)

        features_desc = self.feature1.getFeaturesDesc()
        self.features_names = features_desc['FEATURES']

        self.layout.addLayout(self.top_layout)
        self.layout.addWidget(self.feature_plot)

        self.filter_below = QtWidgets.QPushButton("Filter out < threshold")
        self.filter_below.clicked.connect(functools.partial(self.filterWithThreshold, -1))
        self.bottom_layout.addWidget(self.filter_below)
        self.reset_filter = QtWidgets.QPushButton("Reset filter")
        self.reset_filter.clicked.connect(functools.partial(self.filterWithThreshold, 0))
        self.bottom_layout.addWidget(self.reset_filter)
        self.filter_above = QtWidgets.QPushButton("Filter out >= threshold")
        self.filter_above.clicked.connect(functools.partial(self.filterWithThreshold, 1))
        self.bottom_layout.addWidget(self.filter_above)
        self.layout.addLayout(self.bottom_layout)

        if feat_id1 and feat_id1[0] != '.':
            self.selectFeature(feat_id1, 'x-axis')

        self.setLayout(self.layout)

    def selectFeature(self, feat_id, axis):
        self.feat_id1 = feat_id
        reversed = True if self.sort_order.checkState() == QtCore.Qt.Checked else False
        sorted_sta_all = cfg.features.sortByFeature(feat_id, not reversed,
                                                return_list=False,
                                                store_result=False).copy()
        self.sorted_sta = {sta: value for sta, value in sorted_sta_all.items() if sta in cfg.stalist}

        try:
            group, feat = feat_id.split('.')
            name = self.features_names[group][feat]['desc_short']
            #name = name[0].lower() + name[1:]
            if axis == 'x-axis':
                self.feature1_button.setText(name)
        except ValueError:
            # Dealing with a model parameter
            _, model, param = feat_id.split('.')
            if axis == 'x-axis':
                self.feature1_button.setText(param + ' (model ' + model + ')')

        self.plotFeature(feat_id, axis)

    def plotFeature(self, feat_id, axis):
        # Full stalist before filtering
        # full_stalist = cfg.filter_history.get(self.id, [])
        self.feature_plot.setFeature(self.sorted_sta)

    @QtCore.Slot()
    def changeThreshold(self):
        self.ithreshold = self.feature_plot.getThresholdIndex()

        sta_events = dict()
        if self.selected_sta:
            sta_events[~cst.SELECTED] = [self.selected_sta]
        sorted_sta_list = list(self.sorted_sta.keys())
        self.selected_sta = sorted_sta_list[self.ithreshold]
        sta_events[cst.SELECTED] = [self.selected_sta]
        self.send(sta_events)

    def gotoStation(self):
        if not self.selected_sta:
            return

        sta_events = dict()
        sta_events['PLOT_REQUEST'] = self.selected_sta
        self.send(sta_events)

    def filterWithThreshold(self, side):
        stalist = list(self.sorted_sta.keys())

        if side < 0:
            # Remove stations below threshold
            # (= keep stations above (or equal to) threshold
            stalist = stalist[self.ithreshold:]
        elif side > 0:
            # Remove stations above threshold
            # (= Keep stations below threshold)
            stalist = stalist[:self.ithreshold]
        else:
            # Reset filter by sending an empty list
            stalist = []

        sorted_sta_tmp = self.sorted_sta.copy()
        if stalist:
            self.sorted_sta = {sta: value for sta, value in sorted_sta_tmp.items() if sta in stalist}
        else:
            reversed = True if self.sort_order.checkState() == QtCore.Qt.Checked else False
            sorted_sta_all = cfg.features.sortByFeature(self.feat_id1, not reversed,
                                                    return_list=False,
                                                    store_result=False).copy()
            self.sorted_sta = {sta: value for sta, value in sorted_sta_all.items() if sta in cfg.filter_history[self.id]}

        self.feature_plot.setFeature(self.sorted_sta)

        self.send({'FILTER': stalist})

    @QtCore.Slot()
    def sortOrder(self, state):
        if self.feat_id1:
            reverse = True if self.sort_order.checkState() == QtCore.Qt.Checked else False
            self.sorted_sta = cfg.features.sortByFeature(self.feat_id1, not reverse,
                                                     return_list=False,
                                                     store_result=False).copy()
            self.plotFeature(self.feat_id1, axis='x-axis')
            self.feature_plot.setTextAnchor(side=0 if reverse else 1)

    def showMostStations(self):
        values = np.asarray(list(self.sorted_sta.values()))
        if (values > 0).any():
            y_pos_max = np.quantile(values[values > 0], [0.99])[0]
        else:
            y_pos_max = np.max(values)

        if (values < 0).any():
            y_neg_max = -np.quantile(-values[values < 0], [0.99])[0]
        else:
            y_neg_max = np.min(values)

        self.feature_plot.setXYRange(y_neg_max, y_pos_max)

    def close(self):
        # For now, reset filter when closing
        self.filterWithThreshold(0)
        super().close()

    def send(self, message):
        message['FROM'] = self.id
        self.gui_to_ctrl.emit(message)
