# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import functools

import numpy as np

import constants as cst
import config as cfg
from datasets import fit_data
from datasets import timeseries_features as ts_features


class FeaturesMenu(QtWidgets.QPushButton):

    def __init__(self, text, prefix='', exclude_names=False):
        QtWidgets.QPushButton.__init__(self, text)

        self.features_desc = ts_features.load_features_desc()
        self.features_groups = self.features_desc['GROUPS']

        self.models_names = fit_data.timeseries_models_names

        if prefix:
            if prefix[-1] != ' ':
                prefix += ' '
            text = prefix + text[0].lower() + text[1:]
        self.features_button = QtWidgets.QPushButton(text)
        self.features_menu = QtWidgets.QMenu("Features", self.features_button)
        self.features_menu.setToolTipsVisible(True)

        self.features_list = []
        self.features_submenus = dict()
        self.models_submenus = dict()
        self.features_actions = dict()

        # Top-level features: DEFAULT and NAMES
        for feat_id, _, description in cfg.features.iterateFeatures(description=True, append_formula=True):
            if exclude_names or (feat_id not in ('.DEFAULT', '.NAMES')):
                break
            self.features_list.append(feat_id)
            self.features_actions[feat_id] = QtWidgets.QAction(description, self)
            self.features_menu.addAction(self.features_actions[feat_id])

        # Generic submenus
        for group, description in self.features_groups.items():
            self.features_submenus[group] = self.features_menu.addMenu(description)
            self.features_submenus[group].setToolTipsVisible(True)
        # Models submenu
        for model, description in self.models_names.items():
            model_menu = self.features_submenus['MODELS']
            self.models_submenus[model] = model_menu.addMenu(description)
            self.models_submenus[model].setToolTipsVisible(True)

        # Generic features
        for feat_id, _, description in cfg.features.iterateFeatures(description=True, append_formula=True):
            if feat_id in ('.DEFAULT', '.NAMES'):
                continue # already done above
            self.features_list.append(feat_id)
            try:
                group, feat = feat_id.split('.')
                # print(group, feat)
                self.features_actions[feat_id] = QtWidgets.QAction(description, self)
                if group:
                    # Feature in a group
                    self.features_submenus[group].addAction(self.features_actions[feat_id])
                else:
                    # Top-level feature, e.g. NAMES
                    self.features_menu.addAction(self.features_actions[feat_id])
            except ValueError:
                # Dealing with a model
                group, model, param = feat_id.split('.')
                # print(group, model, param)
                param_path = 'metaparams/' + param
                param_desc = cfg.features.models[model].getInfo(infos=param_path + '/desc')
                param_desc_short = cfg.features.models[model].getInfo(infos=param_path + '/desc_short')
                param_formula = cfg.features.models[model].getInfo(infos=param_path + '/formula')
                if param_formula:
                    param_desc_short += ': ' + param_formula
                self.features_actions[feat_id] = QtWidgets.QAction(param_desc_short, self)
                self.features_actions[feat_id].setToolTip(param_desc)
                self.models_submenus[model].addAction(self.features_actions[feat_id])

        self.features_button.setMenu(self.features_menu)

    def getButton(self):
        return self.features_button

    def getQActions(self):
        return self.features_actions

    def getFeaturesDesc(self):
        return self.features_desc


