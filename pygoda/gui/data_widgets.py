# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import copy
import functools

import numpy as np
import scipy as sp

import config as cfg

class DataComponentWidget(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self, grid=None):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals
        self.grid = grid

        self.layout = QtWidgets.QHBoxLayout()

        # self.comp_combo = gui.NoKeyEventCombo()
        # Components
        self.comp_combo = QtWidgets.QComboBox()
        self.comp_combo.setToolTip("Time series component currently in use")
        self.layout.addWidget(self.comp_combo)
        self.current_component = ""
        self.components = []
        self.ncomponents = 0
        self.icomponent = 0
        self.fillComponentsCombo()
        # Corrections
        self.corr_button = QtWidgets.QPushButton("corrections")
        self.corr_button.setToolTip("Toggle time series corrections...")
        self.layout.addWidget(self.corr_button)
        self.corrections = dict()
        self.ncorrections = 0
        self.icorrection = 0
        self.fillCorrectionsMenu()
        # Events
        #TODO


        self.setLayout(self.layout)

    def fillComponentsCombo(self):
        if self.ncomponents > 0:
            # Temporarily disconnect the components combo before updating it
            self.comp_combo.currentIndexChanged.disconnect()

        # Clear the combo
        for i in range(self.ncomponents):
            self.comp_combo.removeItem(0)

        # Fill the combo
        self.components = list(cfg.dataset.getData(cfg.stalist[0]).components.keys())
        self.ncomponents = len(self.components)
        self.icomponent = 0
        for comp in self.components:
            self.comp_combo.addItem("{:s}".format(comp))
            self.ncomponents += 1
        self.current_component = self.components[0]

        # Reconnect the combo once updated
        self.comp_combo.currentIndexChanged.connect(self.setCurrentComponent)

    def setCurrentComponent(self, icomponent):
        self.icomponent = icomponent
        self.current_component = self.components[self.icomponent]

        self.send({'COMPONENT': self.current_component})

    def getCorrections(self, data, name):

        # Component-independent corrections
        corrections = dict()
        try:
            reordered_corrections = copy.deepcopy(data.corrections)
            if '' in reordered_corrections:
                # Put generic ('') group at the end
                tmp = reordered_corrections.pop('')
                reordered_corrections.update({'': tmp})
            for grp_name, grp_corr in reordered_corrections.items():
                corrections[grp_name] = list(grp_corr.keys())
        except AttributeError:
            return corrections

        if corrections:
            self.corr_menu.addAction(name)

        for grp_name, grp_corr in corrections.items():
            if grp_name:
                self.corr_submenu = self.corr_menu.addMenu(grp_name)
            else:
                self.corr_submenu = self.corr_menu
            self.corrections[grp_name] = dict()
            for corr in grp_corr:
                self.corrections[grp_name][corr] = QtWidgets.QAction(corr)
                self.corrections[grp_name][corr].setCheckable(True)
                applied = data.corrections[grp_name][corr].correction_applied
                self.corrections[grp_name][corr].setChecked(applied)
                self.corr_submenu.addAction(self.corrections[grp_name][corr])
                self.corrections[grp_name][corr].triggered.connect(self.toggleCorrections)

        return corrections

    def fillCorrectionsMenu(self):

        self.corr_menu = QtWidgets.QMenu()

        # TODO: may require to loop over *all* the stations
        data = cfg.dataset.getData(cfg.stalist[0])
        corrections = self.getCorrections(data, "[Generic corrections]")

        if corrections:
            self.corr_menu.addSeparator()

        # Component-specific corrections
        comp = data.components[self.current_component]
        corrections = self.getCorrections(comp, "[Component-specific corrections]")

        self.corr_button.setMenu(self.corr_menu)

    def toggleCorrections(self):

        corrections = dict()
        for grp_name, grp_corr in self.corrections.items():
            corrections[grp_name] = []
            for corr_name, corr in grp_corr.items():
                if corr.isChecked():
                    corrections[grp_name].append(corr_name)

        self.send({'COMPONENT': self.current_component,
                   'CORRECTIONS': corrections})

    @QtCore.Slot()
    def updateComponentsCombo(self, events):
        if 'COMPONENT' in events:
            component = events['COMPONENT']

            self.icomponent = self.components.index(component)
            self.comp_combo.setCurrentIndex(self.icomponent)

        # self.setCompTooltip()

    def send(self, message):
        message['FROM'] = self.id
        self.gui_to_ctrl.emit(message)

    def setComboTooltip(self):

        pass
        # text = "%d comp:" % cfg.nsta
        # self.label.setText(text)
        # tooltip = "%d components\n" % self.ncomponents
        # self.comp_combo.setToolTip(tooltip)
