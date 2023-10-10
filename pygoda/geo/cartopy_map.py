# coding: utf-8

import numpy as np
import scipy as sp

import cartopy.feature as cfeature
from cartopy.feature import ShapelyFeature
import geopandas as gpd
import matplotlib.pyplot as plt
from pyqtgraph.widgets import MatplotlibWidget
import shapely.geometry as geom

import constants as cst
import config as cfg
from themes import gui_themes as thm
from . import geotools


class CartopyMap():

    def __init__(self, proj, mw=None):

        self.proj = proj
        # Map extent is always stored as PROJ_GEODETIC crs (lon, lat)
        # Use self.getMapExtent() if you need the projected coordinates
        #if cfg.map_extent:
        #    self.map_extent = cfg.map_extent
        #    self.map_extent = geotools.transformExtentProj(cfg.map_extent,
        #                                                   self.proj)
        self.map_extent = cfg.map_extent

        self.map_overlays = dict() # ordered dict needed (Python >= 3.7)
        self.regions_filter = []

        if not mw:
            # Create Matplotlib figure
            mw = MatplotlibWidget.MatplotlibWidget()

        self.mw = mw
        self.fig = self.mw.getFigure()
        #plt.get_current_fig_manager().toolbar.pan()
        self.ax = None
        self.ax_overlays = []

        # Setup the map, call that every time a big refresh is needed
        self.createMap()

    def draw(self):
        self.mw.draw()

    def getMatplotlibWidget(self):
        return self.mw

    def getFigure(self):
        return self.fig

    def getStationsAxis(self):
        return self.ax_sta

    def getMapExtent(self, projected=True):
        # Do not return self.map_extent but the actual extent
        if projected:
            return self.ax.get_extent()
        else:
            return self.map_extent

    def setMapExtent(self, extent, projected=True, draw_now=False):

        if projected:
            #self.map_extent = geotools.transformExtentProj(extent,
            #                                               geotools.PROJ_GEODETIC,
            #                                               proj_src=self.proj)
            self.ax.set_extent(extent, self.proj)
            for ax_overlay in self.ax_overlays:
                ax_overlay.set_extent(extent, self.proj)
            self.map_extent = self.ax.get_extent()
            # /!\ self.map_extent != self.getMapExtent(projected=False)
            #print('MAP EXTENT', self.map_extent, self.getMapExtent(projected=False))
        else:
            self.map_extent = extent
            self.ax.set_extent(extent, geotools.PROJ_GEODETIC)
            for ax_overlay in self.ax_overlays:
                ax_overlay.set_extent(extent, geotools.PROJ_GEODETIC)

        if draw_now:
            self.draw()

    def createMap(self, draw_now=False):
        self.fig.clear()
        self.fig.patch.set_facecolor(thm.figure_color['background'])

        # self.proj = ccrs.LambertConformal(central_longitude=-96.0,
        #                                   central_latitude=40.0,
        #                                   standard_parallels=(20, 60),
        #                                   cutoff=0)
        # self.proj = ccrs.LambertConformal(central_longitude=-10.0,
        #                                   central_latitude=50.0,
        #                                   standard_parallels=(40, 60),
        #                                   cutoff=0)

        # Compute the convex hull containing all the stations
        # This improve the plotting speed for additional overlays
        self.gps_lon = np.asarray([cfg.data[staname].lon for staname in cfg.stalist])
        self.gps_lat = np.asarray([cfg.data[staname].lat for staname in cfg.stalist])
        self.sta_convex_hull = geotools.convexHull(self.gps_lon, self.gps_lat)
        # print(dir(self.sta_convex_hull))
        # for i, lonlat in enumerate(list(self.sta_convex_hull)):
            # lonlat_proj = self.proj.transform_points(ccrs.PlateCarree(), lonlat[0], lontlat[1])
            # self.sta_convex_hull[i] = lonlat_proj
        # print(self.sta_convex_hull)

        # with pg.BusyCursor():
        # Background map axis
        self.ax = self.fig.add_axes([0, 0, 1, 1], projection=self.proj, label='map')
        # self.fig.subplots_adjust(left=0.1, right=1-0.1, bottom=0.1, top=1-0.1)
        # self.ax_map.outline_patch.set_visible(False)
        # self.ax_map.background_patch.set_visible(False)
        self.plotBackgroundMap()
        #self.ax.set_aspect('auto')

        #TODO: strongly slow down zooming, check that...
        #if cfg.map_extent is None:
        #    self.ax.set_adjustable('datalim') # box or datalim

        # Add the overlays (e.g. the river basins)
        self.loadOverlays(filter_region=self.sta_convex_hull)
        self.plotOverlays()

        if draw_now:
            self.mw.draw()

    def plotBackgroundMap(self):
        ax = self.ax
        ax.clear()
        #ax.stock_img()
        ax.coastlines(resolution=cfg.map_resolution)
        # self.ax.coastlines(resolution='50m')
        # self.ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.OCEAN,
                       color=thm.map_colors['oceans'],
                       zorder=0,
                       alpha=1.0)
        #ocean = cfeature.NaturalEarthFeature('physical',
        #                                     'ocean',
        #                                     cfg.map_resolution,
        #                                     edgecolor=None,
        #                                     facecolor=thm.map_colors['oceans'],
        #                                     alpha=1.0)
        #ax.add_feature(ocean, zorder=1)
        #ax.add_feature(cfeature.LAND,
        #               color=thm.map_colors['continents'],
        #               edgecolor='black',
        #               zorder=0)
        land = cfeature.NaturalEarthFeature('physical',
                                            'land',
                                            cfg.map_resolution,
                                            edgecolor=None,
                                            facecolor=thm.map_colors['continents'],
                                            alpha=1.0)
        ax.add_feature(land, zorder=2)
        ax.add_feature(cfeature.BORDERS, linestyle=':')
        ax.add_feature(cfeature.LAKES, alpha=0.5)
        ax.add_feature(cfeature.RIVERS, alpha=0.5)

        # Once the stations are plotted, store the plot
        # self.mw.draw() # Needed before storing the background
        # self.map_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        if self.map_extent:
            self.setMapExtent(self.map_extent, projected=False)

    def loadOverlays(self, filter_region=None):
        for overlay, content in cfg.map_overlays.items():
            self.map_overlays[overlay] = {'axis': None, 'regions': []}
            shp_file = gpd.read_file(content['path'])
            # shp_basins = shp_basins.to_crs({'proj':'longlat', 'ellps':'WGS84', 'datum':'WGS84'})
            for region in shp_file['geometry']:
                # Get only the polygons which are inside the selected region
                if not filter_region or filter_region.intersects(region):
                    color = '#%02X%02X%02X' % tuple(np.random.randint(255, size=3))
                    # region_feature = ShapelyFeature([basin,], PROJ_CARREE)
                    # self.basins.append((region_feature, color))
                    self.map_overlays[overlay]['regions'].append((region, color))

    def updateOverlays(self, names=None):
        # Overlays to update
        if names:
            if not isinstance(names, list):
                names = [names]
        else:
            names = cfg.map_layers.keys()

        selected_overlays = dict()
        for name in names:
            # Select the overlays to plot (assuming that now display==True)
            selected_overlays[name] = cfg.map_layers[name]

        # with pg.BusyCursor():
        self.plotOverlays(selected_overlays=selected_overlays)
        self.mw.draw()

    def plotOverlays(self, selected_overlays=None, add_axes_only=False):
        if not selected_overlays:
            selected_overlays = cfg.map_overlays

        for name, overlay in selected_overlays.items():
            # Even if there is nothing to plot *yet*, we need to add
            # the axes in the right order, bottom to top.
            ax = self.map_overlays[name]['axis']
            if not ax:
                ax = self.fig.add_axes([0, 0, 1, 1],
                                       projection=self.proj,
                                       label=name)
                self.map_overlays[name]['axis'] = ax
                self.ax_overlays.append(ax)

            #if not overlay['display'] or add_axes_only:
            ax.clear()

            ax.spines['geo'].set_visible(False)
            ax.patch.set_visible(False)
            if self.map_extent:
                self.setMapExtent(self.map_extent, projected=False)
            else:
                # 0-size, transparent markers, just to auto-update map extent
                ax.scatter(self.lon_proj, self.lat_proj, marker='o',
                           s=0, color='w', alpha=0)
                self.map_extent = self.getMapExtent(projected=False)

            if not overlay['display'] or add_axes_only:
                continue

            if overlay['type'] == 'SHP':
                self.plotShapeFiles(ax, self.map_overlays[name]['regions'],
                                    alpha=overlay['alpha'],
                                    simplify=overlay['simplify'])
            else:
                raise ValueError("Unknown type of data in overlay '%s'." % name)

    def plotShapeFiles(self, ax, shapes, alpha=1, simplify=0):
        plot_shapes, plot_colors = [], []

        for shape, color in shapes:
            # Only plot the region used to filter the stations if a filter is enabled
            if not self.regions_filter or shape in self.regions_filter:
                # ax.add_feature(shape, edgecolor='black', facecolor=color, alpha=alpha)
                if simplify > 0:
                    shape = shape.simplify(simplify, preserve_topology=False)
                plot_shapes.append(shape)
                plot_colors.append(color)

        ax.add_geometries(plot_shapes, crs=geotools.PROJ_CARREE,
                          edgecolor='black', facecolor=plot_colors, alpha=alpha)
