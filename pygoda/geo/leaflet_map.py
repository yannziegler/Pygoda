# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui
import functools

import cartopy.feature as cfeature
from cartopy.feature import ShapelyFeature
import numpy as np
import scipy as sp

import constants as cst
import config as cfg
import themes as thm
from . import geotools


class LeafletMap():

    def __init__(self, page, jslink):

        self.page = page
        self.jslink = jslink

    # def configureMap(self):
    #     # Color filter for Leaflet
    #     with open('geo/leaflet-tilelayer-colorfilter.min.js', 'r', encoding='utf-8') as f:
    #         self.page.runJavaScript(f.read())
    #     # Configure the map
    #     with open('geo/map.js', 'r', encoding='utf-8') as f:
    #         # frame = self.view.page().mainFrame()
    #         # frame.evaluateJavaScript(f.read())
    #         self.page.runJavaScript(f.read())

    def panMap(self, lng, lat):
        # frame = self.view.page().mainFrame()
        # frame.evaluateJavaScript('map.panTo(L.latLng({}, {}));'.format(lat, lng))
        self.page.runJavaScript('map.panTo(L.latLng({}, {}));'.format(lat, lng))

    def fitBound(self):
        self.jslink.fitMapBound.emit()
