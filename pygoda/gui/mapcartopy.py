# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import numpy as np
import scipy as sp
import shapely.geometry as geom

import constants as cst
import config as cfg
import themes as thm
from geo import geotools
from geo import cartopy_map
from geo import cartopy_stations
from geo import cartopy_markers


class MapPanel(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self, hide_toolbar=True):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals

        self.mode = cfg.mode

        self.proj = geotools.PROJ2CARTOPY[cfg.proj]
        # Map extent is always given in PROJ_GEODETIC crs (lon, lat)
        #if cfg.map_extent:
        #    self.map_extent = geotools.transformExtentProj(cfg.map_extent,
        #                                                   self.proj)
        self.map_extent = cfg.map_extent
        self.initial_map_extent = None # set when zooming

        self.setMouseTracking(True)
        self.is_panning = False
        self.pressed_button = None

        self.hovered_sta = []
        self.selected_sta = []

        # Store the stations coordinates in the selected projection
        self.getStationsCoordinates()

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setMargin(0)

        self.axes = {}

        # Create the map
        self.map_ = cartopy_map.CartopyMap(self.proj)
        self.mw = self.map_.getMatplotlibWidget()
        self.fig = self.map_.getFigure()
        self.axes['map'] = self.map_.ax
        self.axes['overlays'] = self.map_.ax_overlays
        if hide_toolbar:
            toolbar = self.mw.findChild(QtWidgets.QToolBar)
            toolbar.setVisible(False)

        # Create the stations
        self.stations = cartopy_stations.CartopyStations(self.fig, self.proj)
        self.axes['stations'] = self.stations.ax

        # Create the markers for interactivity
        self.markers = cartopy_markers.CartopyMarkers(self.fig, self.proj)
        self.axes['markers'] = self.markers.ax

        # Determine the map extent using the entire data set
        if not self.map_extent:
            # 0-size, transparent markers, just to auto-update map extent
            self.map_.ax.scatter(self.lon_proj, self.lat_proj, marker='o',
                                 s=0, color='w', alpha=0)
            self.map_extent = self.map_.getMapExtent()
            self.map_.map_extent = self.map_.getMapExtent()

        self.layout.addWidget(self.mw)
        self.reset_view = QtWidgets.QPushButton('Reset view')
        self.reset_view.clicked.connect(self.resetView)
        self.layout.addWidget(self.reset_view)

        #self.layout.setContentsMargins(0, 0, 0, 0)
        #self.layout.setSpacing(0)
        self.setLayout(self.layout)

        # Connect the map (figure) to the events
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_motion)
        self.fig.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.fig.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.fig.canvas.mpl_connect('figure_leave_event', self.mouse_leave_map)

        self.base_scale = 0.1
        self.fig.canvas.mpl_connect('scroll_event', self.scrollZoom)

    def getAxes(self):
        axes = [self.axes['map'], self.axes['stations'], self.axes['markers']]
        axes += self.axes['overlays']
        return axes

    def setMapExtent(self, extent, projected=True, draw_now=False):
        self.map_.setMapExtent(extent, projected=projected)
        self.stations.setMapExtent(extent, projected=projected)
        self.markers.setMapExtent(extent, projected=projected)
        if draw_now:
            self.map_.draw()
            #self.stations.draw()
            #self.markers.draw()

    def scrollZoom(self, event, centre_zoom=False):
        if self.initial_map_extent is None:
            self.initial_map_extent = self.map_.getMapExtent(projected=True)

        ax = event.inaxes
        #if event.inaxes == ax:
        scale_factor = np.power(1. + self.base_scale, -event.step)
        xdata = event.xdata
        ydata = event.ydata
        #print('DATA', xdata, ydata)
        #xdata, ydata = geotools.transformProj(xdata, ydata, self.proj)
        #print(xdata, ydata)
        xlim_min, xlim_max = ax.get_xlim()
        ylim_min, ylim_max = ax.get_ylim()
        # xlim_min, xlim_max, ylim_min, ylim_max = ax.get_extent() # idem
        #print('MIN', xlim_min, ylim_min)
        #print('MAX', xlim_max, ylim_max)
        #print('EXTENT', ax.get_extent())

        #for axis in self.fig.axes:
        if centre_zoom:
            #TODO: not working yet
            xrange = .5 * (xlim_max - xlim_min)
            yrange = .5 * (ylim_max - ylim_min)
            x_min = xdata - scale_factor * xrange
            x_max = xdata + scale_factor * xrange
            y_min = ydata - scale_factor * yrange
            y_max = ydata + scale_factor * yrange
        else:
            x_left = xdata - xlim_min
            x_right = xlim_max - xdata
            y_top = ydata - ylim_min
            y_bottom = ylim_max - ydata
            x_min = xdata - scale_factor * x_left
            x_max = xdata + scale_factor * x_right
            y_min = ydata - scale_factor * y_top
            y_max = ydata + scale_factor * y_bottom
        #print('NEW', x_min, x_max, y_min, y_max)
        #print('DIFF', x_max - x_min, y_max - y_min)

        if (cfg.proj == 'lcc') and (x_max - x_min < 1.25e6 or y_max - y_min < 1.25e6):
            print('Cartopy bug prevented: maximum zoom level reached!')
            return

        map_extent = [x_min, x_max, y_min, y_max]
        self.setMapExtent(map_extent, projected=True, draw_now=True)
        #self.figure.canvas.draw()

    def resetView(self):
        ### For testing purpose (lcc projection)
        #map_extent = [900000, 2500000., 3600000., 5300000.] # works (with lcc)
        #map_extent = [900000, 2400000., 3600000., 5300000.] # doesn't work?!
        ### Doesn't work for no obvious reason
        #map_extent = [900000, 2300000., 3600000., 5300000.]
        #self.setMapExtent(map_extent, projected=True)
        ### Trick to make it works
        #map_extent = [900000, 2300000., 3600000., 5300000.]
        #print('PROJ BEFORE:', map_extent)
        #map_extent = geotools.transformExtentProj(map_extent,
        #                                          geotools.PROJ_GEODETIC,
        #                                          proj_src=self.proj)
        #print('PROJ AFTER:', map_extent)
        #self.setMapExtent(map_extent, projected=False)

        if self.initial_map_extent is None:
            return
        self.setMapExtent(self.initial_map_extent, projected=True, draw_now=True)
        self.initial_map_extent = None

    def _pan_update_limits(self, ax, axis_id, event, last_event):
        """Compute limits with applied pan."""
        assert axis_id in (0, 1)
        if axis_id == 0:
            lim = ax.get_xlim()
        else:
            lim = ax.get_ylim()

        pixel_to_data = ax.transData.inverted()
        data = pixel_to_data.transform_point((event.x, event.y))
        last_data = pixel_to_data.transform_point((last_event.x, last_event.y))

        delta = data[axis_id] - last_data[axis_id]
        new_lim = lim[0] - delta, lim[1] - delta

        return new_lim

    def _pan(self, event, draw_now=True):
        if event.name == 'button_press_event':  # begin pan
            self._event = event

        elif event.name == 'button_release_event':  # end pan
            self._event = None

        elif event.name == 'motion_notify_event':  # pan
            if self._event is None:
                return

            if event.x != self._event.x:
                for ax in self.getAxes():
                    xlim = self._pan_update_limits(ax, 0, event, self._event)
                    ax.set_xlim(xlim)

            if event.y != self._event.y:
                for ax in self.getAxes():
                    ylim = self._pan_update_limits(ax, 1, event, self._event)
                    ax.set_ylim(ylim)

            if event.x != self._event.x or event.y != self._event.y:
                if self.initial_map_extent is None:
                    self.initial_map_extent = self.map_.getMapExtent(projected=True)
                self.map_.draw()

            self._event = event

    def _on_mouse_press(self, event):
        if self.pressed_button is not None:
            return  # Discard event if a button is already pressed

        if event.button == 1:  # Start
            self.pressed_button = event.button
            self.is_panning = False # wait and see
            self._pan(event)

    def _on_mouse_motion(self, event):
        if self.pressed_button == 1:  # pan
            self.is_panning = True
            self._pan(event, draw_now=False)
            return

        #TODO: multi-hovering by region

        if event.xdata is not None and event.ydata is not None:
            # We are inside the map, get the index of the closest station
            node = np.asarray([event.xdata, event.ydata])
            dist_2 = np.sum((self.nodes - node)**2, axis=1)
            ista = np.argmin(dist_2)

            if cfg.stalist[ista] not in self.hovered_sta:
                previous_hovered_sta = self.hovered_sta
                self.hovered_sta = [cfg.stalist[ista]]
                self.updateHoveredMarker()
                self.send({~cst.HOVERED: previous_hovered_sta,
                           cst.HOVERED: self.hovered_sta})
                self.map_.draw()

    def _on_mouse_release(self, event):
        end_panning = False
        if self.pressed_button == event.button and event.button == 1:
            if self.is_panning:
                self._pan(event)
                end_panning = True
        self.pressed_button = None
        self.is_panning = False
        if end_panning:
            return

        #TODO: implement multi-selection (simultaneously if multi-hovering or successively)

        if int(event.button) == 1: # MouseButton.LEFT
            # Select a station
            if event.xdata is not None and event.ydata is not None:
                # We are inside the map, get the index of the closest station
                node = np.asarray([event.xdata, event.ydata])
                dist_2 = np.sum((self.nodes - node)**2, axis=1)
                ista = np.argmin(dist_2)

                staname = cfg.stalist[ista]
                self.selectStations([staname])
                self.map_.draw()

        elif int(event.button) == 3: # MouseButton.RIGHT
            # De-select all selected stations
            self.resetSelection()
            self.map_.draw()

        elif int(event.button) == 2: # MouseButton.CENTER
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                if event.xdata is not None and event.ydata is not None:
                    lon, lat = geotools.PROJ_CARREE.transform_point(event.xdata, event.ydata, self.proj)
                    self.send({'REFERENCE_POINT': (lon, lat)})
            else:
                if not self.map_.map_overlays:
                    return

                if self.map_.regions_filter:
                    # We are already filtering, remove the filter
                    self.map_.regions_filter = []
                    new_stalist = cfg.stalist_all
                else:
                    # Only display the stations inside the clicked polygon
                    if event.xdata is not None and event.ydata is not None:
                        lon, lat = geotools.PROJ_CARREE.transform_point(event.xdata, event.ydata, self.proj)
                        # print(lon, lat)
                        new_stalist = []
                        for region, _ in self.map_.map_overlays['basins']['regions']:
                            if region.contains(geom.Point(lon, lat)):
                                self.map_.regions_filter.append(region)
                                for i, sta_point in enumerate(self.sta_multipoint.geoms):
                                    if sta_point.within(region):
                                        staname = cfg.stalist[i]
                                        new_stalist.append(staname)
                self.map_.updateOverlays('basins')

                if new_stalist:
                    self.resetSelection()
                    self.send({'FILTER': new_stalist})

    def mouse_leave_map(self, event):

        # When leaving, switch the last hovered station back to default
        if self.hovered_sta is not None:
            print('leaving map')
            previous_hovered_sta = self.hovered_sta
            self.hovered_sta = []
            self.updateHoveredMarker()
            # self.send({~cst.HOVERED: previous_hovered_sta,
            #            cst.HOVERED: []})
            self.send({cst.HOVERED: []})
            self.map_.draw()

    def getStationsCoordinates(self):

        self.stalist_hash = hash(''.join(cfg.stalist))
        self.sta_lon = np.asarray([cfg.data[staname].lon for staname in cfg.stalist])
        self.sta_lat = np.asarray([cfg.data[staname].lat for staname in cfg.stalist])
        self.lon_proj, self.lat_proj = geotools.transformProj(self.sta_lon, self.sta_lat, self.proj)
        self.nodes = np.vstack((self.lon_proj, self.lat_proj)).T
        self.sta_multipoint = geom.MultiPoint(list(zip(self.sta_lon, self.sta_lat)))

    # From controller or dataset
    @QtCore.Slot(dict)
    def updateMap(self, sta_events):

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
            # Update the list of stations
            # self.getStationsCoordinates()
            # Replot
            # self.updateStations(update_list=True, draw_now=True)
            return

        # The current group of categories has changed
        if 'CURRENT_CAT_GROUP' in sta_events:
            self.updateStations()

        # The category of at least one station has changed, replot the markers
        if 'CATEGORY_CHANGED' in sta_events:
            # At least one station has changed
            # We lazily completely replot the stations for now
            self.updateStations()

        # The category of at least one station has changed, replot the markers
        if 'COMPONENT' in sta_events and cfg.sort_by not in ('.DEFAULT', '.NAMES'):
            #TODO: doesn't work yet!
            # Plot another component
            self.updateStations()

        # The plotted stations have changed, replot the markers
        if 'PLOTTED' in sta_events:
            update_list = False

            # Update the list of stations if needed
            if hash(''.join(cfg.stalist)) != self.stalist_hash:
                # The list of stations has changed (due to sorting/filtering)
                update_list = True
                self.getStationsCoordinates()

            self.updateStations(update_list=update_list)

        # States have changed for some stations, update the hovered/selected lists
        event_hovered, event_selected = False, False
        for event, list_sta in sta_events.items():
            if event not in cst.STATE_EVENTS:
                continue

            if event == cst.HOVERED:
                self.hovered_sta += [sta for sta in list_sta if sta not in self.hovered_sta]
                event_hovered = True
            elif event == ~cst.HOVERED:
                self.hovered_sta = [sta for sta in self.hovered_sta if sta not in list_sta]
                event_hovered = True
            elif event == cst.SELECTED:
                self.selected_sta += [sta for sta in list_sta if sta not in self.selected_sta]
                event_selected = True
            elif event == ~cst.SELECTED:
                self.selected_sta = [sta for sta in self.selected_sta if sta not in list_sta]
                event_selected = True

        if event_hovered:
            self.updateHoveredMarker()
        if event_selected:
            self.updateSelectedMarker()

        # self.fig.canvas.blit(self.ax.bbox) # doesn't work well
        self.map_.draw()

    def updateFullMap(self, draw_now=False):

        #TODO: do not use, doesn't work yet (wrong map_extent)

        self.map_.plotBackgroundMap()
        #TODO: plot the overlays if needed
        self.stations.plotStations(update_list=True)
        self.stations.setMapExtent(self.map_extent)
        self.markers.reset()
        self.markers.setMapExtent(self.map_extent)

        if draw_now:
            self.map_.draw()

    def updateStations(self, draw_now=False, update_list=False):

        self.stations.plotStations(update_list=update_list)
        if not self.map_extent:
            # Use the stations to adjust the maps extent automatically
            map_extent = self.stations.getMapExtent()
            self.map_.setMapExtent(map_extent)
            self.markers.setMapExtent(map_extent)
        else:
            # Use the map extent to adjust the stations layer
            map_extent = self.map_.getMapExtent()
            self.stations.setMapExtent(map_extent)
            self.markers.setMapExtent(map_extent)

        if draw_now:
            self.map_.draw()

    def updateHoveredMarker(self, draw_now=False):

        self.markers.setHoveredMarker(self.hovered_sta)

        if draw_now:
            self.map_.draw()

    def updateSelectedMarker(self, draw_now=False):

        self.markers.setSelectedMarker(self.selected_sta)

        if draw_now:
            self.map_.draw()

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
            self.updateSelectedMarker()

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

        if staname not in self.selected_sta:
            if not cfg.plotted_sta[staname]:
                # We need to plot the station in the grid before selecting it
                sta_events.update({'PLOT_REQUEST': staname})
            previous_selected_sta = self.selected_sta
            previous_hovered_sta = self.hovered_sta
            self.selected_sta = [staname]
            self.updateSelectedMarker()
            self.hovered_sta = [] # When we click, we consider that we stop hovering on the station
            self.updateHoveredMarker()
            sta_events.update({~cst.SELECTED: previous_selected_sta,
                               ~cst.HOVERED: previous_hovered_sta,
                               cst.SELECTED: self.selected_sta})

        self.send(sta_events)

    def send(self, message, sender=None):
        if not sender:
            sender = self.id
        message['FROM'] = sender
        self.gui_to_ctrl.emit(message)
