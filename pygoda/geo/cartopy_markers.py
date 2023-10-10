# coding: utf-8

import numpy as np
import scipy as sp

import matplotlib.pyplot as plt
import matplotlib.transforms as mpl_transforms

import constants as cst
import config as cfg
from themes import gui_themes as thm
from . import geotools


class CartopyMarkers():

    def __init__(self, fig, proj, lon_init=0., lat_init=0.):

        self.fig = fig
        self.proj = proj

        # Add the stations axis (always the last, top-most layer)
        self.ax = self.fig.add_axes([0, 0, 1, 1], projection=self.proj, label='markers')
        self.ax.spines['geo'].set_visible(False)
        self.ax.patch.set_visible(False)

        self.mouse_pt = None
        self.mouse_txt = None
        self.kbd_pt = None
        self.kbd_txt = None

        self._createHoveredMarker(lon_init, lat_init)
        self._createSelectedMarker(lon_init, lat_init)

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

    def _createHoveredMarker(self, lon_init=0., lat_init=0.):
        # Create the marker used to indicate hovered stations
        self.mouse_pt = self.ax.plot(lon_init, lat_init,
                                     thm.stations_shape[cfg.CAT_NEUTRAL][cst.HOVERED],
                                     markersize=thm.stations_size[cfg.CAT_NEUTRAL][cst.HOVERED],
                                     color=thm.stations_color[cfg.CAT_NEUTRAL][cst.HOVERED],
                                     zorder=-2, alpha=0)
        bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0)
        self.mouse_txt = self.ax.text(lon_init, lat_init, '',
                                      bbox=bbox_props, zorder=2e6, alpha=0) #, ha='center', va='center'

    def _createSelectedMarker(self, lon_init=0., lat_init=0.):
        # Create the marker used to indicate selected stations
        self.kbd_pt = self.ax.plot(lon_init, lat_init,
                                   thm.stations_shape[cfg.CAT_NEUTRAL][cst.SELECTED],
                                   markersize=thm.stations_size[cfg.CAT_NEUTRAL][cst.SELECTED],
                                   color=thm.stations_color[cfg.CAT_NEUTRAL][cst.SELECTED],
                                   zorder=-1, alpha=0)
        bbox_props = dict(boxstyle="round", fc="#fcf3cf", ec="0.5", alpha=0)
        self.kbd_txt = self.ax.text(lon_init, lat_init, '',
                                    bbox=bbox_props, zorder=1e6, alpha=0) #, ha='center', va='center'

    def reset(self):
        self.mouse_pt = None
        self.mouse_txt = None
        self.kbd_pt = None
        self.kbd_txt = None

    def setHoveredMarker(self, hovered_sta):

        if self.mouse_pt is None:
            self._createHoveredMarker()

        if not hovered_sta:
            # Nothing is hovered, hide the marker
            self.mouse_pt[0].set_alpha(0)
            self.mouse_txt.set_alpha(0)
            bbox_props = dict(alpha=0)
            self.mouse_txt.set_bbox(bbox_props)
        else:
            n = len(hovered_sta)
            lon_hovered, lat_hovered = [0.]*n, [0.]*n
            for i, staname in enumerate(hovered_sta):
                lon_hovered[i] = cfg.data[staname].lon
                lat_hovered[i] = cfg.data[staname].lat

            # For now, only highlight the first station of the list
            hovered_sta = hovered_sta[0]
            # ista = cfg.stalist.index(hovered_sta)
            sta_lon = lon_hovered[0]
            sta_lat = lat_hovered[0]
            coord = "%.2f%c\n%.2f%c\n%.1fm" % \
                    (abs(sta_lon), 'W' if sta_lon < 0. else 'E',
                     abs(sta_lat), 'S' if sta_lat < 0. else 'N',
                     cfg.data[hovered_sta].h)

            lon_proj, lat_proj = geotools.transformProj(lon_hovered, lat_hovered, self.proj)
            lon_proj = lon_proj[0]
            lat_proj = lat_proj[0]
            self.mouse_pt[0].set_xdata(lon_proj)
            self.mouse_pt[0].set_ydata(lat_proj)
            self.mouse_pt[0].set_alpha(1)
            dx, dy = 7/72., 5/72. # in typographic points (1pt = 1/72 inch)
            txt_transform = mpl_transforms.offset_copy(self.ax.transData,
                                                       fig=self.fig, x=dx, y=dy, units='inches')
            self.mouse_txt.set_transform(txt_transform)
            self.mouse_txt.set_x(lon_proj)
            self.mouse_txt.set_y(lat_proj)
            self.mouse_txt.set_alpha(0.9)
            self.mouse_txt.set_text(hovered_sta + '\n' + coord)
            bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.8)
            self.mouse_txt.set_bbox(bbox_props)

        # self.ax.draw_artist(self.mouse_pt[0])
        # self.ax.draw_artist(self.mouse_txt)
        # self.cartopy_map.draw()

    def setSelectedMarker(self, selected_sta):

        if self.kbd_pt is None:
            self._createSelectedMarker()

        if not selected_sta:
            # Nothing is selected, hide the marker
            self.kbd_pt[0].set_alpha(0)
            self.kbd_txt.set_alpha(0)
            bbox_props = dict(alpha=0)
            self.kbd_txt.set_bbox(bbox_props)
        else:
            n = len(selected_sta)
            lon_selected, lat_selected = [0.]*n, [0.]*n
            for i, staname in enumerate(selected_sta):
                lon_selected[i] = cfg.data[staname].lon
                lat_selected[i] = cfg.data[staname].lat

            # For now, only highlight the first station of the list
            selected_sta = selected_sta[0]
            # ista = cfg.stalist.index(selected_sta)
            sta_lon = lon_selected[0]
            sta_lat = lat_selected[0]
            coord = "%.2f%c\n%.2f%c\n%.1fm" % \
                    (abs(sta_lon), 'W' if sta_lon < 0. else 'E',
                     abs(sta_lat), 'S' if sta_lat < 0. else 'N',
                     cfg.data[selected_sta].h)

            lon_proj, lat_proj = geotools.transformProj(lon_selected, lat_selected, self.proj)
            lon_proj = lon_proj[0]
            lat_proj = lat_proj[0]
            self.kbd_pt[0].set_xdata(lon_proj)
            self.kbd_pt[0].set_ydata(lat_proj)
            self.kbd_pt[0].set_alpha(1)
            dx, dy = 7/72., 5/72. # in typographic points (1pt = 1/72 inch)
            txt_transform = mpl_transforms.offset_copy(self.ax.transData,
                                                       fig=self.fig, x=dx, y=dy, units='inches')
            self.kbd_txt.set_transform(txt_transform)
            self.kbd_txt.set_x(lon_proj)
            self.kbd_txt.set_y(lat_proj)
            self.kbd_txt.set_alpha(0.9)
            self.kbd_txt.set_text(selected_sta + '\n' + coord)
            bbox_props = dict(boxstyle="round", fc="y", ec="0.5", alpha=0.8)
            self.kbd_txt.set_bbox(bbox_props)

        # self.ax.draw_artist(self.kbd_pt[0])
        # self.ax.draw_artist(self.kbd_txt)
        # self.cartopy_map.draw()
