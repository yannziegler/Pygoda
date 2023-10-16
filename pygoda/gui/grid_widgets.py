# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import functools

import numpy as np
import scipy as sp

import config as cfg
import tools

class GenericGridWidget(QtWidgets.QWidget):

    controls_to_grid = QtCore.Signal(dict)

    def __init__(self, grid=None):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals
        self.grid = grid

    def send(self, message, sender=None):
        if not sender:
            sender = self.id
        message['FROM'] = sender
        self.controls_to_grid.emit(message)


class GridControlWidget(GenericGridWidget):

    def __init__(self, grid=None):
        GenericGridWidget.__init__(self, grid=grid)

        # Category filter menu/push button
        self.layout = QtWidgets.QHBoxLayout()

        # self.label = QtWidgets.QLabel("%d stations:" % cfg.nsta)
        # self.layout.addWidget(self.label)

        # self.stations_combo = gui.NoKeyEventCombo()
        self.stations_combo = QtWidgets.QComboBox()
        self.stations_combo.currentIndexChanged.connect(self.updateNavigationBtnState)
        self.layout.addWidget(self.stations_combo)
        self.npages = 0
        self.ipage = 0

        # Navigation buttons

        self.left_btn = QtWidgets.QPushButton("<")
        self.left_btn.clicked.connect(self.previousPage)
        self.left_btn.setMaximumWidth(30)
        self.left_btn.setToolTip("Previous grid page [CTRL+Left]")
        self.left_btn.setEnabled(False)
        self.layout.addWidget(self.left_btn)

        self.right_btn = QtWidgets.QPushButton(">")
        self.right_btn.clicked.connect(self.nextPage)
        self.right_btn.setMaximumWidth(30)
        self.right_btn.setToolTip("Next grid page [CTRL+Right]")
        self.layout.addWidget(self.right_btn)

        # self.layout.addStretch()

        self.setLayout(self.layout)

        if self.grid:
            self.connectToGrid()

    def nextPage(self):
        # current_index = self.stations_combo.currentIndex()
        self.ipage += 1
        self.stations_combo.setCurrentIndex(self.ipage)

    def previousPage(self):
        # current_index = self.stations_combo.currentIndex()
        self.ipage -= 1
        self.stations_combo.setCurrentIndex(self.ipage)

    def connectToGrid(self, grid):
        self.grid = grid
        self.fillPagesCombo()
        self.grid.grid_to_dependencies.connect(self.updateCombo)

    def fillPagesCombo(self):
        if self.npages > 0:
            # Temporarily disconnect the pages combo before updating it
            self.stations_combo.currentIndexChanged.disconnect()

        # Clear the combo
        for i in range(self.npages):
            self.stations_combo.removeItem(0)

        # Fill the combo
        self.ipage = 0
        self.npages = 0
        for i in range(0, cfg.nsta, self.grid.nplots):
            first_sta = cfg.stalist[i]
            ilast = min(i + self.grid.nplots, cfg.nsta) - 1
            last_sta = cfg.stalist[ilast]
            ndigits = int(np.log10(cfg.nsta_all))
            first_sta = tools.middle_ellipsis(first_sta, 25)
            last_sta = tools.middle_ellipsis(last_sta, 25)
            self.stations_combo.addItem("{:s} - {:s} [{:02d}: {:0{ndigits}d}-{:0{ndigits}d}]".\
                                        format(first_sta, last_sta, self.npages+1,\
                                               i+1, ilast+1, ndigits=ndigits))
            self.npages += 1

        # Reconnect the combo once updated
        self.stations_combo.currentIndexChanged.connect(self.updateNavigationBtnState)
        self.stations_combo.currentIndexChanged.connect(self.grid.changeGridPage)

        self.updateNavigationBtnState()

    @QtCore.Slot()
    def updateCombo(self, events):
        if 'PAGE' in events:
            index = events['PAGE']

            if index == -1:
                # Full refresh requested
                self.fillPagesCombo()
            else:
                self.ipage = index
                self.stations_combo.setCurrentIndex(self.ipage)
                if events.get('UPDATE', False):
                    # Manual update
                    self.grid.changeGridPage(self.ipage)

        self.updateNavigationBtnState()

        self.setStationsTooltip()

    def setStationsTooltip(self):

        # text = "%d stations:" % cfg.nsta
        # self.label.setText(text)
        tooltip = "%d stations in the dataset\n" % cfg.nsta_all + \
                  " : %d stations listed\n" % cfg.nsta + \
                  " : %d stations filtered out\n" % (cfg.nsta_all - cfg.nsta) + \
                  " : %d stations plotted" % len([sta for sta, plot in cfg.plotted_sta.items() if plot])
        self.stations_combo.setToolTip(tooltip)

    def updateNavigationBtnState(self):

        self.ipage = self.stations_combo.currentIndex()

        if self.ipage > 0:
            self.left_btn.setEnabled(True)
        else:
            self.left_btn.setEnabled(False)

        if self.ipage < self.npages - 1:
            self.right_btn.setEnabled(True)
        else:
            self.right_btn.setEnabled(False)


