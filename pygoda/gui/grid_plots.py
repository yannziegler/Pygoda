# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import functools
import time

import numpy as np
import pyqtgraph as pg
import scipy as sp
from scipy import signal

import constants as cst
import config as cfg
from themes import gui_themes as thm
from tools import datetime_tools
from tools import tools


class GridPlots(pg.GraphicsLayoutWidget):

    gui_to_ctrl = QtCore.Signal(dict)
    grid_to_dependencies = QtCore.Signal(dict)

    def __init__(self):
        pg.GraphicsLayoutWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals

        self.mode = cfg.mode

        self.hovered_sta = []
        self.selected_sta = []
        self.nplots = cfg.nplots
        self.ncols = cfg.ncols
        self.npages = 0
        self.timerange = {'start': None, 'end': None}
        self.yrange = {'ymin': None,
                       'ymax': None,
                       'bound_type': 'absolute',
                       'reference_level': 'zero'}

        self.plotted_sta = []

        self.ipage = 0
        self.group = cfg.current_grp

        # Finish the setup by calling setup() from the outside once all the
        # signals are connected.
        self.setup = self.createPlotsGrid

        ## Shortcuts
        self.shortcut = {}
        self.createShortcuts()
        self.setDefaultShortcuts()

    @QtCore.Slot()
    def createPlotsGrid(self, new_plotted_sta=[]):
        self.setBackground(thm.figure_color['background'])
        #pg.setConfigOption('foreground', ax_color[CAT_NEUTRAL][DEFAULT])
        self.nplots = cfg.nplots

        old_plotted_sta = [sta for sta in self.plotted_sta if sta not in new_plotted_sta]

        if self.plotted_sta:
            self.clearGrid()

        if new_plotted_sta:
            # When we replot the same stations, remove them from old_plotted_sta
            self.plotted_sta = new_plotted_sta.copy()
        else:
            # Fill the plots with the first stations at launch
            self.plotted_sta = cfg.stalist[0:cfg.nplots]

        self.graphs = [None]*len(self.plotted_sta)
        self.placeholders = []

        with pg.BusyCursor():
            # self.setEnabled(False)
            if (nsta := len(self.plotted_sta)) < cfg.nplots and cfg.auto_adjust_geometry:
                self.ncols = int(np.round(.5*np.sqrt(nsta)))
            else:
                self.ncols = cfg.ncols

            for iplot, staname in enumerate(self.plotted_sta):
                plot_state = cst.SELECTED if staname in self.selected_sta else cst.DEFAULT
                new_plot = GridSubplot(iplot, staname, state=plot_state,
                                       yrange=self.yrange, timerange=self.timerange,
                                       plot_now=True)
                self.graphs[iplot] = new_plot
                # cfg.plotted_sta[staname] = True # done by the controller now

                self.addItem(new_plot, iplot // self.ncols, iplot % self.ncols)

                self.graphs[iplot].plot_to_grid.connect(self.signalFromSubplot)

            if not cfg.auto_adjust_geometry:
                for iplot in range(len(self.plotted_sta), cfg.nplots):
                    # Put blank placeholders in the grid to force the same number of rows/columns
                    new_blank = GridSubplot(iplot, placeholder=True)
                    self.placeholders.append(new_blank)
                    self.addItem(new_blank, iplot // cfg.ncols, iplot % cfg.ncols)

            # self.setEnabled(True)

            # Set the selected stations
            sta_events = dict()

            if len(self.selected_sta) == 1:
                if isinstance(self.selected_sta[0], int):
                    # We have moved to a new page, get the name of the station
                    # at plot index iplot:
                    iplot = self.selected_sta[0]
                    if iplot >= len(self.plotted_sta):
                        # On last page, we may have less plots
                        iplot = 0
                    staname = self.plotted_sta[iplot]
                    self.selected_sta = [staname]
                    sta_events[cst.SELECTED] = self.selected_sta.copy()
                    self.graphs[iplot].addPlotState(cst.SELECTED, plot_now=True)
                else:
                    # Deselect the (single)previously selected station
                    if self.selected_sta[0] not in self.plotted_sta:
                        sta_events[~cst.SELECTED] = self.selected_sta.copy()
                        self.selected_sta = []
            else:
                # If a multi-selection is ongoing, we keep previously selected
                # stations when changing the grid page and we don't
                # automatically select a new station.
                sta_events[cst.SELECTED] = self.selected_sta.copy()

            # if self.selected_sta:
            #     # Ensure that we are in inspection mode
            #     self.mode = cst.MODE_INSPECTION
            if self.mode == cst.MODE_INSPECTION:
                # No station selected yet, select the first station
                self.selected_sta = self.plotted_sta[:1]
                self.graphs[0].addPlotState(cst.SELECTED, plot_now=True)
                sta_events[cst.SELECTED] = self.selected_sta.copy()

            # if self.mode == cst.INSPECTION_MODE:
            #     self.grabKeyboard()

            sta_events['PLOTTED'] = dict()
            for sta in old_plotted_sta:
                sta_events['PLOTTED'][sta] = False
            for sta in self.plotted_sta:
                sta_events['PLOTTED'][sta] = True

            self.grid_to_dependencies.emit({'UPDATE': True})
            self.send(sta_events)

    def clearGrid(self):
        if self.plotted_sta:
            for iplot, staname in enumerate(self.plotted_sta):
                self.graphs[iplot].clear()
                self.graphs[iplot].plot_to_grid.disconnect()
                self.removeItem(self.graphs[iplot])
            self.plotted_sta = None
            for blank in self.placeholders:
                self.removeItem(blank)
            self.placeholders = []
            # self.selected_sta = [] # Keep the selection during grid update
            self.hovered_sta = []

    @QtCore.Slot(str)
    def changeGridPage(self, page):
        self.ipage = int(page)
        print('Moving to page %d' % self.ipage)
        new_plotted_sta = cfg.stalist[self.ipage*cfg.nplots:min((self.ipage+1)*cfg.nplots, cfg.nsta)]
        # print(self.ipage*cfg.nplots, min((self.ipage+1)*cfg.nplots, cfg.nsta))
        self.createPlotsGrid(new_plotted_sta)

    @QtCore.Slot(str)
    def changeGridComponent(self, component):
        icomponent = int(component)
        self.component = list(cfg.dataset.getData(cfg.stalist[0]).components.keys())[icomponent]
        print('Working with component %s' % self.component)
        self.createPlotsGrid()

    @QtCore.Slot(dict)
    def updateGeometry(self):
        self.createPlotsGrid()
        self.grid_to_dependencies.emit({'PAGE': -1})

    # Directly from controller or dataset or via GridWidget
    @QtCore.Slot(dict)
    def updatePlots(self, sta_events):

        if sta_events['FROM'] == self.id:
            # This is the broadcast response from our own signal, just ignore
            return

        # print('GRID got', sta_events)

        if 'MODE' in sta_events:
            self.mode = sta_events['MODE']
            if self.mode == cst.MODE_VISUALISATION:
                # self.releaseKeyboard()
                self.setModeVisualisation()
            elif self.mode == cst.MODE_INSPECTION:
                # self.grabKeyboard()
                self.setModeInspection()
            elif self.mode == cst.MODE_CATEGORISATION:
                self.setModeCategorisation()

        if 'FILTER' in sta_events or 'SORTED' in sta_events:
            self.createPlotsGrid()
            self.grid_to_dependencies.emit({'PAGE': -1})
            return

        if 'COMPONENT' in sta_events:
            # self.createPlotsGrid()
            self.grid_to_dependencies.emit({'PAGE': self.ipage, 'UPDATE': True})
            return

        if 'PLOT_REQUEST' in sta_events:
            # We need to switch to another page before selecting a station
            # which is not plotted yet.
            staname = sta_events['PLOT_REQUEST']
            self.selected_sta = [staname]
            ista = cfg.stalist.index(staname)
            self.ipage = ista//cfg.nplots
            self.grid_to_dependencies.emit({'PAGE': self.ipage})
            return

        # No return after this line

        plot_to_update = []

        if 'CURRENT_CAT_GROUP' in sta_events:
            # The group of categories has changed
            for iplot, _ in enumerate(self.plotted_sta):
                # iplot = self.plotted_sta.index(staname)
                self.graphs[iplot].updateGroupCategory()
                plot_to_update.append(iplot)

        if 'CATEGORY_CHANGED' in sta_events:
            # with pg.BusyCursor():
            for staname, group, new_category in sta_events['CATEGORY_CHANGED']:
                if staname in self.plotted_sta:
                    # Note that you can change the category
                    # of a station which is not plotted...
                    iplot = self.plotted_sta.index(staname)
                    self.graphs[iplot].setCategory(group, new_category)
                    plot_to_update.append(iplot)

        if 'DISPLAY_FEATURE' in sta_events:
            # Update all the plots
            for staname in self.plotted_sta:
                iplot = self.plotted_sta.index(staname)
                self.graphs[iplot].setFeature(sta_events['DISPLAY_FEATURE'])
                plot_to_update.append(iplot)

        # States have changed for some stations, update the hovered/selected lists and plots
        for event, list_sta in sta_events.items():
            if event not in cst.STATE_EVENTS:
                continue

            # Remove stations which are not plotted
            list_sta = [sta for sta in list_sta if sta in self.plotted_sta]

            if event == cst.HOVERED:
                self.hovered_sta += [sta for sta in list_sta if sta not in self.hovered_sta]
                iplots = self.plotsIndices(list_sta)
                plot_to_update += iplots
                self.setPlotState(iplots, cst.HOVERED)
            elif event == ~cst.HOVERED:
                self.hovered_sta = [sta for sta in self.hovered_sta if sta not in list_sta]
                iplots = self.plotsIndices(list_sta)
                plot_to_update += iplots
                self.setPlotState(iplots, ~cst.HOVERED)
            elif event == cst.SELECTED:
                self.selected_sta += [sta for sta in list_sta if sta not in self.selected_sta]
                iplots = self.plotsIndices(list_sta)
                plot_to_update += iplots
                self.setPlotState(iplots, cst.SELECTED)
            elif event == ~cst.SELECTED:
                self.selected_sta = [sta for sta in self.selected_sta if sta not in list_sta]
                iplots = self.plotsIndices(list_sta)
                plot_to_update += iplots
                self.setPlotState(iplots, ~cst.SELECTED)

        # with pg.BusyCursor():
        plot_to_update = set(plot_to_update) # remove duplicates
        for iplot in plot_to_update:
            self.graphs[iplot].plot()

    # From a subplot (update the subplot, then repeater slot only)
    @QtCore.Slot()
    def signalFromSubplot(self, subplot_event):
        sta_events = dict()

        # For now it's always cst.HOVERED from a single plot
        staname = list(subplot_event.keys())[0]

        if self.hovered_sta and staname not in self.hovered_sta:
            # Restore the state of the previously hovered station
            previous_hovered_sta = self.hovered_sta[0]
            iplot = self.plotted_sta.index(previous_hovered_sta)
            self.graphs[iplot].removePlotState(cst.HOVERED, plot_now=True)
            sta_events[~cst.HOVERED] = [previous_hovered_sta]

        iplot = self.plotted_sta.index(staname)
        self.graphs[iplot].addPlotState(cst.HOVERED, plot_now=True)
        sta_events[cst.HOVERED] = [staname]
        self.hovered_sta = [staname]

        # Forward the signal to the controller, he knows what to do
        self.send(sta_events)

    def mousePressEvent(self, event):
        # print(self.itemAt(event.pos()))

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        no_modifiers = modifiers not in (QtCore.Qt.ShiftModifier, QtCore.Qt.ControlModifier)
        if (modifiers == QtCore.Qt.ShiftModifier and self.mode == cst.MODE_VISUALISATION) or \
           (modifiers == QtCore.Qt.ShiftModifier and self.mode == cst.MODE_INSPECTION) or \
           (no_modifiers and self.mode == cst.MODE_CATEGORISATION):
            # Change category
            if self.selected_sta:
                observed_sta = self.selected_sta
            else:
                observed_sta = self.hovered_sta

            cat_changed = []
            for staname in observed_sta:
                new_category = ''

                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    if cfg.cat_shift_left[cfg.current_grp] == '+':
                        new_category = cfg.getNextCategory(staname)
                    elif cfg.cat_shift_left[cfg.current_grp] == '-':
                        new_category = cfg.getPreviousCategory(staname)
                    # elif cfg.cat_shift_left in cfg.CATEGORIES:
                    #     new_category = cfg.cat_shift_left
                elif event.button() == QtCore.Qt.MouseButton.RightButton:
                    if cfg.cat_shift_right[cfg.current_grp] == '+':
                        new_category = cfg.getNextCategory(staname)
                    elif cfg.cat_shift_right[cfg.current_grp] == '-':
                        new_category = cfg.getPreviousCategory(staname)
                    # elif cfg.cat_shift_right in cfg.CATEGORIES:
                    #     new_category = cfg.cat_shift_right

                if new_category == '':
                    continue

                iplot = self.plotted_sta.index(staname)
                self.graphs[iplot].setCategory(cfg.current_grp, new_category, plot_now=True)
                cat_changed.append((staname, cfg.current_grp, new_category))

            if cat_changed:
                self.send({'CATEGORY_CHANGED': cat_changed})

        elif (modifiers == QtCore.Qt.ControlModifier and self.mode == cst.MODE_CATEGORISATION) or \
             (self.mode in (cst.MODE_VISUALISATION, cst.MODE_INSPECTION)):
            # Selection
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                # Select hovered station, i.e. replace selected_sta by hovered_sta
                if self.hovered_sta[0] in self.selected_sta:
                    # Remove hovered from selection
                    # For now, we assume one hovered station at a time
                    self.updateSelection(self.hovered_sta, [])
                    if not self.selected_sta and self.mode == cst.MODE_INSPECTION:
                        self.setModeVisualisation()
                else:
                    # Add hovered to selection
                    if len(self.selected_sta) > 1:
                        # If we have already selected more than 1 stations,
                        # we keep selecting new stations
                        self.updateSelection([], self.hovered_sta)
                    else:
                        # If we have only selected 1 station, either...
                        if modifiers == QtCore.Qt.ControlModifier:
                            # ...we add hovered station to the selection
                            self.updateSelection([], self.hovered_sta)
                        else:
                            # ...or we replace current selection by hovered station
                            self.updateSelection(self.selected_sta, self.hovered_sta)
                    if self.mode == cst.MODE_VISUALISATION:
                        self.setModeInspection()
            elif event.button() == QtCore.Qt.MouseButton.RightButton:
                if self.mode == cst.MODE_INSPECTION:
                    self.setModeVisualisation() # change that behaviour (context menu?)
                else:
                    # Just deselect everything
                    sta_events = {~cst.SELECTED: [], cst.SELECTED: []}
                    for staname in self.selected_sta:
                        iplot = self.plotted_sta.index(staname)
                        self.graphs[iplot].removePlotState(cst.SELECTED, plot_now=True)
                        sta_events[~cst.SELECTED].append(staname)
                    self.selected_sta = []
                    self.send(sta_events)

    def createShortcuts(self):

        # Handy aliases
        sc = self.shortcut
        nokey = QtGui.QKeySequence()
        Qsc = QtWidgets.QShortcut

        ## Modes
        Qsc(QtGui.QKeySequence(cst.MODES_KEY[cst.MODE_VISUALISATION]),
            self, self.setModeVisualisation)
        Qsc(QtGui.QKeySequence(cst.MODES_KEY[cst.MODE_INSPECTION]),
            self, self.setModeInspection)
        Qsc(QtGui.QKeySequence(cst.MODES_KEY[cst.MODE_CATEGORISATION]),
            self, self.setModeCategorisation)

        # Movements
        sc['move_up'] = Qsc(nokey, self,
                            functools.partial(self.moveSelection,
                                              QtCore.Qt.Key_Up))
        sc['move_down'] = Qsc(nokey, self,
                              functools.partial(self.moveSelection,
                                                QtCore.Qt.Key_Down))
        sc['move_left'] = Qsc(nokey, self,
                              functools.partial(self.moveSelection,
                                                QtCore.Qt.Key_Left))
        sc['move_right'] = Qsc(nokey, self,
                               functools.partial(self.moveSelection,
                                                 QtCore.Qt.Key_Right))
        # Next and previous page
        def prevPage():
            self.grid_to_dependencies.emit({'PAGE': self.ipage - 1})
        def nextPage():
            self.grid_to_dependencies.emit({'PAGE': self.ipage + 1})
        sc['page_prev'] = Qsc(nokey, self, prevPage)
        sc['page_next'] = Qsc(nokey, self, nextPage)

        # Categories
        sc['cat_toggle'] = Qsc(QtGui.QKeySequence('Space'), self,
                               functools.partial(self.setCategory, 'toggle'))
        sc['cat_prev'] = Qsc(QtGui.QKeySequence('-'), self,
                             functools.partial(self.setCategory, '-'))
        sc['cat_next'] = Qsc(QtGui.QKeySequence('+'), self,
                             functools.partial(self.setCategory, '+'))
        sc['cat'] = {}
        for k in '0123456789':
            sc['cat'][k] = Qsc(QtGui.QKeySequence(k), self,
                               functools.partial(self.setCategory,
                                                 'pick',
                                                 key=cst.QT_KEYS[k]))

        # Delete key
        sc['filter_out'] = Qsc(QtGui.QKeySequence(), self, self.filterStations)
        sc['flag'] = Qsc(QtGui.QKeySequence(), self, self.flagStations)

    def setDefaultShortcuts(self):

        # Disable selector
        self.shortcut['move_up'].setKey(QtGui.QKeySequence())
        self.shortcut['move_down'].setKey(QtGui.QKeySequence())

        # Next and previous page
        self.shortcut['page_prev'].setKey(QtGui.QKeySequence('Left'))
        self.shortcut['page_next'].setKey(QtGui.QKeySequence('Right'))

        # Categories
        # ...set in self.createShortcuts()

        # Delete key
        self.shortcut['filter_out'].setKey(QtGui.QKeySequence('Del'))
        self.shortcut['flag'].setKey(QtGui.QKeySequence())

    def setModeVisualisation(self):

        if self.mode == cst.MODE_VISUALISATION:
            # Already in visualisation mode
            return

        print('Entering visualisation mode.')
        # self.releaseKeyboard()
        self.mode = cst.MODE_DEFAULT

        self.setDefaultShortcuts()

        sta_events = {'MODE': self.mode, ~cst.SELECTED: [], cst.SELECTED: []}
        for staname in self.selected_sta:
            iplot = self.plotted_sta.index(staname)
            self.graphs[iplot].removePlotState(cst.SELECTED, plot_now=True)
            sta_events[~cst.SELECTED].append(staname)
        self.selected_sta = []
        self.send(sta_events)

    def setModeInspection(self):

        if self.mode == cst.MODE_INSPECTION:
            # Already in inspection mode
            return

        # Selection of stations with the keyboard
        if self.hovered_sta:
            self.selected_sta = self.hovered_sta
        else:
            # Select the first plotted station
            self.selected_sta = [self.plotted_sta[0]]

        print('Entering inspection mode.')
        self.mode = cst.MODE_INSPECTION
        # self.grabKeyboard()

        # Selector
        self.shortcut['move_up'].setKey(QtGui.QKeySequence())
        self.shortcut['move_down'].setKey(QtGui.QKeySequence())
        self.shortcut['move_left'].setKey(QtGui.QKeySequence('Left'))
        self.shortcut['move_right'].setKey(QtGui.QKeySequence('Right'))
        # Next and previous page
        self.shortcut['page_prev'].setKey(QtGui.QKeySequence('Ctrl+Left'))
        self.shortcut['page_next'].setKey(QtGui.QKeySequence('Ctrl+Right'))
        # Delete key
        self.shortcut['filter_out'].setKey(QtGui.QKeySequence('Del'))
        self.shortcut['flag'].setKey(QtGui.QKeySequence())

        sta_events = {'MODE': self.mode, cst.SELECTED: []}
        for staname in self.selected_sta:
            iplot = self.plotted_sta.index(staname)
            self.graphs[iplot].addPlotState(cst.SELECTED, plot_now=True)
            sta_events[cst.SELECTED].append(staname)
        self.send(sta_events)

    def setModeCategorisation(self):

        if self.mode == cst.MODE_CATEGORISATION:
            # Already in categorisation mode
            return

        # Selection of stations with the keyboard
        # if self.hovered_sta:
        #     self.selected_sta = self.hovered_sta
        # else:
        #     # Select the first plotted station
        #     self.selected_sta = [self.plotted_sta[0]]

        print('Entering categorisation mode.')
        self.mode = cst.MODE_CATEGORISATION

        # Selector
        self.shortcut['move_up'].setKey(QtGui.QKeySequence('Up'))
        self.shortcut['move_down'].setKey(QtGui.QKeySequence('Down'))
        self.shortcut['move_left'].setKey(QtGui.QKeySequence('Left'))
        self.shortcut['move_right'].setKey(QtGui.QKeySequence('Right'))
        # Next and previous page
        self.shortcut['page_prev'].setKey(QtGui.QKeySequence('Ctrl+Left'))
        self.shortcut['page_next'].setKey(QtGui.QKeySequence('Ctrl+Right'))
        # Categories
        #TODO: new Qt 6.x
        # self.shortcut['cat_prev'].setKeys([QtGui.QKeySequence('-'),
        #                                    QtGui.QKeySequence('Down')],
        #                                   self,
        #                                   functools.partial(self.setCategory, '-'))
        # self.shortcut['cat_next'].setKeys([QtGui.QKeySequence('+'),
        #                                    QtGui.QKeySequence('Up')],
        #                                   self,
        #                                   functools.partial(self.setCategory, '+'))
        # Delete key
        self.shortcut['flag'].setKey(QtGui.QKeySequence('Del'))
        self.shortcut['filter_out'].setKey(QtGui.QKeySequence())

        # sta_events = {'MODE': self.mode, cst.SELECTED: []}
        # for staname in self.selected_sta:
        #     iplot = self.plotted_sta.index(staname)
        #     self.graphs[iplot].addPlotState(cst.SELECTED, plot_now=True)
        #     sta_events[cst.SELECTED].append(staname)
        # self.send(sta_events)

        self.send({'MODE': self.mode})

    def _toggleCategory(self, current_sta_category, target=''):

        if target == '':
            cat_target = cfg.cat_switch[cfg.current_grp]
        else:
            cat_target = target

        if cfg.current_grp == cfg.GRP_QUALITY:
            new_category = cfg.CAT_DEFAULT if current_sta_category != cfg.CAT_DEFAULT else cat_target
        else:
            new_category = None if current_sta_category else cat_target

        return new_category

    def _pickCategory(self, key):

        if key == QtCore.Qt.Key_0:
            if cfg.current_grp == cfg.GRP_QUALITY:
                new_category = cfg.CAT_DEFAULT
            else:
                new_category = None
        else:
            if key in cfg.cat_keys[cfg.current_grp]:
                new_category = cfg.cat_keys[cfg.current_grp][key]
            else:
                return ''

        return new_category

    def _nextCategory(self, icategory):

        if icategory + 1 >= len(cfg.CATEGORIES[cfg.current_grp]):
            return ''
        return cfg.CATEGORIES[cfg.current_grp][icategory + 1]

    def _prevCategory(self, icategory):

        if icategory - 1 < 0:
            if cfg.current_grp == cfg.GRP_QUALITY:
                return ''
            else:
                new_category = None
        else:
            new_category = cfg.CATEGORIES[cfg.current_grp][icategory - 1]

        return new_category

    def setCategory(self, method, key=None, target=''):

        if self.selected_sta:
            observed_sta = self.selected_sta
        else:
            observed_sta = self.hovered_sta

        sta_events = {'CATEGORY_CHANGED': []}
        for staname in observed_sta:
            current_sta_category = cfg.sta_category[staname][cfg.current_grp]
            # Toggling the current station category
            if current_sta_category:
                icategory = cfg.CATEGORIES[cfg.current_grp].index(current_sta_category)
            else:
                if cfg.current_grp == cfg.GRP_QUALITY:
                    icategory = 1
                else:
                    icategory = -1 # -1 + 1 = 0 (first not-None category); -1 - 1 = -2 (return)

            if method == 'toggle':
                current_cat = cfg.sta_category[staname][cfg.current_grp]
                new_category = self._toggleCategory(current_cat, target=target)
            elif method == '+':
                new_category = self._nextCategory(icategory)
            elif method == '-':
                new_category = self._prevCategory(icategory)
            else:
                new_category = self._pickCategory(key)

            if new_category == '':
                continue # no change

            if staname in self.plotted_sta:
                iplot = self.plotted_sta.index(staname)
                self.graphs[iplot].setCategory(cfg.current_grp, new_category, plot_now=True)
            sta_events['CATEGORY_CHANGED'].append((staname, cfg.current_grp, new_category))

        if sta_events['CATEGORY_CHANGED']:
            self.send(sta_events)

        if cfg.auto_advance and method in ('toggle', 'pick'):
            # If +/- is pressed, don't move, the user may need to press them several times
            self.moveSelection(QtCore.Qt.Key_Right)

    def flagStations(self):

        if cfg.current_grp != cfg.GRP_QUALITY:
            return

        # cfg.CAT_BAD is used to flag stations
        # We pretend that current category is DEFAULT
        self.setCategory('toggle', cfg.CAT_DEFAULT, target=cfg.CAT_BAD)

    def filterStations(self):

        #TODO
        print('Not implemented yet!')

    def moveSelection(self, key):
        if not self.selected_sta:
            return

        if len(self.selected_sta) > 1:
            print("Can't move with the keyboard during multi-selection.")
            return

        ista = self.plotted_sta.index(self.selected_sta[0])
        inext = ista

        if key == QtCore.Qt.Key_Right:
            inext += 1
        elif key == QtCore.Qt.Key_Left:
            inext += -1
        elif key == QtCore.Qt.Key_Up:
            inext += -self.ncols
        elif key == QtCore.Qt.Key_Down:
            inext += self.ncols

        if inext < 0:
            if self.ipage > 0:
                inext += cfg.nplots
                self.selected_sta = [inext] # /!\ replaced in createPlotsGrid
                # We use an index because we don't know yet which station will be
                # displayed in this subplot after changing the page.
                # self.stations_combo.setCurrentIndex(self.ipage - 1)
                self.grid_to_dependencies.emit({'PAGE': self.ipage - 1})
        elif inext >= len(self.plotted_sta):
            if self.ipage*cfg.nplots + inext < cfg.nsta:
                inext -= cfg.nplots
                self.selected_sta = [inext] # /!\ idem
                # self.stations_combo.setCurrentIndex(self.ipage + 1)
                self.grid_to_dependencies.emit({'PAGE': self.ipage + 1})
        else:
            next_selected_sta = [self.plotted_sta[inext]]
            self.updateSelection(self.selected_sta, next_selected_sta)

    def updateSelection(self, previously_selected, newly_selected):
        sta_events = dict()
        plot_to_update = []

        if previously_selected:
            sta_events[~cst.SELECTED] = []
            self.selected_sta = [sta for sta in self.selected_sta if sta not in previously_selected]
            sta_events[~cst.SELECTED] = previously_selected
            # There are subplots to clean before moving
            iplots = self.plotsIndices(previously_selected)
            plot_to_update += iplots
            self.setPlotState(iplots, ~cst.SELECTED)

        if newly_selected:
            sta_events[cst.SELECTED] = []
            self.selected_sta += [sta for sta in newly_selected if sta not in self.selected_sta]
            sta_events[cst.SELECTED] = newly_selected
            # Update the newly selected plots
            iplots = self.plotsIndices(newly_selected)
            plot_to_update += iplots
            self.setPlotState(iplots, cst.SELECTED)

        for iplot in plot_to_update:
            self.graphs[iplot].plot()

        # if self.selected_sta and self.mode != cst.MODE_INSPECTION:
        #     self.mode = cst.MODE_INSPECTION
        #     sta_events['MODE'] = cst.MODE_INSPECTION
        # elif not self.selected_sta and self.mode != cst.MODE_DEFAULT:
        #     self.mode = cst.MODE_DEFAULT
        #     sta_events['MODE'] = cst.MODE_DEFAULT

        self.send(sta_events)

    def leaveEvent(self, event):
        #TODO: we have a non-blocking bug here sometimes
        previously_hovered_sta = self.hovered_sta.copy()
        for staname in self.hovered_sta:
            # Restore the state of the previously hovered station
            iplot = self.plotted_sta.index(staname)
            self.graphs[iplot].removePlotState(cst.HOVERED, plot_now=True)
        self.hovered_sta = []

        # Forward the signal to the controller, he knows what to do
        self.send({~cst.HOVERED: previously_hovered_sta})

    def plotsIndices(self, stalist):

        return [self.plotted_sta.index(staname) for staname in stalist]

    def setPlotState(self, indices, state):

        for iplot in indices:
            if state > 0:
                self.graphs[iplot].addPlotState(state)
            else:
                self.graphs[iplot].removePlotState(~state)

    def updateTimeRange(self, timerange):
        self.timerange = timerange
        for plot in self.graphs:
            plot.setTimerange(self.timerange)
        if timerange['start']:
            start_date = timerange['start']
            end_date = timerange['end']
            print('Set timerange:', start_date, 'to', end_date)

    def updateYRange(self, yrange):
        if 'ymin' in yrange:
            self.yrange['ymin'] = yrange['ymin']
        if 'ymax' in yrange:
            self.yrange['ymax'] = yrange['ymax']

        self.yrange['bound_type'] = yrange['bound_type']
        self.yrange['reference_level'] = yrange['reference_level']

        if self.yrange['ymin'] and self.yrange['ymax']:
            print('Set {:s} yrange: {:+.2f} to {:+.2f} (wrt {:s})'.\
                  format(self.yrange['bound_type'],
                         self.yrange['ymin'],
                         self.yrange['ymax'],
                         self.yrange['reference_level']))
        else:
            print('Disable Y-range sync')

        for plot in self.graphs:
            plot.setOrdinateRange(self.yrange)

    def send(self, message, sender=None):
        if not sender:
            sender = self.id
        message['FROM'] = sender
        self.gui_to_ctrl.emit(message)


class GridSubplot(pg.ViewBox):

    plot_to_grid = QtCore.Signal(dict)

    def __init__(self, iplot, staname=None, state=cst.DEFAULT,
                 timerange={}, yrange={},
                 plot_now=False, placeholder=False):
        pg.ViewBox.__init__(self, enableMenu=False)

        print('Creating subplot', iplot)

        self.iplot = iplot
        self.plot_state = state
        self.downsampling_rate = cfg.downsampling_rate
        self.feature = cfg.displayed_feature
        self.feature_text = ""
        self.feature_text_item = None
        self.model_item = None
        self.title = ""

        self.first_plot = True # not plotted yet

        self.no_data = False

        if timerange:
            self.timerange = timerange
        else:
            self.timerange = {'start': None, 'end': None}

        if yrange:
            self.yrange = yrange
        else:
            self.yrange = {'ymin': None,
                           'ymax': None,
                           'bound_type': 'absolute',
                           'reference_level': 'zero'}

        self.placeholder = placeholder
        if self.placeholder:
            self.plot()
            self.focusInEvent = lambda x: False
            return

        self.setAcceptHoverEvents(True)

        if staname is None and plot_now:
            raise ValueError('Asking to plot an unspecified station.')
        else:
            self.setStation(staname, plot_now=plot_now)

    # Needed to make GridSubplot pickleable for multiprocessing
    # def __reduce__(self):
    #     return (GridSubplot, (self.iplot, self.staname))

    def hoverEnterEvent(self, event):
        # self.setFocus()
        # self.setPlotState(cst.HOVERED) # done by the grid
        self.plot_to_grid.emit({self.staname: 'ENTER'})

    def hoverLeaveEvent(self, event):
        # self.clearFocus()
        # self.setPlotState(cst.DEFAULT) # done by the grid
        # self.plot_to_grid.emit({self.staname: 'LEAVE'})
        pass

    # def keyPressEvent(self, event):
    #     pass

    def mouseReleaseEvent(self, event):
        print('Release!', event)

    def focusInEvent(self, focus):
        print('Focus on', self.staname)

    # def focusOutEvent(self, focus):
    #     print('Focus out', self.staname)

    def setStation(self, staname, plot_now=True):
        self.staname = staname
        self.group_category = cfg.current_grp
        self.plot_category = cfg.sta_category[staname][cfg.current_grp]
        self.placeholder = False
        if plot_now:
            self.plot()

    def getPlotState(self): # getState() is a method of pg.ViewBox
        return self.plot_state

    def setPlotState(self, state, plot_now=False):
        self.plot_state = state
        # if state in (cst.HOVERED, cst.SELECTED):
        #     self.setFocus()
        # else:
        #     self.clearFocus()
        if plot_now and not self.placeholder:
            self._updatePlot()

    def addPlotState(self, state, plot_now=False):
        self.plot_state |= state
        if plot_now and not self.placeholder:
            self._updatePlot()

    def removePlotState(self, state, plot_now=False):
        self.plot_state = ~state & self.plot_state
        # Don't use ^= state in case we remove 'state' several times
        if plot_now and not self.placeholder:
            self._updatePlot()

    # Not used
    def togglePlotState(self, state, plot_now=False):
        self.plot_state ^= state
        if plot_now and not self.placeholder:
            self._updatePlot()

    def setCategory(self, group, category, plot_now=False):
        self.group_category = group
        self.plot_category = category
        if plot_now and not self.placeholder:
            self._updatePlot()

    def updateGroupCategory(self, plot_now=False):
        self.group_category = cfg.current_grp
        self.plot_category = cfg.sta_category[self.staname][cfg.current_grp]
        if plot_now and not self.placeholder:
            self._updatePlot()

    def setFeature(self, feature, plot_now=False):
        self.feature = feature
        if plot_now and not self.placeholder:
            self._updateFeature()

    def downsample(self, t, Z, downsampling_rate=0):
        if not downsampling_rate:
            downsampling_rate = self.downsampling_rate
        else:
            # We can temporarily force another downsampling rate
            pass

        if downsampling_rate > 1:
            if t.shape[0] >= cfg.downsampling_threshold:
                if cfg.downsampling_method == 'naive':
                    t = t[::downsampling_rate]
                    Z = Z[::downsampling_rate]
                else:
                    raise ValueError('Unknown downsampling method')

        return t, Z

    def createTitle(self, state, name_only=False, no_data=False):

        if self.plot_category and self.group_category == cfg.current_grp:
            plot_category = self.plot_category
            cat_name = cfg.cat_names[cfg.current_grp][self.plot_category]
        else:
            plot_category = cfg.CAT_DEFAULT
            cat_name = ''

        nodata_text = ''
        if no_data:
            nodata_text = '!NO DATA! '

        if name_only or not cat_name:
            text_template = '<span style="color: {color};">' \
                            '{nodata}<span style="font-weight: bold;">{station}</span> ' \
                            '</span>'
            text_template = text_template.replace('}', ':s}')
            self.title = text_template.format(station=self.staname,
                                              color=thm.station_name_color[plot_category][state],
                                              nodata=nodata_text)
        else:
            text_template = '<span style="color: {color};">' \
                            '{nodata}<span style="font-weight: bold;">{station}</span> ' \
                            '{category}' \
                            '</span>' # <br />' \
            text_template = text_template.replace('}', ':s}')
            self.title = text_template.format(station=self.staname,
                                              category='[' + cat_name + ']' if self.plot_category != cfg.CAT_NEUTRAL else '',
                                              color=thm.station_name_color[plot_category][state],
                                              nodata=nodata_text)

        return self.title

    def createFeatureText(self, state):

        if self.plot_category and self.group_category == cfg.current_grp:
            plot_category = self.plot_category
            cat_name = cfg.cat_names[cfg.current_grp][self.plot_category]
        else:
            plot_category = cfg.CAT_DEFAULT
            cat_name = ''

        if self.no_data and not self.feature:
            self.feature_text = 'NO DATA'
            return self.feature_text

        feature_value = cfg.features.getStationsFeature(self.feature,
                                                        staname=self.staname)

        if self.no_data:
            if isinstance(feature_value, str):
                if not feature_value or self.feature in ('.DEFAULT', '.NAMES'):
                    self.feature_text = 'NO DATA'
                    return self.feature_text
            elif np.isnan(feature_value):
                self.feature_text = 'NO DATA'
                return self.feature_text

        #feature_info = cfg.features.getInfo(self.feature)
        feature_str = cfg.features.formatFeature(self.feature, feature_value)

        if self.no_data:
            feature_str += ' (NO DATA)'

        #TODO: state-independent for now, decide what works best
        #text_template = '<span style="color: {color};">{feature}</span>'
        #text_template = text_template.replace('}', ':s}')
        #self.feature_text = text_template.format(feature=feature_value)
        #                                  color=thm.station_name_color[plot_category][state])
        self.feature_text = feature_str

        return self.feature_text

    def plot(self):

        if self.placeholder:
            self.setBackgroundColor(thm.figure_color['background'])
            # self.border = thm.figure_background_color
            return

        if not self.first_plot:
            self._updatePlot()
            self._updateFeature()
            return
        self.first_plot = False

        data = cfg.dataset.getData(self.staname)
        t = data.t
        Z = data.data
        if np.all(np.isnan(Z)):
            self.no_data = True
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

        if self.plot_category and self.group_category == cfg.current_grp:
            plot_category = self.plot_category
        else:
            plot_category = cfg.CAT_DEFAULT

        # self.clear()
        # When multiple states are combined,
        # we pick a dominant one for plotting
        if cst.SELECTED & self.plot_state:
            state = cst.SELECTED
        elif cst.HOVERED & self.plot_state:
            state = cst.HOVERED
        else:
            state = cst.DEFAULT

        self.setBackgroundColor(thm.ax_color[plot_category][state])
        self.setBorder(thm.ax_spines_color[plot_category][state])

        # if np.all(np.isnan(Z)):
        #     self.createTitle(state, no_data=True)
        #     self.title_item = pg.TextItem(html=self.title,
        #                                   fill=thm.figure_color['background'] + 'E0')
        #     # self.addItem(self.title)  # Use coordinate system
        #     self.title_item.setParentItem(self)
        #     self.title_item.setPos(5, 5)
        #     return

        for event in events:
            self.event_line = pg.InfiniteLine(event,
                                              pen=pg.mkPen(color=thm.events_color[plot_category][state],
                                                           width=1))
            self.addItem(self.event_line)
            self.event_line.setZValue(6)

        t, Z = self.downsample(t, Z)
        self.scatter = pg.ScatterPlotItem(t, Z,
                                          pen=None, symbol='o', size=2,
                                          brush=thm.data_color[plot_category][state])
        self.addItem(self.scatter)
        self.scatter.setZValue(5)

        # self.title = pg.TextItem(self.staname, color=thm.station_name_color[self.plot_category][state])
        # anchor=(0.05, 0.89),
        # ax.addItem(title)

        #         horizontalalignment='left',
        #         verticalalignment='center', transform=ax.transAxes)
        # for spine in ax.spines:
        #     ax.spines[spine].set_color(ax_spines_color[category][state])
        #     ax.spines[spine].set_linewidth(ax_spines_width[category][state])
        # ax.axes.get_xaxis().set_visible(False)
        # ax.axes.get_yaxis().set_visible(False)
        self.setTimerange(self.timerange)
        self.setOrdinateRange(self.yrange)

        self.createTitle(state, name_only=True)
        self.title_item = pg.TextItem(html=self.title,
                                      fill=thm.figure_color['background'] + 'E0')
        # self.addItem(self.title)  # Use coordinate system
        self.title_item.setParentItem(self)
        self.title_item.setPos(5, 5)

        if self.feature or self.no_data:
            self._updateFeature()

    def setOrdinateRange(self, yrange):

        Z = cfg.data[self.staname].data
        if np.all(np.isnan(Z)):
            return

        self.yrange = yrange

        if yrange.get('ymin', None) is None and \
           yrange.get('ymax', None) is None:
            Zmin, Zmax = np.nanmin(Z), np.nanmax(Z)
            if np.isnan(Zmin):
                Zmin = -1.
            if np.isnan(Zmax):
                Zmax = 1.

            if np.abs(Zmax - Zmin) < 1e-15:
                # Lower and upper bound are identical
                # Make sure the range is non-zero
                if np.abs(Zmin) < 1e-15:
                    Zmin -= 1e-12
                    Zmax += 1e-12
                else:
                    Zmin *= (1. - 1e-12)
                    Zmax *= (1. + 1e-12)
            self.setYRange(Zmin, Zmax, padding=0.05)
            return

        ymin_new = yrange.get('ymin', None)
        ymax_new = yrange.get('ymax', None)
        bound_type = yrange['bound_type']
        reference_level = yrange['reference_level']

        Z = np.copy(cfg.data[self.staname].data)

        if 'detrended' in bound_type:
            Z = signal.detrend(Z)

        if reference_level == 'zero':
            Z_ref = 0.0 # Default
        elif reference_level == 'initial':
            Z_ref = Z[0]
        elif reference_level == 'median':
            Z_ref = np.nanmedian(Z)
        elif reference_level == 'mean':
            Z_ref = np.nanmean(Z)
        Z -= Z_ref

        if bound_type == 'absolute':
            # Default
            #ymin_default *= 1 - 0.1*np.sign(ymin_default)
            #ymax_default *= 1 + 0.1*np.sign(ymax_default)
            ymin = ymin_new if ymin_new else np.nanmin(Z)
            ymax = ymax_new if ymax_new else np.nanmax(Z)
        elif bound_type == 'percentile':
            if not ymin_new:
                ymin_new = 100.
            if not ymax_new:
                ymax_new = 100.

            if abs(ymin_new) > 1.0:
                ymin_new /= 100.
            if abs(ymax_new) > 1.0:
                ymax_new /= 100.

            ymin = np.nanmin(Z) # default
            if ymin_new < 0:
                if (Z < 0.).any():
                    ymin = -np.quantile(-Z[Z < 0.], [-ymin_new])[0]
            else:
                if (Z > 0.).any():
                    ymin = np.quantile(Z[Z > 0.], [ymin_new])[0]

            ymax = np.nanmax(Z) # default
            if ymax_new > 0:
                if (Z > 0.).any():
                    ymax = np.quantile(Z[Z > 0.], [ymax_new])[0]
            else:
                if (Z < 0.).any():
                    ymax = -np.quantile(-Z[Z < 0.], [-ymax_new])[0]
        elif bound_type == 'fraction':
            if not ymin_new:
                ymin_new = 100.
            if not ymax_new:
                ymax_new = 100.

            if abs(ymin_new) > 1.0:
                ymin_new /= 100.
            if abs(ymax_new) > 1.0:
                ymax_new /= 100.

            ymin = np.nanmin(Z) # default
            if ymin_new < 0:
                if (Z < 0.).any():
                    ymin = abs(ymin_new) * np.nanmin(Z)
            else:
                if (Z > 0.).any():
                    ymin = ymin_new * np.nanmax(Z)

            ymax = np.nanmax(Z) # default
            if ymax_new > 0:
                if (Z > 0.).any():
                    ymax = ymax_new * np.nanmax(Z)
            else:
                if (Z < 0.).any():
                    ymax = abs(ymax) * np.nanmin(Z)
        elif bound_type == 'sigma' or bound_type == 'sigma (detrended)':
            std = np.std(Z)
            ymin = ymin_new * std if ymin_new else np.nanmin(Z)
            ymax = ymax_new * std if ymax_new else np.nanmax(Z)
        elif bound_type == 'MAD' or bound_type == 'MAD (detrended)':
            mad = np.median(np.abs(Z - np.median(Z)))
            ymin = ymin_new * mad if ymin_new else np.nanmin(Z)
            ymax = ymax_new * mad if ymax_new else np.nanmax(Z)

        # print(Z_ref, ymin, ymax)
        ymin += Z_ref
        ymax += Z_ref
        if np.abs(ymax - ymin) < 1e-15:
            # Lower and upper bound are identical
            # Make sure the range is non-zero
            if np.abs(ymin) < 1e-15:
                ymin -= 1e-12
                ymax += 1e-12
            else:
                ymin *= (1. - 1e-12)
                ymax *= (1. + 1e-12)

        self.setYRange(ymin, ymax, padding=0.0)

    def setTimerange(self, timerange):

        self.timerange = timerange

        start_date = self.timerange['start']
        end_date = self.timerange['end']
        if not start_date and not end_date:
            t = cfg.data[self.staname].t
            istart = 0
            while np.isnan(t[istart]):
                i += 1
            iend = -1
            while np.isnan(t[iend]):
                i -= 1
            self.setXRange(t[istart], t[iend], padding=0)
            return

        start_range = time.mktime(start_date.timetuple())
        end_range = time.mktime(end_date.timetuple())

        self.setXRange(start_range, end_range, padding=0)

    def _updatePlot(self):

        if self.plot_category and self.group_category == cfg.current_grp:
            category = self.plot_category
        else:
            category = cfg.CAT_DEFAULT

        # When multiple states are combined,
        # we pick a dominant one for plotting
        if cst.SELECTED & self.plot_state:
            state = cst.SELECTED
        elif cst.HOVERED & self.plot_state:
            state = cst.HOVERED
        else:
            state = cst.DEFAULT

        self.setBackgroundColor(thm.ax_color[category][state])
        self.setBorder(pg.mkPen(color=thm.ax_spines_color[category][state],
                                size=thm.ax_spines_width[category][state]))
        self.scatter.setBrush(thm.data_color[category][state])

        # Look better without any change with state
        if state in (cst.SELECTED, cst.HOVERED):
            self.createTitle(cst.DEFAULT)
        else:
            self.createTitle(cst.DEFAULT, name_only=True)
        self.title_item.setHtml(self.title)

        if self.downsampling_rate != 1 and cfg.best_quality_on_hover:
            if state in (cst.SELECTED, cst.HOVERED):
                downsampling_rate = 1  # best quality
            else:
                downsampling_rate = self.downsampling_rate  # restore default
            # Since it is not possible to plot in another thread,
            # we may only plot with the best quality when the
            # user interact with the plot (hovering or selection).
            data = cfg.dataset.getData(self.staname)
            t = data.t
            Z = data.data
            t, Z = self.downsample(t, Z, downsampling_rate)
            self.scatter.setData(t, Z)
            if cfg.keep_best_quality:
                # Henceforth, this plot is not downsampled
                self.downsampling_rate = 1

    def _updateFeature(self):

        if not self.feature and not self.no_data:
            return

        # When multiple states are combined,
        # we pick a dominant one for plotting
        if cst.SELECTED & self.plot_state:
            state = cst.SELECTED
        elif cst.HOVERED & self.plot_state:
            state = cst.HOVERED
        else:
            state = cst.DEFAULT

        if self.model_item:
            self.removeItem(self.model_item)
        if self.feature_text_item:
            self.removeItem(self.feature_text_item)

        if 'MODELS.' in self.feature:
            _, selected_model, _ = self.feature.split('.')
            fitted_model = cfg.models[selected_model].fitted_models[self.staname]
            if fitted_model is not None:
                # self.model_item = pg.PlotCurveItem(t, fitted_model, pen=pg.mkPen(color='#FF0000', width=2),
                #                               antialias=True, connect='finite')
                # Note: no downsampling on the model (for now at least)
                t = cfg.dataset.getData(self.staname).t
                self.model_item = pg.ScatterPlotItem(t, fitted_model,
                                                     pen=None,
                                                     brush='#FF0000',
                                                     size=1,
                                                     alpha=0.5)
                self.addItem(self.model_item)
                self.model_item.setZValue(10)

        if self.feature not in ('.DEFAULT', '.NAMES') or self.no_data:
            self.createFeatureText(state)
            #self.feature_text_item = pg.TextItem(html=self.feature_text,
            self.feature_text_item = pg.TextItem(self.feature_text,
                                                 #anchor=(1, 1),
                                                 anchor=(0, 0),
                                                 color='#FF0000',
                                                 fill=thm.figure_color['background'] + 'E0') # 0xC0 = alpha 0.75
            # self.addItem(self.title)  # Use coordinate system
            self.feature_text_item.setParentItem(self)
            #TODO: doesn't work because self.screenGeometry() can be None
            #width = self.screenGeometry().width()
            #height = self.screenGeometry().height()
            #self.feature_text_item.setPos(width - 5, height - 5)
            self.feature_text_item.setPos(5, 25)
