# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import contextlib
import numpy as np
from scipy import stats
from scipy import signal

from tools import datetime_tools
import constants as cst
import config as cfg
from themes import gui_themes as thm

show_hour = False

class InfLineLabelDate(pg.InfLineLabel):

    def __init__(self, args, **kwargs):
        pg.InfLineLabel.__init__(self, args, **kwargs)

    def valueChanged(self):
        global show_hour

        if not self.isVisible():
            return
        value = self.line.value()
        # Here is the change to handle date
        text = datetime_tools.timestamp2str(value, show_hour=show_hour)
        #self.setText(self.format.format(value=value))
        self.setText(text)
        self.updatePosition()


class InfiniteLineDate(pg.InfiniteLine):

    def __init__(self, args, label=None, labelOpts=None, **kwargs):
        pg.InfiniteLine.__init__(self, args, angle=90, label=label, labelOpts=labelOpts, **kwargs)

        if label is not None:
            labelOpts = {} if labelOpts is None else labelOpts
            self.label = InfLineLabelDate(self, text=label, **labelOpts)


class LargePlot(pg.PlotWidget):

    def __init__(self, staname=None, plot_now=False):
        #pg.PlotWidget.__init__(self)
        pg.PlotWidget.__init__(self, axisItems = {'bottom': pg.DateAxisItem(utcOffset=0)})

        self.lock_view = None
        self.pending_plot = False
        self.plotted = False
        self.crosshair_plotted = False

        self.title_item = None

        self.stats_item = None
        self.t0 = None
        self.t1 = None
        self.t0_line = None
        self.t1_line = None
        self.interval_fill = None

        self.nodata_item = None

        self.setBackground(thm.ax_color[cfg.CAT_NEUTRAL][cst.DEFAULT])

        if staname is not None:
            self.setStation(staname, plot_now)
        else:
            # Allow initialisation without specifying a station
            self.staname = None

        self.getViewBox().setAcceptHoverEvents(True)
        self.getViewBox().hoverEnterEvent = self.hoverEnterEvent
        self.getViewBox().hoverLeaveEvent = self.hoverLeaveEvent
        #self.getViewBox().mouseClickEvent = self.mouseClickEvent
        self.scene().sigMouseClicked.connect(self.mouseClickEvent)

    def hoverEnterEvent(self, event):
        if self.pending_plot:
            self.plot()
        if self.plotted and not self.crosshair_plotted:
            self.addCrosshair()

    def hoverLeaveEvent(self, event):
        if self.crosshair_plotted:
            self.removeCrosshair()

    def snapMouse(self, mouse_point, modifier=None):
        tmin, tmax = self.getViewBox().state['viewRange'][0]
        Zmin, Zmax = self.getViewBox().state['viewRange'][1]
        #geom = self.getViewBox().screenGeometry()
        #width = geom.width()
        #height = geom.height()

        if modifier == QtCore.Qt.ControlModifier:
            # Snap to the closest point by date if CONTROL pressed
            i = np.argmin(np.abs(self.t - mouse_point.x()))
            t_snap = self.t[i]
            Z_snap = self.Z[i]
        elif modifier == QtCore.Qt.ShiftModifier:
            # Snap to the closest point by value if SHIFT pressed
            in_range = (self.t >= tmin) & (self.t <= tmax)
            i = np.argmin(np.abs(self.Z[in_range] - mouse_point.y()))
            t_snap = self.t[in_range][i]
            Z_snap = self.Z[in_range][i]
        else:
            # Snap to the closest point by default
            in_range = (self.t >= tmin) & (self.t <= tmax)
            tt = np.abs(tmax - tmin)
            if np.abs(tt) < 1e-15:
                tt = 1.
            ZZ = np.abs(Zmax - Zmin)
            if np.abs(ZZ) < 1e-15:
                ZZ = 1.
            t_diff = (self.t[in_range] - mouse_point.x())/tt
            Z_diff = (self.Z[in_range] - mouse_point.y())/ZZ
            i = np.argmin(np.abs(t_diff**2 + Z_diff**2))
            t_snap = self.t[in_range][i]
            Z_snap = self.Z[in_range][i]

        return t_snap, Z_snap

    def mouseMoved(self, event):
        global show_hour

        coordinates = event[0]
        if self.sceneBoundingRect().contains(coordinates):
            mouse_point = self.plotItem.vb.mapSceneToView(coordinates)
            tmin, tmax = self.getViewBox().state['viewRange'][0]
            Zmin, Zmax = self.getViewBox().state['viewRange'][1]
            if tmax - tmin < 3.15576e7: # one year in seconds
                show_hour = True
            else:
                show_hour = False

            modifier = QtWidgets.QApplication.keyboardModifiers()
            t_crosshair, Z_crosshair = self.snapMouse(mouse_point, modifier)
            self.date_line.setValue(t_crosshair)
            self.data_line.setValue(Z_crosshair)
            #self.date_line.setPos(t_crosshair)
            #self.data_line.setPos(Z_crosshair)
            #self.text.setText(self.Z[i])
            #self.text.setPos(self.t[i], self.Z[i])
            #self.date_line.setPos(mouse_point.x())
            #self.data_line.setPos(mouse_point.y())

            if self.t0 is not None and self.t1 is None:
                self.updateIntervalStats(t_crosshair)

    def mouseClickEvent(self, event):

        # print(dir(event))
        # event.buttons()
        # event.modifiers()
        # event.pos()
        # event.double()

        if not self.plotted:
            return

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            coordinates = event.scenePos()
            if not self.sceneBoundingRect().contains(coordinates):
                return
            mouse_point = self.plotItem.vb.mapSceneToView(coordinates)
            #print('MOUSE', mouse_point)
            modifier = QtWidgets.QApplication.keyboardModifiers()
            t_point, Z_point = self.snapMouse(mouse_point, modifier)
            #print('POINT', (t_point, Z_point))
            if self.t0 is None or (self.t1 is None and t_point < self.t0):
                self.t0 = t_point
                self.updateIntervalStats()
            elif self.t0 is not None and self.t1 is None and t_point > self.t0:
                self.t1 = t_point
                self.updateIntervalStats()
            else:
                # Third click, or second click exactly on t0
                self.resetInterval()

    def updateIntervalStats(self, t1=None):
        if self.t0 is None:
            self.resetInterval()
            return

        if self.t0 is not None and self.t0_line is None:
            self.t0_line = pg.InfiniteLine(self.t0, angle=90, movable=False, label='', pen='#FFFFFF')
            self.t0_line.setZValue(100)
            self.addItem(self.t0_line)
        else:
            self.t0_line.setPos(self.t0)

        if self.t1 is not None and self.t1_line is None:
            self.t1_line = pg.InfiniteLine(self.t1, angle=90, movable=False, label='', pen='#FFFFFF')
            self.t1_line.setZValue(101)
            self.addItem(self.t1_line)

        t0 = self.t0 # handy alias
        if t1 is None:
            if self.t1 is None:
                # Interval selection just started
                t1 = t0
            else:
                t1 = self.t1
        # else: interval selection is ongoing, t1 is set to crosshair position

        if t1 < t0:
            if self.interval_fill:
                self.removeItem(self.interval_fill)
            return

        i0 = np.argmin(np.abs(self.t - t0))
        i1 = np.argmin(np.abs(self.t - t1))

        if self.interval_fill:
            self.removeItem(self.interval_fill)
        Zmin, Zmax = np.amin(self.Z), np.amax(self.Z)
        self.interval_fill = pg.QtGui.QGraphicsRectItem(t0, Zmin, abs(t1 - t0), abs(Zmax - Zmin))
        self.interval_fill.setPen(pg.mkPen(None))
        self.interval_fill.setBrush(pg.mkBrush(thm.figure_color['background'] + 'A0'))
        self.interval_fill.setZValue(1)
        self.addItem(self.interval_fill)

        if i1 == i0:
            slope = 0.0
            std_err = 0.0
            mad_detrended = 0.0
        else:
            t_interval = self.t[i0:min(i1 + 1, len(self.t))]
            Z_interval = self.Z[i0:min(i1 + 1, len(self.t))]
            slope, _, _, _, std_err = stats.linregress(t_interval, Z_interval)
            Z_detrended = signal.detrend(Z_interval)
            #mad = np.median(np.abs(Z_interval - np.median(Z_interval)))
            mad_detrended = np.median(np.abs(Z_detrended - np.median(Z_detrended)))

        #TODO: doesn't work well when there is a gap

        text_template = '<span style="color: {color:s};">' \
                        '<span style="font-weight: bold;">t<sub>0</sub>: </span>{t0:s}' \
                        '<br>' \
                        '<span style="font-weight: bold;">t<sub>1</sub>: </span>{t1:s}' \
                        '<br>' \
                        '<span style="font-weight: bold;">&#916;t: </span>{dt:.2f} day' \
                        '<br>' \
                        '<span style="font-weight: bold;">slope: </span>{slope:+.2f}  &#177;{std:.2f} yr<sup>-1</sup>' \
                        '<br>' \
                        '<span style="font-weight: bold;">MAD (detrend): </span>{mad:.2f}' \
                        '</span>'
        #text_template = text_template.replace('}', ':s}')
        self.stats_text = text_template.format(color=thm.station_name_color[cfg.CAT_NEUTRAL][cst.DEFAULT],
                                               t0=datetime_tools.timestamp2str(t0, show_hour=show_hour),
                                               t1=datetime_tools.timestamp2str(t1, show_hour=show_hour),
                                               dt=(t1 - t0)/86400.,
                                               slope=slope*86400.*365.25, std=std_err*86400.*365.25,
                                               mad=mad_detrended)
        if self.stats_item:
            self.getViewBox().removeItem(self.stats_item)
        self.stats_item = pg.TextItem(html=self.stats_text,
                                      fill=thm.figure_color['background'] + 'E0')
        self.stats_item.setZValue(200)
        # self.addItem(self.title)  # Use coordinate system
        self.stats_item.setParentItem(self.getViewBox())
        self.stats_item.setPos(5, 25)

    def resetInterval(self, keep_boundaries=False):
        if not keep_boundaries:
            self.t0 = None
            self.t1 = None
        if self.stats_item:
            self.getViewBox().removeItem(self.stats_item)
            self.removeItem(self.t0_line)
            self.removeItem(self.t1_line)
            self.removeItem(self.interval_fill)
            self.stats_item = None
            self.t0_line = None
            self.t1_line = None

    def setStation(self, staname, plot_now=True):
        if staname == self.staname:
            return

        self.staname = staname

        # self.dock.setTitleBarWidget(self.staname)

        if plot_now and len(cfg.dataset.getData(self.staname).data) < cfg.largeplot_update_threshold:
            self.plot()
        else:
            text_template = '<span style="color: {color};">' \
                            'Too many data points, auto update is disabled.<br />' \
                            'Hover to plot <span style="font-weight: bold;">{station}</span>' \
                            '</span>'
            text_template = text_template.replace('}', ':s}')
            self.text = text_template.format(station=self.staname,
                                             color=thm.station_name_color[cfg.CAT_NEUTRAL][cst.DEFAULT])
            self.clear()
            if self.pending_plot:
                self.getViewBox().removeItem(self.text_item)
            self.text_item = pg.TextItem(html=self.text)
            self.text_item.setParentItem(self.getViewBox())
            self.text_item.setPos(50, 10)
            self.pending_plot = True
            self.plotted = False

    def createTitle(self, name_only=False):

        sta_category = cfg.sta_category[self.staname][cfg.current_grp]
        if sta_category and sta_category != cfg.CAT_DEFAULT:
            cat_name = cfg.cat_names[cfg.current_grp][sta_category]
        else:
            sta_category = cfg.CAT_DEFAULT
            cat_name = ''

        if name_only or not cat_name:
            text_template = '<span style="color: {color};">' \
                            '<span style="font-weight: bold;">{station}</span> ' \
                            '</span>'
            text_template = text_template.replace('}', ':s}')
            self.title = text_template.format(station=self.staname,
                                              color=thm.station_name_color[sta_category][cst.DEFAULT])
        else:
            text_template = '<span style="color: {color};">' \
                            '<span style="font-weight: bold;">{station}</span> ' \
                            '{category}' \
                            '</span>' # <br />' \
            text_template = text_template.replace('}', ':s}')
            self.title = text_template.format(station=self.staname,
                                              category='[' + cat_name + ']' if sta_category != cfg.CAT_DEFAULT else '',
                                              color=thm.station_name_color[sta_category][cst.DEFAULT])

        return self.title

    def plot(self):

        data = cfg.dataset.getData(self.staname)
        self.t = data.t
        self.Z = data.data
        self.Zstd = data.data.std
        t, Z, Zstd = self.t, self.Z, self.Zstd # aliases
        category = cfg.sta_category[self.staname]

        if np.all(np.isnan(Z)):
            if self.nodata_item is not None:
                self.getViewBox().removeItem(self.nodata_item)
            self.clear()

            self.setBackground(thm.ax_color[cfg.CAT_NEUTRAL][cst.DEFAULT])
            self.showGrid(x=True, y=True, alpha=.5)

            if self.title_item is not None:
                self.getViewBox().removeItem(self.title_item)

            color = thm.station_name_color[cfg.CAT_NEUTRAL][cst.DEFAULT]
            station = self.staname
            nodata_text = f'<span style="color: {color};">' \
                           'No data for ' \
                          f'<span style="font-weight: bold;">{station}</span>' \
                           '</span>'
            self.nodata_item = pg.TextItem(html=nodata_text)
            self.nodata_item.setParentItem(self.getViewBox())
            self.nodata_item.setPos(10, 5)

            self.plotted = True
            return
        elif self.nodata_item is not None:
            self.getViewBox().removeItem(self.nodata_item)

        # Component-independent events
        events = list(data.all_events)
        # Component-specific events
        comp_events_grps = data.components[cfg.data_component].events
        for comp_events_grp in comp_events_grps.values():
            for comp_events in comp_events_grp.values():
                events += list(comp_events)
        events.sort()
        events = np.asarray(events)
        #print(events)

        # We will replot the interval using the same boundaries (if any)
        self.resetInterval(keep_boundaries=True)

        if self.pending_plot:
            self.pending_plot = False
            self.getViewBox().removeItem(self.text_item)
        self.clear()
        self.setBackground(thm.ax_color[cfg.CAT_NEUTRAL][cst.DEFAULT])

        for event in events:
            event_line = pg.InfiniteLine(event, pen=pg.mkPen(color=thm.events_color[cfg.CAT_NEUTRAL][cst.DEFAULT], width=1))
            event_line.setZValue(6)
            self.addItem(event_line)

        if len(Z[~np.isnan(Z)]) > cfg.largeplot_update_threshold:
            context = pg.BusyCursor()
        else:
            context = contextlib.nullcontext()

        with context:
            self.scatter = pg.ScatterPlotItem(t, Z, pen=None, symbol='o', size=2.5,
                                              brush=thm.data_color[cfg.CAT_NEUTRAL][cst.DEFAULT])
            self.scatter.setZValue(5)
            self.addItem(self.scatter)
            if np.any(Zstd):
                self.std_low = pg.PlotDataItem(t, Z - Zstd, pen=pg.mkPen('#00000044'))
                self.std_low.setZValue(4)
                self.addItem(self.std_low)
                self.std_high = pg.PlotDataItem(t, Z + Zstd, pen=pg.mkPen('#00000044'))
                self.std_high.setZValue(4)
                self.addItem(self.std_high)
                self.std_between = pg.FillBetweenItem(self.std_low, self.std_high, brush=pg.mkBrush('#0000001C'))
                self.std_between.setZValue(3)
                self.addItem(self.std_between)

        if 'MODELS.' in cfg.displayed_feature:
            _, selected_model, _ = cfg.displayed_feature.split('.')
            fitted_model = cfg.models[selected_model].fitted_models[self.staname]
            if fitted_model is not None:
                # self.model = pg.PlotCurveItem(t, fitted_model, pen=pg.mkPen(color='#FF0000', width=2),
                #                               antialias=True, connect='finite')
                self.model = pg.ScatterPlotItem(t, fitted_model, pen=None, brush='#FF0000', size=1, alpha=0.5)
                self.addItem(self.model)
                self.model.setZValue(10)

        #         horizontalalignment='left',
        #         verticalalignment='center', transform=ax.transAxes)
        # for spine in ax.spines:
        #     ax.spines[spine].set_color(ax_spines_color[category][state])
        #     ax.spines[spine].set_linewidth(ax_spines_width[category][state])
        # ax.axes.get_xaxis().set_visible(False)
        # ax.axes.get_yaxis().set_visible(False)
        # np.float64 needed for unclear reasons
        #self.setXRange(np.nanmin(t), np.nanmax(t), padding=0)
        self.setXRange(np.float64(np.nanmin(t)), np.float64(np.nanmax(t)), padding=0)
        Zmin = np.nanmin(Z - Zstd)
        Zmin *= 1 - 0.1*np.sign(Zmin)
        Zmax = np.nanmax(Z + Zstd)
        Zmax *= 1 + 0.1*np.sign(Zmax)
        if np.abs(Zmax - Zmin) < 1e-15:
            # Everything is 0.0
            Zmin = -1.
            Zmax = 1.
        self.setYRange(Zmin, Zmax, padding=0)

        self.showGrid(x=True, y=True, alpha=.5)

        self.createTitle()
        if self.title_item:
            self.getViewBox().removeItem(self.title_item)
        self.title_item = pg.TextItem(html=self.title,
                                      fill=thm.figure_color['background'] + 'E0')
        self.title_item.setZValue(200)
        # self.addItem(self.title)  # Use coordinate system
        self.title_item.setParentItem(self.getViewBox())
        self.title_item.setPos(10, 5)

        if self.t0:
            self.updateIntervalStats()

        self.plotted = True

    def addCrosshair(self):
        t, Z = self.t, self.Z # aliases
        self.date_line = InfiniteLineDate(t[len(t)//2-1],
                                          movable=False,
                                          label='',
                                          labelOpts={'position': 0.05,
                                                     #'anchors': [(0, 0.5), (0, 0.5)],
                                                     'fill': thm.figure_color['background'] + 'E0'})
        self.data_line = pg.InfiniteLine(Z[len(Z)//2-1],
                                         angle=0,
                                         movable=False,
                                         label='{value:g}',
                                         labelOpts={'position': 0.05,
                                                    #'anchors': [(0.5, 0), (0.5, 0)],
                                                    'fill': thm.figure_color['background'] + 'E0'})
        self.date_line.setZValue(1000)
        self.data_line.setZValue(1001)
        #self.date_line.sigPositionChanged.connect(self.updateThresholdFromX)
        #self.data_line.sigPositionChanged.connect(self.updateThresholdFromY)
        #self.date_line.sigPositionChangeFinished.connect(self.changeThreshold)
        #self.data_line.sigPositionChangeFinished.connect(self.changeThreshold)
        self.addItem(self.date_line)
        self.addItem(self.data_line)

        #self.text = pg.TextItem(str(Z[len(t)//2-1]), anchor=(1, 1))
        #self.text.setPos(t[len(t)//2-1], Z[len(Z)//2-1])
        #self.addItem(self.text)

        self.crosshair_plotted = True
        self.crosshair_proxy = pg.SignalProxy(self.scene().sigMouseMoved,
                                              rateLimit=10,
                                              slot=self.mouseMoved)

    def removeCrosshair(self):
        t, Z = self.t, self.Z # aliases
        self.removeItem(self.date_line)
        self.removeItem(self.data_line)

        self.crosshair_plotted = False
        self.crosshair_proxy.disconnect()

    @QtCore.Slot(dict)
    def updatePlot(self, sta_events):
        if 'MODE' in sta_events and sta_events['MODE'] == cst.MODE_DEFAULT:
            self.lock_view = None

        list_hovered = []
        list_selected = []
        for event, stalist in sta_events.items():
            if not isinstance(event, int):
                continue # not a state change, it's another event
            if cst.HOVERED == event:
                list_hovered += stalist
            if cst.SELECTED == event:
                list_selected += stalist
                # Lock the view on the last selection
                if list_selected:
                    self.lock_view = list_selected[-1]

        if list_hovered:
            self.setStation(staname=list_hovered[-1])
        elif list_selected:
            self.setStation(staname=list_selected[-1])
        elif self.lock_view:
            self.setStation(staname=self.lock_view)
