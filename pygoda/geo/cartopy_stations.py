# coding: utf-8

import copy

import numpy as np
import scipy as sp

import matplotlib.pyplot as plt

import constants as cst
import config as cfg
from themes import gui_themes as thm
from . import geotools

class CartopyStations():

    def __init__(self, fig, proj):

        self.fig = fig
        self.proj = proj

        # Add the stations axis (always the last, top-most layer)
        self.ax = self.fig.add_axes([0, 0, 1, 1], projection=self.proj, label='stations')
        #self.ax.outline_patch.set_visible(False)
        #self.ax.background_patch.set_visible(False)
        self.ax.spines['geo'].set_visible(False)
        self.ax.patch.set_visible(False)

        self.getStationsCoordinates()

    def getMapExtent(self, projected=True):
        if projected:
            return self.ax.get_extent()
        else:
            return self.ax.get_extent(geotools.PROJ_CARREE)

    def setMapExtent(self, extent, projected=True):

        if projected:
            self.ax.set_extent(extent, self.proj)
        else:
            self.ax.set_extent(extent, geotools.PROJ_GEODETIC)

    def getStationsCoordinates(self):

        self.sta_lon = np.asarray([cfg.data[staname].lon for staname in cfg.stalist])
        self.sta_lat = np.asarray([cfg.data[staname].lat for staname in cfg.stalist])
        self.lon_proj, self.lat_proj = geotools.transformProj(self.sta_lon, self.sta_lat, self.proj)

    def plotStations(self, update_list=False):

        self.ax.clear()
        self.ax.spines['geo'].set_visible(False)
        self.ax.patch.set_visible(False)

        if update_list:
            self.getStationsCoordinates()

        if cfg.sort_by in ('.DEFAULT', '.NAMES'):
            self.plotStationsCategories()
        else:
            self.plotStationsFeatures()

    def plotStationsCategories(self):

        plotted_indices = [cfg.plotted_sta[staname] for staname in cfg.stalist]

        list_categories = copy.deepcopy(cfg.CATEGORIES[cfg.current_grp])
        if cfg.current_grp != cfg.GRP_QUALITY:
            list_categories.insert(0, None)
        for category in list_categories:
            icat = [True if cfg.sta_category[staname][cfg.current_grp] == category else False
                    for staname in cfg.stalist]

            if category is None:
                category = cfg.CAT_DEFAULT

            # Stations currently in the grid
            icategory = [bool(x & y) for x, y in zip(icat, plotted_indices)]
            # print('Visible stations for category', category, ':')
            # print(icategory)
            self.ax.scatter(self.lon_proj[icategory], self.lat_proj[icategory],
                            marker=thm.stations_shape[category][cst.DEFAULT],
                            s=thm.stations_size[category][cst.DEFAULT],
                            # markeredgecolor='#FFFFFF',
                            color=thm.stations_color[category][cst.DEFAULT], zorder=2)

            # Stations not in the grid currently
            icategory = [bool(x & ~y) for x, y in zip(icat, plotted_indices)]
            # print('Hidden stations for category', category, ':')
            # print(icategory)
            self.ax.scatter(self.lon_proj[icategory], self.lat_proj[icategory],
                            marker='^',#thm.stations_shape[category][cst.DEFAULT],
                            s=.75*thm.stations_size[category][cst.DEFAULT],
                            # markeredgecolor='#FFFFFF',
                            color=thm.stations_color[category][cst.DEFAULT], zorder=1,
                            alpha=0.8)

    def plotStationsFeatures(self):

        feature = cfg.features.sta_features[cfg.sort_by]
        values_all = np.asarray([feature[sta] for sta in cfg.stalist \
                                 if not np.isnan(feature[sta])])
        mean = np.mean(values_all)
        #TODO: make color map choice more robust
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
        # size_normalize = np.abs(values)/max(abs(vmax), abs(vmin))
        # size_normalize[size_normalize > 1] = 1.
        size_normalize = 1.0
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
        # size_normalize = np.abs(values)/max(abs(vmax), abs(vmin))
        # size_normalize[size_normalize > 1] = 1.
        size_normalize = 1.0
        # print('Hidden stations for cfg.CAT_DEFAULT', cfg.CAT_DEFAULT, ':')
        # print(ihidden)
        self.ax.scatter(self.lon_proj[ihidden], self.lat_proj[ihidden],
                        marker=thm.stations_shape[cfg.CAT_DEFAULT][cst.DEFAULT],
                        # s=.5*thm.stations_size[cfg.CAT_DEFAULT][cst.DEFAULT],
                        s=2*thm.stations_size[cfg.CAT_DEFAULT][cst.DEFAULT]*size_normalize,
                        c=values, cmap=cmap, vmin=vmin, vmax=vmax, zorder=1) #, alpha=0.8)