class FeaturesWidget(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals
        self.sorted_text = ""
        self.displayed_text = ""

        self.layout = QtWidgets.QHBoxLayout()

        self.features_menu = FeaturesMenu('Default order',
                                          prefix='Sorted by')
        self.features_desc = self.features_menu.getFeaturesDesc()
        self.features_infos = self.features_desc['FEATURES']
        self.features_button = self.features_menu.getButton()
        self.features_button.setToolTip("Select a feature to sort and display\n" +
                                        "SHIFT+click to sort while keeping the current feature displayed\n" +
                                        "CONTROL+click to display a feature while keeping the current sort order")
        self.features_actions = self.features_menu.getQActions()
        for feat_id in self.features_actions.keys():
            sort_by_feature = functools.partial(self.sortByFeatureId, feat_id)
            self.features_actions[feat_id].triggered.connect(sort_by_feature)
        self.layout.addWidget(self.features_button)

        # self.features_combo = gui.NoKeyEventCombo()
        # self.layout.addWidget(self.features_combo)
        # self.features_list = []
        # for feat_id, _, description in cfg.features.iterateFeatures(description=True):
        #     self.features_list.append(feat_id)
        #     self.features_combo.addItem(description)
        # self.features_combo.currentIndexChanged.connect(self.sortByFeature)

        self.sort_order = QtWidgets.QCheckBox("Decreasing order")
        self.sort_order.setCheckState(QtCore.Qt.Unchecked)
        self.sort_order.setToolTip("Hold SHIFT to disable auto-refresh")
        self.sort_order.stateChanged.connect(self.sortOrder)
        self.layout.addWidget(self.sort_order)

        # self.plot_btn = QtWidgets.QPushButton("Plot feature(s)")
        # self.plot_menu = QtWidgets.QMenu("Features plots", self.plot_btn)
        # self.features_plot = []
        # self.plot_single = QtWidgets.QAction("station-feature")
        # self.plot_single.triggered.connect(functools.partial(self.plotFeatures, False))
        # self.plot_menu.addAction(self.plot_single)
        # self.plot_multi = QtWidgets.QAction("feature1-feature2")
        # self.plot_multi.triggered.connect(functools.partial(self.plotFeatures, True))
        # self.plot_menu.addAction(self.plot_multi)
        # self.plot_btn.setMenu(self.plot_menu)
        # self.layout.addWidget(self.plot_btn)

        self.setLayout(self.layout)

    @QtCore.Slot()
    def sortByFeatureId(self, feat_id):
        kb_modifiers = QtWidgets.QApplication.keyboardModifiers()
        try:
            group, feat = feat_id.split('.')
            if group:
                name = self.features_infos[group][feat]['desc']
                formula = self.features_infos[group][feat].get('formula', '')
            else:
                name = self.features_infos[feat]['desc']
                formula = ''
            name = name[0].lower() + name[1:]
            if formula:
                name = f'{name}: {formula}'
            if kb_modifiers == QtCore.Qt.ControlModifier:
                # Display feature but keep previous sorting as is
                self.displayed_text = name
                #self.sorted_text doesn't change
            elif kb_modifiers == QtCore.Qt.ShiftModifier:
                # Sort with feature but keep previous feature displayed
                self.sorted_text = name
                #self.displayed_text doesn't change
            else:
                # By default, sort and display newly selected feature
                self.sorted_text = name
                self.displayed_text = self.sorted_text
        except ValueError:
            # Dealing with a model parameter
            _, model, param = feat_id.split('.')
            param_path = 'metaparams/' + param
            param = cfg.features.models[model].getInfo(infos=param_path + '/desc_short')
            model = cfg.features.models[model].getInfo(infos='desc_short')
            if kb_modifiers == QtCore.Qt.ControlModifier:
                # Display feature but keep previous sorting as is
                self.displayed_text = f"{param:s} ({model:s})"
                #self.sorted_text doesn't change
            elif kb_modifiers == QtCore.Qt.ShiftModifier:
                # Sort with feature but keep previous feature displayed
                self.sorted_text = f"{param:s} ({model:s})"
                #self.displayed_text doesn't change
            else:
                # By default, sort and display newly selected feature
                self.sorted_text = f"{param:s} ({model:s})"
                self.displayed_text = self.sorted_text

        if self.displayed_text == self.sorted_text:
            text = "Sorted by " + self.sorted_text
        else:
            text = "Sorted by {:s}, display {:s}".format(self.sorted_text, self.displayed_text)
        self.features_button.setText(text)

        message = {}
        reversed = True if self.sort_order.checkState() == QtCore.Qt.Checked else False
        if kb_modifiers == QtCore.Qt.ControlModifier:
            message.update({'DISPLAY_FEATURE': feat_id})
        elif kb_modifiers == QtCore.Qt.ShiftModifier:
            message.update({'SORT_BY': (feat_id, not reversed)})
        else:
            message.update({'DISPLAY_FEATURE': feat_id})
            message.update({'SORT_BY': (feat_id, not reversed)})
        self.send(message)

    @QtCore.Slot()
    def sortByFeature(self, ifeature):
        feature_id = self.features_list[ifeature]
        kb_modifiers = QtWidgets.QApplication.keyboardModifiers()
        message = {}
        reversed = True if self.sort_order.checkState() == QtCore.Qt.Checked else False
        if kb_modifiers == QtCore.Qt.ControlModifier:
            message.update({'DISPLAY_FEATURE': feat_id})
        elif kb_modifiers == QtCore.Qt.ShiftModifier:
            message.update({'SORT_BY': (feat_id, not reversed)})
        else:
            message.update({'DISPLAY_FEATURE': feat_id})
            message.update({'SORT_BY': (feature_id, not reversed)})
        self.send(message)

    @QtCore.Slot()
    def sortOrder(self, state):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        checked = True if state == 2 else False
        reversed = checked
        sort_message = {'SORT_BY': (None, not reversed)}
        if modifiers == QtCore.Qt.ShiftModifier:
            sort_message.update({'DELAY_SORT': True})
        self.send(sort_message)

    def plotFeatures(self, multi=False):
        self.features_plot.append(FeaturesPlotWindow(feat_id1=cfg.sort_by, multi=multi))
        self.features_plot[-1].show()

    def send(self, message):
        message['FROM'] = self.id
        self.gui_to_ctrl.emit(message)

# import pyqtgraph as pg

# raw_data = np.asarray(list(feature.values()))
# scatter_data = np.zeros(len(raw_data),
#                         dtype={'names':('feat1', 'feat2'),
#                                 'formats':('f8', 'f8')})
# # scatter_data['fields'] = cfg.stalist
# scatter_data['feat1'] = np.r_[1:cfg.nsta+.5]
# scatter_data['feat2'] = raw_data
# scatter_data = scatter_data.view(np.recarray)
# self.scatter = pg.ScatterPlotWidget()
# self.scatter.setData(scatter_data)
# self.scatter.setFields([('feat1', {'units': 'toto'}), ('feat2', {'units': 'toto'})])
# self.scatter.show()
# return
