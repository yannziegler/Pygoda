# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import numpy as np
import scipy as sp

import config as cfg


class CategoryGroupWidget(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self, grid=None):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals
        self.grid = grid

        # Category filter menu/push button
        self.layout = QtWidgets.QHBoxLayout()

        self.groups_combo = QtWidgets.QComboBox()
        self.tooltip_header = "Group of categories currently in use.\n" \
                              "(CTRL+1..9 to switch to one of the first 9 groups)"
        self.updateToolTip(cfg.GRP_QUALITY)
        self.layout.addWidget(self.groups_combo)
        self.ngroups = 0
        self.igroup = 0

        self.setLayout(self.layout)

        self.fillGroupCombo()

    def fillGroupCombo(self):
        if self.ngroups > 0:
            # Temporarily disconnect the groups combo before updating it
            self.groups_combo.currentIndexChanged.disconnect()

        # Clear the combo
        for i in range(self.ngroups):
            self.groups_combo.removeItem(0)

        # Fill the combo
        for i, grp in enumerate(cfg.grp_names.values()):
            self.groups_combo.addItem("{:d}: {:s}".format(i, grp))
        self.ngroups = cfg.N_GRP_CAT

        # Reconnect the combo once updated
        self.groups_combo.currentIndexChanged.connect(self.setCurrentCategoryGroup)

    def setCurrentCategoryGroup(self, igroup):
        group = list(cfg.CATEGORIES.keys())[int(igroup)]
        self.updateToolTip(group)

        self.send({'CURRENT_CAT_GROUP': group})

    def updateToolTip(self, group):

        grp_name = cfg.grp_names[group]
        # list_keys = list(cfg.cat_keys[group].keys())
        # list_cats = list(cfg.cat_keys[group].values())

        tooltip = self.tooltip_header + '\n\n'
        tooltip += grp_name + ':\n'
        # for cat_id, cat_name in cfg.cat_names[group].items():
            # if cat_id in list_cats:
                # key = list_keys[list_cats.index(cat_id)]
        for i, cat_name in enumerate(cfg.cat_names[group].values()):
            tooltip += '[%d] %s\n' % (i, cat_name)

        self.groups_combo.setToolTip(tooltip[:-1])

    @QtCore.Slot()
    def updateCombo(self, events):
        if 'CURRENT_CAT_GROUP' in events:
            group = events['CURRENT_CAT_GROUP']

            self.igroup = list(cfg.CATEGORIES.keys()).index(group)
            self.groups_combo.setCurrentIndex(self.igroup)

            self.updateToolTip(group)

    def send(self, message):
        message['FROM'] = self.id
        self.gui_to_ctrl.emit(message)
