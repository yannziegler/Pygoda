# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import numpy as np
import scipy as sp

import config as cfg
from . import grid_plots


class GridPanel(QtWidgets.QWidget):

    def __init__(self,
                 grid=None,
                 grid_widgets=None,
                 highlevel_widgets=None,
                 parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.widgets = []

        if grid:
            self.grid = grid
        else:
            self.grid = grid_plots.GridPlots()

        # Setup the grid controls and features widget
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setMargin(0)

        # Control panel above the grid
        self.top_layout = QtWidgets.QVBoxLayout()
        self.top_layout.setSpacing(0)
        self.top_layout.setMargin(0)

        # High-level functions
        self.high_layout = QtWidgets.QHBoxLayout()
        self.high_layout.setSpacing(0)
        self.high_layout.setMargin(0)
        if 'category_group' in highlevel_widgets:
            self.setupCategoryGroupWidget(highlevel_widgets['category_group'])
            # self.high_layout.addStretch()
        if 'features_sort':
            self.setupFeaturesWidget(highlevel_widgets['features_sort'])

        # Low level grid controls
        self.low_layout = QtWidgets.QHBoxLayout()
        self.low_layout.setSpacing(0)
        self.low_layout.setMargin(0)
        if 'page_control' in grid_widgets:
            self.setupControlsWidget(grid_widgets['page_control'])
            # self.low_layout.addStretch()
        if 'data_component' in highlevel_widgets:
            self.setupComponentWidget(highlevel_widgets['data_component'])
            # self.low_layout.addStretch()
        if 'timerange':
            self.setupTimeRangeWidget(grid_widgets['timerange'])
            # self.low_layout.addStretch()
        if 'yrange':
            self.setupYRangeWidget(grid_widgets['yrange'])

        self.top_layout.addLayout(self.high_layout)
        self.top_layout.addLayout(self.low_layout)
        self.layout.addLayout(self.top_layout)

        self.layout.addWidget(self.grid, 100)
        # self.grid.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        # self.grid.setMinimumSize(800, 800)

        self.setLayout(self.layout)

    def getGrid(self):
        return self.grid

    def setupControlsWidget(self, widget, layout=None):
        if not layout:
            layout = self.low_layout
        self.controls_widget = widget
        self.controls_widget.connectToGrid(self.grid)
        layout.addWidget(self.controls_widget)

    def setupYRangeWidget(self, widget, layout=None):
        if not layout:
            layout = self.low_layout
        self.yrange_widget = widget
        self.yrange_widget.connectToGrid(self.grid)
        layout.addWidget(self.yrange_widget)

    def setupTimeRangeWidget(self, widget, layout=None):
        if not layout:
            layout = self.low_layout
        self.timerange_widget = widget
        self.timerange_widget.connectToGrid(self.grid)
        layout.addWidget(self.timerange_widget)

    def setupComponentWidget(self, widget, layout=None):
        if not layout:
            layout = self.low_layout
        self.component_widget = widget
        layout.addWidget(self.component_widget)

    def setupCategoryGroupWidget(self, widget, layout=None):
        if not layout:
            layout = self.high_layout
        self.features_widget = widget
        layout.addWidget(self.features_widget)

    def setupFeaturesWidget(self, widget, layout=None):
        if not layout:
            layout = self.high_layout
        self.cat_group_widget = widget
        layout.addWidget(self.cat_group_widget)


class GridGeometryWidget(QtWidgets.QWidget):

    geom_to_grid = QtCore.Signal()

    def __init__(self, grid=None):
        QtWidgets.QWidget.__init__(self)

        self.overrideWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle('Grid geometry')

        self.grid = grid

        # Setup the layout and its components
        self.layout = QtWidgets.QVBoxLayout()

        self.row = QtWidgets.QLabel("rows")
        self.nrows = QtWidgets.QLineEdit(str(cfg.nrows))
        self.nrows_field = QtWidgets.QHBoxLayout()
        self.nrows_field.addWidget(self.row)
        self.nrows_field.addWidget(self.nrows)
        self.layout.addLayout(self.nrows_field)

        self.col = QtWidgets.QLabel("columns")
        self.ncols = QtWidgets.QLineEdit(str(cfg.ncols))
        self.ncols_field = QtWidgets.QHBoxLayout()
        self.ncols_field.addWidget(self.col)
        self.ncols_field.addWidget(self.ncols)
        self.layout.addLayout(self.ncols_field)

        self.auto_adjust = QtWidgets.QCheckBox("Adjust geometry")
        state = QtCore.Qt.Checked if cfg.auto_adjust_geometry else QtCore.Qt.Unchecked
        self.auto_adjust.setCheckState(state)
        self.layout.addWidget(self.auto_adjust)

        self.apply_geom = QtWidgets.QPushButton("Apply")
        self.apply_geom.clicked.connect(self.setGridGeometry)
        self.layout.addWidget(self.apply_geom)

        self.setLayout(self.layout)

        if self.grid:
            self.connectToGrid()

    def connectToGrid(self, grid):
        self.grid = grid
        self.geom_to_grid.connect(self.grid.updateGeometry)

    def setGridGeometry(self):
        emit_signal = False
        try:
            new_nrows = int(self.nrows.text())
            new_ncols = int(self.ncols.text())
        except:
            self.nrows = cfg.nrows
            self.ncols = cfg.ncols
            return

        if new_nrows != cfg.nrows or new_ncols != cfg.ncols:
            emit_signal = True

        cfg.nrows = new_nrows
        cfg.ncols = new_ncols
        cfg.nplots = cfg.nrows * cfg.ncols
        cfg.auto_adjust_geometry = self.auto_adjust.isChecked()
        if emit_signal:
            self.geom_to_grid.emit()
        self.close()