class GridTimeRangeWidget(GenericGridWidget):

    def __init__(self, grid=None, enabled=False, timespan=None):
        GenericGridWidget.__init__(self, grid=grid)

        # Category filter menu/push button
        self.layout = QtWidgets.QHBoxLayout()

        self.sync_timerange = QtWidgets.QCheckBox("t-sync")
        self.sync_timerange.setToolTip("Synchronise time range between all plots")
        self.sync_timerange.stateChanged.connect(self.syncTimeRange)
        self.layout.addWidget(self.sync_timerange)

        if timespan: 
            t0, t1 = timespan
            ymd_start, time_start = tools.datetime_tools.split_date(t0, group_datetime=True)
            ymd_end, time_end = tools.datetime_tools.split_date(t1, group_datetime=True)
        else:
            ymd_start = 2000, 1, 1
            time_start = 0, 0, 0
            ymd_end = 2022, 12, 31
            time_end = 23, 59, 59

        self.start_date = QtCore.QDateTime(QtCore.QDate(*ymd_start),
                                           QtCore.QTime(*time_start),
                                           QtCore.QTimeZone.utc())
        self.date_first = QtWidgets.QDateTimeEdit(self.start_date)
        # self.date_first.setCalendarPopup(True)
        self.date_first.dateTimeChanged.connect(self.updateTimeRange)
        self.date_first.setToolTip("Starting date")
        self.layout.addWidget(self.date_first)

        self.end_date = QtCore.QDateTime(QtCore.QDate(*ymd_end),
                                           QtCore.QTime(*time_end),
                                           QtCore.QTimeZone.utc())
        self.date_last = QtWidgets.QDateTimeEdit(self.end_date)
        # self.date_last.setCalendarPopup(True)
        self.date_last.dateTimeChanged.connect(self.updateTimeRange)
        self.date_last.setToolTip("End date")
        self.layout.addWidget(self.date_last)

        if enabled:
            self.sync_timerange.setCheckState(QtCore.Qt.Checked)
            self.date_first.setEnabled(True)
            self.date_last.setEnabled(True)
        else:
            self.sync_timerange.setCheckState(QtCore.Qt.Unchecked)
            self.date_first.setEnabled(False)
            self.date_last.setEnabled(False)

        # self.validate = QtWidgets.QPushButton('set')
        # self.date_last.setToolTip("Update the time span")
        # self.validate.clicked.connect(self.updateTimerange)
        # self.layout.addWidget(self.validate)

        self.setLayout(self.layout)

        if self.grid:
            self.connectToGrid()

    def updateTimeRange(self, sync=True):
        #TODO: bug once a model is fitted?! (double refresh)
        if sync:
            self.send({'start': self.date_first.dateTime().toPython(),
                       'end': self.date_last.dateTime().toPython()})
        else:
            self.send({'start': None, 'end': None})

    def syncTimeRange(self, state):
        checked = True if state == 2 else False
        if checked:
            self.date_first.setEnabled(True)
            self.date_last.setEnabled(True)
        else:
            self.date_first.setEnabled(False)
            self.date_last.setEnabled(False)

        self.updateTimeRange(sync=checked)

    def connectToGrid(self, grid):
        self.grid = grid
        # self.grid.grid_to_dependencies.connect(self.updateTimerange)
        self.controls_to_grid.connect(self.grid.updateTimeRange)


