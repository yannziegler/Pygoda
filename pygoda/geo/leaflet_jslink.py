# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui, QtWebChannel
from PySide2.QtWebEngineWidgets import QWebEngineView

import json

import config as cfg
import constants as cst
from tools import tools

class JSLink(QtCore.QObject):

    mapLoaded = QtCore.Signal()

    addSingleStation = QtCore.Signal(str, float, float, str, bool)  # staname, lat, lng, tooltip, plotted
    addStations = QtCore.Signal(str)  # JSON as string
    clearStations = QtCore.Signal()
    sendStationData = QtCore.Signal(str, str)  # staname, JSON as string
    sendMarkerTemplate = QtCore.Signal(str)  # SVG
    setMarkersColors = QtCore.Signal(str)  # JSON as string
    setStationsState = QtCore.Signal(str, int)  # JSON as string
    # sendList = QtCore.Signal(list)

    markerMouseover = QtCore.Signal(str)
    markerMouseout = QtCore.Signal(str)
    markerLeftClick = QtCore.Signal(str)
    markerRightClick = QtCore.Signal(str)
    mapRightClick = QtCore.Signal()
    fitMapBound = QtCore.Signal()

    def __init__(self, label):
        QtCore.QObject.__init__(self)

        self.label = label
        self._lon = 0.0
        self._lat = 0.0
        self.onMapMove(self.lat, self.lon)

    @QtCore.Slot(str)
    def jsPrint(self, msg):
        print('JS says:', msg)

    def jsonDump(self, list_dict):
        return json.dumps(list_dict)

    @QtCore.Slot()
    def onMapLoad(self):
        print('Leaflet map fully loaded')
        self.mapLoaded.emit()

    @QtCore.Slot(float, float)
    def onMapMove(self, lon, lat):
        self.lon = lon
        self.lat = lat
        lon_dms = tools.to_dms(lon, plus_sign=False, lonlat='lon')
        lat_dms = tools.to_dms(lat, plus_sign=False, lonlat='lat')
        self.label.setText("Centre of the view: {:s}, {:s} ({:+.5f}, {:+.5f})".\
                            format(lon_dms, lat_dms, lon, lat))

    @QtCore.Slot(float, float)
    def onMapLeftClick(self, lon, lat):
        print('Left click!')
        self.lon = lon
        self.lat = lat
        lon_dms = tools.to_dms(lon, plus_sign=False, lonlat='lon')
        lat_dms = tools.to_dms(lat, plus_sign=False, lonlat='lat')
        self.label.setText("Click position: {:s}, {:s} ({:+.5f}, {:+.5f})".\
                            format(lon_dms, lat_dms, lon, lat))

    @QtCore.Slot()
    def onMapRightClick(self):
        print('Right click!')
        self.mapRightClick.emit()

    @QtCore.Slot(str)
    def onMarkerMouseover(self, staname):
        print('Station hovered:', staname)
        self.markerMouseover.emit(staname)

    @QtCore.Slot(str)
    def onMarkerMouseout(self, staname):
        # print('Station left:', staname)
        self.markerMouseout.emit(staname)

    @QtCore.Slot(str, int)
    def onMarkerClick(self, staname, state):
        if state == cst.SELECTED:
            print('Station selected:', staname)
        else:
            print('Station deselected:', staname)
        self.markerLeftClick.emit(staname)

    @QtCore.Slot(str)
    def onMarkerRightClick(self, staname):
        print('Data displayed:', staname)

        # Get the stations data
        data = {'t': [], 'Z': [], 'stdZ': []}
        data['t'] = [float(x) for x in cfg.data[staname].t]
        data['Z'] = [float(x) for x in cfg.data[staname].data]
        # data['stdZ'] = [float(x) for x in cfg.data[staname].std_data]
        data['Zlow'] = [float(x) for x in cfg.data[staname].data - cfg.data[staname].std_data]
        data['Zhigh'] = [float(x) for x in cfg.data[staname].data + cfg.data[staname].std_data]

        # Send the data for plotting in Javascript
        self.sendStationData.emit(staname, self.jsonDump(data))

    @QtCore.Slot(str)
    def printFromMap(self, msg=''):
        if not msg:
            msg = '({:+08.3f}, {:+07.3f})'.format(self.lon, self.lat)
        print(msg)

    @QtCore.Slot(float, float, bool)
    def updateLatLon(self, lat, lon, verbose=False):
        self.lon = lon
        self.lat = lat
        if verbose:
            self.printFromMap()

    # Longitude getter and setter
    def _get_lon(self):
        return self._lon

    def _set_lon(self, val):
        self._lon = val

    # Latitude getter and setter
    def _get_lat(self):
        return self._lat

    def _set_lat(self, val):
        self._lat = val

    @QtCore.Signal
    def _varUpdated(self):
        # Required with QWebChannel to avoid message:
        # Property 'xxx'' of object 'JSLink' has no notify signal
        # and is not constant, value updates in HTML will be broken!
        pass

    lon = QtCore.Property(float, _get_lon, _set_lon, notify=_varUpdated)
    lat = QtCore.Property(float, _get_lat, _set_lat, notify=_varUpdated)
