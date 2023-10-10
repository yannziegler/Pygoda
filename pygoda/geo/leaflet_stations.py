# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui, QtWebChannel
from PySide2.QtWebEngineWidgets import QWebEngineView
import functools

import copy

import matplotlib.pyplot as plt
import numpy as np
import scipy as sp

import constants as cst
import config as cfg
from themes import gui_themes as thm
from . import geotools

class LeafletStations():

    def __init__(self, page, jslink):

        self.page = page
        self.jslink = jslink

        self.sta_lon = np.asarray([cfg.data[staname].lon for staname in cfg.stalist])
        self.sta_lat = np.asarray([cfg.data[staname].lat for staname in cfg.stalist])

        self.marker_svg = ''

    def makeMarker(self, marker_svg=""):

        # marker_default = {'shape': 'o',
        #                   'color': '#ffffff',
        #                   'alpha': 1.,
        #                   'stroke_color': '#000000',
        #                   'stroke_width': 5,
        #                   'size': 3}
        # marker_default.update(marker)
        # marker = marker_default
        # marker['size'] *= 6

        # marker['svg'] = "<svg xmlns='http://www.w3.org/2000/svg'
        #                 width='300' height='300'>
        #                 <path d='M2,111 h300 l-242.7,176.3 92.7,-285.3 92.7,285.3 z'
        #                 fill='{color:s}'
        #                 fill-opacity='{alpha:f}'/>
        #                 </svg>".format(color=marker['color'],
        #                                alpha=marker.get('alpha', 1.))
        # marker['svg'] = """<svg xmlns='http://www.w3.org/2000/svg'
        #                     width='256' height='256'>
        #                     <circle cx="128" cy="128" r="120"
        #                     stroke='{stroke_color}'
        #                     stroke-width='{stroke_width}'
        #                     fill='{color}'
        #                     fill-opacity='{alpha}'/>
                            # </svg>"""
        # return self.jslink.jsonDump(marker)

        if not marker_svg:
            marker_svg = "<svg xmlns='http://www.w3.org/2000/svg' id='svg-icon-{staname}' class='svg-icon-default' viewBox='0 0 100 100'><circle id='svg-component-{staname}' class='svg-component-default' cx='50' cy='50' r='40' shape-rendering='geometricPrecision'/></svg>" # crispEdges

        self.marker_svg = marker_svg

        print('Create template!')
        self.jslink.sendMarkerTemplate.emit(marker_svg)

    def makeTooltip(self, staname):
        sta_lon, sta_lat = cfg.data[staname].lon, cfg.data[staname].lat
        tooltip = "<span style='font-weight: bold'>%s</span><br />" \
                  "%.2f&deg;&nbsp;%c, %.2f&deg;&nbsp;%c<br />" \
                  "%.1fm" % \
                    (staname,
                    abs(sta_lon), 'W' if sta_lon < 0. else 'E',
                    abs(sta_lat), 'S' if sta_lat < 0. else 'N',
                    cfg.data[staname].h)

        return tooltip

    @QtCore.Slot(str, dict, bool)
    def addSingleStation(self, staname, tooltip='', plotted=True):

        if not self.marker_svg:
            self.makeMarker()

        if staname not in cfg.data:
            lon, lat = -0.09, 51.505
        else:
            lon, lat = cfg.data[staname].lon, cfg.data[staname].lat

        if not tooltip:
            tooltip = self.makeTooltip(staname)

        # Add a marker ABCD with a random time series
        # js_add_plot = "addMarker([51.505, -0.09], `Hello world!`);"
        # js_add_plot = "addMarker(`{plot_id:s}`, [{lat:f}, {lng:f}]," \
        #               "`<div style='padding: 0; margin: 0; width: 400px; height: 250px;'" \
        #               "id='plot_{plot_id:s}'></div>`" \
        #               ");".format(lat=51.505, lng=-0.09, plot_id=plot_id)
        # Add a marker with a popup
        # self.view.page().runJavaScript(js_add_plot)

        self.jslink.addSingleStation.emit(staname, lat, lon, tooltip, plotted)

    @QtCore.Slot(list)
    def addStations(self, stalist):

        if not self.marker_svg:
            self.makeMarker()

        nsta = len(stalist)
        stalist_map = {'staname': stalist,
                       'lon': [0.]*nsta,
                       'lat': [0.]*nsta,
                       'tooltip': ['']*nsta,
                       'plotted': [False]*nsta}
        for ista, staname in enumerate(stalist):
            stalist_map['lon'][ista] = cfg.data[staname].lon
            stalist_map['lat'][ista] = cfg.data[staname].lat
            stalist_map['tooltip'][ista] = self.makeTooltip(staname)
            if cfg.plotted_sta[staname]:
                stalist_map['plotted'][ista] = True

        self.jslink.addStations.emit(self.jslink.jsonDump(stalist_map))

    def clearStations(self):

        self.jslink.clearStations.emit()

    def setMarkersColors(self, stalist=[]):

        if not stalist:
            stalist = cfg.stalist
        colorlist = []
        for staname in stalist:
            category = cfg.sta_category[staname][cfg.current_grp]
            if category is None:
                category = cfg.CAT_DEFAULT
            colorlist.append(thm.data_color[category][cst.DEFAULT])
        stacolors = {'staname': stalist,
                     'color': colorlist}

        self.jslink.setMarkersColors.emit(self.jslink.jsonDump(stacolors))

    def setStationsState(self, stalist, state):

        self.jslink.setStationsState.emit(self.jslink.jsonDump(stalist), state)

    def plotStations(self):

        self.clearStations()

        if cfg.sort_by in ('.DEFAULT', '.NAMES'):
            self.plotStationsCategories()
        else:
            self.plotStationsCategories() #TODO
            # self.plotStationsFeatures()

    def sendList(self, python_list=[1, 2, 3]):

        print('SEND LIST')
        self.jslink.sendList.emit(python_list)

    def plotStationsCategories(self):

        plotted_indices = [cfg.plotted_sta[staname] for staname in cfg.stalist]
        plotted_indices = np.asarray(plotted_indices)
        stalist = np.asarray(cfg.stalist)

        list_categories = copy.deepcopy(cfg.CATEGORIES[cfg.current_grp])
        if cfg.current_grp != cfg.GRP_QUALITY:
            list_categories.insert(0, None)

        for category in list_categories:
            icat = [True if cfg.sta_category[staname][cfg.current_grp] == category else False
                    for staname in cfg.stalist]

            if category is None:
                category = cfg.CAT_DEFAULT

            # Stations on current figure
            icategory = [bool(x & y) for x, y in zip(icat, plotted_indices)]
            #print('Visible stations for category', category, ':')
            #print(icategory)
            # for staname in stalist[icategory]:
            #     self.addSingleStation(staname, marker)
            stalist_category = list(stalist[icategory])
            if stalist_category:
                self.addStations(stalist_category)

            # Stations not on current figure
            icategory = [bool(x & ~y) for x, y in zip(icat, plotted_indices)]
            #print('Hidden stations for category', category, ':')
            #print(icategory)
            # for staname in stalist[icategory]:
            #     self.addSingleStation(staname, marker)
            stalist_category = list(stalist[icategory])
            if stalist_category:
                self.addStations(stalist_category)

        self.setMarkersColors()

    def plotStationsFeatures(self):

        feature = cfg.features.sta_features[cfg.sort_by]
        values_all = np.asarray([feature[sta] for sta in cfg.stalist])
        mean = np.mean(values_all)
        if (values_all <= 0).all():
            cmap = 'viridis'
            vmax = -np.min(np.abs(values_all))
            vmin = -np.quantile(np.abs(values_all), .99)
        elif (values_all >= 0).all():
            cmap = 'viridis'
            vmax = np.quantile(values_all, .99)
            vmin = np.min(values_all)
        else:
            cmap = 'coolwarm'
            vmax = np.quantile(np.abs(values_all[values_all > 0]), .99)
            vmin = -np.quantile(np.abs(values_all[values_all < 0]), .99)
            if np.abs(vmax - mean) > np.abs(vmin - mean):
                vmin = -vmax
            else:
                vmax = -vmin

        # Stations on current figure
        ivisible = [cfg.plotted_sta[staname] for staname in cfg.stalist]
        values = [feature[sta] for sta in cfg.stalist if cfg.plotted_sta[sta]]
        size_normalize = np.abs(values)/max(abs(vmax), abs(vmin))
        size_normalize[size_normalize > 1] = 1.
        # print('Visible stations for category', category, ':')
        # print(ivisible)
        self.ax.scatter(self.lon_proj[ivisible], self.lat_proj[ivisible],
                        marker=thm.stations_shape[cfg.CAT_DEFAULT][cst.DEFAULT],
                        # s=2*thm.stations_size[cfg.CAT_DEFAULT][cst.DEFAULT],
                        s=2*thm.stations_size[cfg.CAT_DEFAULT][cst.DEFAULT]*size_normalize,
                        c=values, cmap=cmap, vmin=vmin, vmax=vmax, zorder=2)

        # Stations not on current figure
        ihidden = [not cfg.plotted_sta[staname] for staname in cfg.stalist]
        values = [feature[sta] for sta in cfg.stalist if not cfg.plotted_sta[sta]]
        size_normalize = np.abs(values)/max(abs(vmax), abs(vmin))
        size_normalize[size_normalize > 1] = 1.
        # print('Hidden stations for cfg.CAT_DEFAULT', cfg.CAT_DEFAULT, ':')
        # print(ihidden)
        self.ax.scatter(self.lon_proj[ihidden], self.lat_proj[ihidden],
                        marker=thm.stations_shape[cfg.CAT_DEFAULT][cst.DEFAULT],
                        # s=.5*thm.stations_size[cfg.CAT_DEFAULT][cst.DEFAULT],
                        s=2*thm.stations_size[cfg.CAT_DEFAULT][cst.DEFAULT]*size_normalize,
                        c=values, cmap=cmap, vmin=vmin, vmax=vmax, zorder=1) #, alpha=0.8)