class GridYRangeWidget(GenericGridWidget):

    def __init__(self, grid=None, enabled=False):
        GenericGridWidget.__init__(self, grid=grid)

        # Category filter menu/push button
        self.layout = QtWidgets.QHBoxLayout()

        self.sync_yrange = QtWidgets.QCheckBox("y-sync")
        self.sync_yrange.setToolTip("Synchronise y-range between all plots")
        self.sync_yrange.stateChanged.connect(self.syncYRange)
        self.layout.addWidget(self.sync_yrange)

        self.ymin = QtWidgets.QLineEdit()
        self.ymin.setMinimumWidth(80)
        self.ymin.setClearButtonEnabled(True)
        self.ymin.editingFinished.connect(self.updateYRangeMin)
        self.ymin.returnPressed.connect(self.updateYRangeMin)
        self.ymin.setPlaceholderText("ymin")
        self.setToolTip("Set ymin and/or ymax to synchronise all the y-axes or let empty to disable synchronisation")
        self.layout.addWidget(self.ymin)

        self.ymax = QtWidgets.QLineEdit()
        self.ymax.setMinimumWidth(80)
        self.ymax.setClearButtonEnabled(True)
        self.ymax.editingFinished.connect(self.updateYRangeMax)
        self.ymax.returnPressed.connect(self.updateYRangeMax)
        self.ymax.setPlaceholderText("ymax")
        # self.ymax.setToolTip("Sync Ymax")
        self.layout.addWidget(self.ymax)

        #self.yrange_items = dict()
        self.yrange_actions = dict()
        
        # Bounds type and reference

        self.bound_type = "absolute"
        self.yrange_bound_types = {
        "absolute": "bounds refer to data value",
        "percentile": "bounds are quantiles (0.0 to +/-1.0) or percentiles (beyond +/-1% to +/-100%) of the data",
        "fraction": "bounds are fractions (0.0 to +/-1.0) or percentages (beyond +/-1%) of the data min/max",
        "sigma": "bounds are standard deviations (sigmas)",
        "sigma (detrended)": "bounds are standard deviations after removing trend (sigmas)",
        "MAD": "bounds are median absolute deviations",
        "MAD (detrended)": "bounds are median absolute deviations after removing trend"
        }
        self.bound_button = QtWidgets.QPushButton(self.bound_type)
        self.bound_button.setToolTip("Bound type")
        self.bound_menu = QtWidgets.QMenu("Bound type", self.bound_button)
        self.bound_menu.setToolTipsVisible(True)
        for bound_type, description in self.yrange_bound_types.items():
            self.yrange_actions[bound_type] = QtWidgets.QAction(bound_type, self)
            self.yrange_actions[bound_type].setToolTip(description)
            self.bound_menu.addAction(self.yrange_actions[bound_type])
            set_bound_type = functools.partial(self.setYRangeType, bound_type=bound_type)
            self.yrange_actions[bound_type].triggered.connect(set_bound_type)
        self.bound_button.setMenu(self.bound_menu)
        self.layout.addWidget(self.bound_button)

        self.reference_level = "zero"
        self.yrange_ref_types = {
        "zero": "bounds are relative to zero",
        "initial": "bounds are relative to data value at t0\n"
                   "[positive=above initial value, negative=below initial value]",
        "median": "bounds are relative to data median\n"
                  "[positive=above median, negative=below median]",
        "mean": "bounds are relative to data mean\n"
                "[positive=above mean, negative=below mean]",
        }
        self.reference_button = QtWidgets.QPushButton("wrt " + self.reference_level)
        self.reference_button.setToolTip("Reference level")
        self.reference_menu = QtWidgets.QMenu("Reference level", self.reference_button)
        self.reference_menu.setToolTipsVisible(True)
        for ref_type, description in self.yrange_ref_types.items():
            self.yrange_actions[ref_type] = QtWidgets.QAction(ref_type, self)
            self.yrange_actions[ref_type].setToolTip(description)
            self.reference_menu.addAction(self.yrange_actions[ref_type])
            set_reference_type = functools.partial(self.setYRangeType, reference_level=ref_type)
            self.yrange_actions[ref_type].triggered.connect(set_reference_type)
        self.reference_button.setMenu(self.reference_menu)
        self.layout.addWidget(self.reference_button)

        if enabled:
            self.sync_yrange.setCheckState(QtCore.Qt.Checked)
            self.ymin.setEnabled(True)
            self.ymax.setEnabled(True)
            self.bound_button.setEnabled(True)
            self.reference_button.setEnabled(True)
        else:
            self.sync_yrange.setCheckState(QtCore.Qt.Unchecked)
            self.ymin.setEnabled(False)
            self.ymax.setEnabled(False)
            self.bound_button.setEnabled(False)
            self.reference_button.setEnabled(False)

        self.setLayout(self.layout)

        if self.grid:
            self.connectToGrid()

    def updateYRangeMin(self):
        try:
            ymin = float(self.ymin.text())
            if self.bound_type == 'percentile' and abs(ymin) > 100:
                ymin = np.sign(ymin) * 100.
                self.ymin.setText(f'{ymin:.0f}')
            #if self.bound_type == 'fraction' or self.bound_type == 'percentile':
            #    try:
            #        ymax = float(self.ymax.text())
            #    except ValueError:
            #        ymax = 1.0
            #    if abs(ymin) <= 1.0 and abs(ymax) > 1.0:
            #        self.ymax.setText('{:.2f}'.format(ymax/100.))
            #    elif abs(ymin) > 1.0 and abs(ymax) <= 1.0:
            #        self.ymax.setText('{:.0f}'.format(ymax*100.))
        except ValueError:
            self.ymin.clear()
            ymin = None
        self.send({'ymin': ymin,
                   'bound_type': self.bound_type,
                   'reference_level': self.reference_level})

    def updateYRangeMax(self):
        try:
            ymax = float(self.ymax.text())
            if self.bound_type == 'percentile' and abs(ymax) > 100:
                ymax = np.sign(ymax) * 100.
                self.ymax.setText(f'{ymax:.0f}')
            #if self.bound_type == 'fraction' or self.bound_type == 'percentile':
            #    try:
            #        ymin = float(self.ymin.text())
            #    except ValueError:
            #        ymin = 1.0
            #    if abs(ymax) <= 1.0 and abs(ymin) > 1.0:
            #        self.ymin.setText('{:.2f}'.format(ymin/100.))
            #    elif abs(ymax) > 1.0 and abs(ymin) <= 1.0:
            #        self.ymin.setText('{:.0f}'.format(ymin*100.))
        except ValueError:
            self.ymax.clear()
            ymax = None
        self.send({'ymax': ymax,
                   'bound_type': self.bound_type,
                   'reference_level': self.reference_level})

    def syncYRange(self, state):
        checked = True if state == 2 else False
        if checked:
            self.ymin.setEnabled(True)
            self.ymax.setEnabled(True)
            self.bound_button.setEnabled(True)
            self.reference_button.setEnabled(True)
            if self.ymin.text():
                self.updateYRangeMin()
            if self.ymax.text():
                self.updateYRangeMax()
        else:
            self.ymin.setEnabled(False)
            self.ymax.setEnabled(False)
            self.bound_button.setEnabled(False)
            self.reference_button.setEnabled(False)
            self.send({'ymin': None,
                       'ymax': None,
                       'bound_type': self.bound_type,
                       'reference_level': self.reference_level})

    def setYRangeType(self, bound_type=None, reference_level=None):
        if bound_type is None:
            bound_type = self.bound_type
        else:
            self.bound_type = bound_type
            self.bound_button.setText(self.bound_type)

        if reference_level is None:
            reference_level = self.reference_level
        else:
            self.reference_level = reference_level
            self.reference_button.setText("wrt " + self.reference_level)

        if self.ymin.text():
            self.updateYRangeMin()
        if self.ymax.text():
            self.updateYRangeMax()

    def connectToGrid(self, grid):
        self.grid = grid
        self.controls_to_grid.connect(self.grid.updateYRange)

