# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import numpy as np

import constants as cst
import config as cfg
import themes as thm

class SingleFeaturePlot(pg.PlotWidget):

    def __init__(self, feature=None, xaxis='n', color_scale='', threshold_sig=None):
        pg.PlotWidget.__init__(self)

        self.changeThreshold = threshold_sig
        self.color_scale = color_scale
        self.xaxis = xaxis

        self.sta_line = None

        if feature:
            self.setFeature(feature)

    def setColorScale(self, color_scale, plot_now=False):
        self.color_scale = color_scale

        if color_scale == 'median':
            self.median = np.median(self.raw_data)
            self.data = self.raw_data - self.median
        else:
            self.data = self.raw_data.copy()
        if plot_now:
            self.plotFeature()

    def setXAxis(self, xaxis, plot_now=True):
        self.xaxis = xaxis.lower()

        if self.xaxis in ('n', 'stations', 'station'):
            self.x = np.r_[1:self.nsta+.5]
            self.xlabel = 'Station #'
        elif self.xaxis in ('fraction', 'percent', 'percentage'):
            step = 1./self.nsta
            # self.x = np.r_[step:100+.5*step:step]
            self.x = np.linspace(step, 1., self.nsta)
            self.xlabel = 'Fraction of stations'
            if self.xaxis == 'percent':
                self.x *= 100
                self.xlabel = '% of stations'

        if plot_now:
            self.plotFeature()

    def setFeature(self, feature, plot_now=True):
        self.feature = feature
        self.stalist = list(self.feature.keys())
        self.nsta = len(self.stalist)
        self.raw_data = np.asarray(list(self.feature.values()))
        self.data = self.raw_data.copy()
        if plot_now:
            self.setXAxis(self.xaxis, plot_now=False)
            self.setColorScale(self.color_scale, plot_now=False)
            self.plotFeature()

    def getThresholdIndex(self):
        return np.argmin(np.abs(self.x - self.sta_line.value()))

    def updateThresholdFromY(self):
        i = np.argmin(np.abs(self.data - self.threshold.value()))
        self.sta_line.setValue(self.x[i])
        self.threshold.setValue(self.data[i])
        self.text.setText(list(self.feature.keys())[i])
        self.text.setPos(self.x[i], self.data[i])

    def updateThresholdFromX(self):
        i = np.argmin(np.abs(self.x - self.sta_line.value()))
        self.threshold.setValue(self.data[i])
        self.sta_line.setValue(self.x[i])
        self.text.setText(list(self.feature.keys())[i])
        self.text.setPos(self.x[i], self.data[i])

    def setTextAnchor(self, side):
        self.text.setAnchor(anchor=(side, 1))

    def setXYRange(self, ymin, ymax):
        self.setYRange(ymin, ymax)
        self.setXRange(self.x[0], self.x[-1])

    def plotFeature(self):
        self.clear()
        self.enableAutoRange()
        self.setBackground(thm.ax_color[cfg.CAT_NEUTRAL][cst.DEFAULT])

        if self.color_scale:
            #TODO: plot with a color scale
            for x, y in self.x, self.data:
                self.scatter = pg.ScatterPlotItem(self.x, self.data, pen=None, symbol='o', size=5,
                                                  brush=thm.markers_color[cfg.CAT_NEUTRAL][cst.DEFAULT])
        else:
            self.scatter = pg.ScatterPlotItem(self.x, self.data, pen=None, symbol='o', size=5,
                                              brush=thm.markers_color[cfg.CAT_NEUTRAL][cst.DEFAULT])
            # self.scatter = pg.ScatterPlotItem(self.x, self.data, pen=None, symbol='o', size=2,
            #                                   brush=thm.data_color[cfg.CAT_NEUTRAL][cst.DEFAULT])
        self.addItem(self.scatter)

        self.threshold = pg.InfiniteLine(self.data[len(self.data)//2-1], angle=0, movable=True,
                                         label='{value:g}', labelOpts={'position': 0.05, 'anchors': [(0.5, 0), (0.5, 0)]})
        self.sta_line = pg.InfiniteLine(self.x[len(self.x)//2-1], angle=90, movable=True,
                                        label='{value:g}', labelOpts={'position': 0.05})
        self.threshold.sigPositionChanged.connect(self.updateThresholdFromY)
        self.sta_line.sigPositionChanged.connect(self.updateThresholdFromX)
        self.threshold.sigPositionChangeFinished.connect(self.changeThreshold)
        self.sta_line.sigPositionChangeFinished.connect(self.changeThreshold)
        self.addItem(self.threshold)
        self.addItem(self.sta_line)

        self.text = pg.TextItem(list(self.feature.keys())[len(self.x)//2-1], anchor=(1, 1))
        self.text.setPos(self.x[len(self.x)//2-1], self.data[len(self.data)//2-1])
        self.addItem(self.text)

        self.showGrid(x=True, y=True)

        # self.setYRange(Zmin, Zmax, padding=0)
        # self.setLabel('left', self.ylabel)
        self.setLabel('bottom', self.xlabel)
