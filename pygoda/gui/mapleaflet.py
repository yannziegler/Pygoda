# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui, QtWebChannel
from PySide2.QtWebEngineWidgets import QWebEngineView

import functools
import time

import numpy as np
import scipy as sp

from resources import rc_leaflet

import constants as cst
import config as cfg
import themes as thm
from geo import geotools
from geo import leaflet_jslink
from geo import leaflet_map
from geo import leaflet_stations


class LeafletMapPanel(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals

        self.mode = cfg.mode

        self.setMouseTracking(True)

        self.hovered_sta = []
        self.selected_sta = []

        self.layout = QtWidgets.QVBoxLayout()
        #self.layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)

        self.label = QtWidgets.QLabel()
        self.label.setText('Coordinates of the centre of the map:')
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                 QtWidgets.QSizePolicy.Minimum)
        self.layout.addWidget(self.label)

        # Create the Web view
        self.view = QWebEngineView()
        self.page = self.view.page()
        # print(dir(view.page()))

        # Setup the channel between Qt and the Web view
        self.jslink = leaflet_jslink.JSLink(self.label)
        self.channel = QtWebChannel.QWebChannel()
        self.page.setWebChannel(self.channel)
        self.channel.registerObject('jslink', self.jslink)

        # Create the map
        self.map_ = leaflet_map.LeafletMap(self.page, self.jslink)
        self.jslink.mapLoaded.connect(self.onLoadFinished)

        # Create the stations
        self.stations = leaflet_stations.LeafletStations(self.page, self.jslink)

        # Load the HTML page with the map
        with open('gui/leaflet_map.html', 'r', encoding='utf-8') as f:
            self.page.setHtml(f.read())
        self.map_loaded = False
        self.tmp_sta_events = None
        #self.view.loadFinished.connect(self.onLoadFinished)
        self.view.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                QtWidgets.QSizePolicy.Expanding)
        self.layout.addWidget(self.view)

        # Add some demo buttons
        self.bottom_layout = QtWidgets.QHBoxLayout()
        button = QtWidgets.QPushButton('Reset view')
        button.clicked.connect(self.map_.fitBound)
        self.bottom_layout.addWidget(button)
        #btn_station = QtWidgets.QPushButton('Add a marker')
        #addRandomStation = functools.partial(self.stations.addSingleStation, 'WXYZ')
        # addRandomStation = functools.partial(self.stations.sendList, [1, 2, 3, 4, 5])
        #btn_station.clicked.connect(addRandomStation)
        #self.bottom_layout.addWidget(btn_station)
        self.layout.addLayout(self.bottom_layout)

        #self.layout.setContentsMargins(0, 0, 0, 0)
        #self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.jslink.markerMouseover.connect(self.markerMouseover)
        self.jslink.markerMouseout.connect(self.markerMouseout)
        self.jslink.markerLeftClick.connect(self.markerLeftClick)
        # self.jslink.markerRightClick.connect(markerRightClick)
        self.jslink.mapRightClick.connect(self.mapRightClick)

    def onLoadFinished(self):

        # self.map_.configureMap()

        # Setup uPlot
        # with open('geo/uPlot.iife.min.js', 'r', encoding='utf-8') as f:
        #     self.page.runJavaScript(f.read())
        # Code (single function) to create a plot in a popup
        with open('geo/plot_data.js', 'r', encoding='utf-8') as f:
            self.page.runJavaScript(f.read())

        # Setup the map
        # with open('geo/setup_map.js', 'r', encoding='utf-8') as f:
            # self.page.runJavaScript(f.read())

        # Load the Javascript for interacting with Qt
        # with open('geo/qwebchannel.js', 'r', encoding='utf-8') as f:
        #    self.page.runJavaScript(f.read())
        # Setup our Javascript object for Qt <-> JS communication
        # with open('geo/setup_qwebchannel.js', 'r', encoding='utf-8') as f:
            # self.page.runJavaScript(f.read())

        #TODO: try to speak with the map to ensure that it is fully loaded


        self.map_loaded = True
        if self.tmp_sta_events:
            # updateMap() was called during the loading
            # do that again now:
            self.updateMap(self.tmp_sta_events)
            self.map_.fitBound()
            self.tmp_sta_events = None

    # From controller or dataset
    @QtCore.Slot(dict)
    def updateMap(self, sta_events):

        if not self.map_loaded:
            # At startup, we have to wait for the page to be fully loaded
            self.tmp_sta_events = sta_events
            return

        if sta_events['FROM'] == self.id:
            # This is the broadcast response from our own signal, just ignore
            return

        if 'MODE' in sta_events:
            self.mode = sta_events['MODE']

        if 'FILTER' in sta_events or 'SORTED' in sta_events:
            # Remove the stations which are not in the list anymore
            # but wait for the plot signal to update the map.
            # Note: in practice, this signal is received *after*
            # the PLOTTED signal, so it is useless.
            for sta in self.selected_sta:
                if sta not in cfg.stalist:
                    del self.selected_sta[self.selected_sta.index(sta)]
            for sta in self.hovered_sta:
                if sta not in cfg.stalist:
                    del self.hovered_sta[self.hovered_sta.index(sta)]
            return

        # The current group of categories has changed
        if 'CURRENT_CAT_GROUP' in sta_events:
            self.stations.plotStations()

        # The category of at least one station has changed, replot the markers
        if 'CATEGORY_CHANGED' in sta_events:
            stalist = [staname for staname, _, _ in sta_events['CATEGORY_CHANGED']]
            self.stations.setMarkersColors(stalist)

        # The plotted stations have changed, replot the markers
        if 'PLOTTED' in sta_events:
            self.stations.plotStations()

        # States have changed for some stations, update the hovered/selected lists
        for event, list_sta in sta_events.items():
            if event not in cst.STATE_EVENTS:
                continue

            if event == cst.HOVERED:
                self.hovered_sta += [sta for sta in list_sta if sta not in self.hovered_sta]
                self.stations.setStationsState(self.hovered_sta, cst.HOVERED)
            elif event == ~cst.HOVERED:
                self.hovered_sta = [sta for sta in self.hovered_sta if sta not in list_sta]
                self.stations.setStationsState(list_sta, ~cst.HOVERED)
            elif event == cst.SELECTED:
                self.selected_sta += [sta for sta in list_sta if sta not in self.selected_sta]
                self.stations.setStationsState(self.selected_sta, cst.SELECTED)
            elif event == ~cst.SELECTED:
                self.selected_sta = [sta for sta in self.selected_sta if sta not in list_sta]
                self.stations.setStationsState(list_sta, ~cst.SELECTED)

    def updateFullMap(self):
        with open('gui/leaflet_map.html', 'r', encoding='utf-8') as f:
            self.page.setHtml(f.read())

    def resetSelection(self):

        sta_events = dict()

        if self.mode == cst.MODE_INSPECTION:
            print('Leaving data inspection mode.')
            self.mode = cst.MODE_DEFAULT
            sta_events['MODE'] = self.mode

        if self.selected_sta:
            previously_selected_sta = self.selected_sta.copy()
            self.selected_sta = []
            sta_events.update({cst.SELECTED: [],
                               ~cst.SELECTED: previously_selected_sta})
            self.stations.setStationsState(previously_selected_sta, ~cst.SELECTED)

        self.send(sta_events)

    def selectStations(self, stalist):
        staname = stalist[0]
        if not cfg.plotted_sta[staname] and not cfg.auto_switch_page:
            return

        sta_events = dict()

        if self.mode != cst.MODE_INSPECTION:
            print('Entering data inspection mode.')
            self.mode = cst.MODE_INSPECTION
            sta_events['MODE'] = self.mode

        if not cfg.plotted_sta[staname]:
            # We need to plot the station on the grid before selecting it
            sta_events.update({'PLOT_REQUEST': staname})

        if staname not in self.selected_sta:
            self.stations.setStationsState(stalist, cst.SELECTED)
            self.selected_sta.append(staname)
            sta_events.update({cst.SELECTED: [staname]})

        self.send(sta_events)

    def deselectStations(self, stalist):
        sta_events = dict()

        for staname in stalist:
            del self.selected_sta[self.selected_sta.index(staname)]
        self.stations.setStationsState(stalist, ~cst.SELECTED)
        sta_events.update({~cst.SELECTED: stalist})

        if not self.selected_sta and self.mode == cst.MODE_INSPECTION:
            print('Leaving data inspection mode.')
            self.mode = cst.MODE_DEFAULT
            sta_events['MODE'] = self.mode

        self.send(sta_events)

    def send(self, message, sender=None):
        if not sender:
            sender = self.id
        message['FROM'] = sender
        self.gui_to_ctrl.emit(message)

    def markerMouseover(self, staname):
        if staname not in self.hovered_sta:
            self.hovered_sta += [staname]
            self.send({cst.HOVERED: self.hovered_sta.copy()})

    def markerMouseout(self, staname):
        if self.hovered_sta and staname in self.hovered_sta:
            del self.hovered_sta[self.hovered_sta.index(staname)]
            self.send({~cst.HOVERED: [staname]})

    def markerLeftClick(self, staname):
        if staname not in self.selected_sta:
            self.selectStations([staname])
        else:
            self.deselectStations([staname])

    def mapRightClick(self):
        self.resetSelection()


    # def click_on_map(self, event):

    #     if int(event.button) == 2: # MouseButton.CENTER
    #         modifiers = QtWidgets.QApplication.keyboardModifiers()
    #         if modifiers == QtCore.Qt.ControlModifier:
    #             if event.xdata is not None and event.ydata is not None:
    #                 lon, lat = PROJ_CARREE.transform_point(event.xdata, event.ydata, self.proj)
    #                 self.send({'REFERENCE_POINT': (lon, lat)})
    #         else:
    #             if self.regions_filter:
    #                 # We are already filtering, remove the filter
    #                 self.regions_filter = []
    #                 new_stalist = cfg.stalist_all
    #             else:
    #                 # Only display the stations inside the clicked polygon
    #                 if event.xdata is not None and event.ydata is not None:
    #                     lon, lat = PROJ_CARREE.transform_point(event.xdata, event.ydata, self.proj)
    #                     # print(lon, lat)
    #                     new_stalist = []
    #                     for region, _ in self.map_overlays['basins']['regions']:
    #                         if region.contains(Point(lon, lat)):
    #                             self.regions_filter.append(region)
    #                             for i, sta_point in enumerate(self.sta_multipoint):
    #                                 if sta_point.within(region):
    #                                     staname = cfg.stalist[i]
    #                                     new_stalist.append(staname)

    #             if new_stalist:
    #                 self.resetSelection()
    #                 self.send({'FILTER': new_stalist})
