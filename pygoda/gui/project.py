# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import os
import functools
import sys

import numpy as np
import scipy as sp

import config as cfg
import constants as cst
from themes import gui_themes as thm
import controller as ctl
from datasets import dataset
# from datasets import timeseries as ts
from datasets import timeseries_features as ts_features
from datasets import fit_data
from datasets import export_data
import projects
from . import data_widgets
from . import category_widgets
from . import features
from . import features_widgets
from . import filter_widgets
from . import grid
from . import grid_widgets
from . import mapcartopy
from . import mapleaflet
from . import largeplot


class ProjectWindow(QtWidgets.QMainWindow):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self, project):
        QtWidgets.QMainWindow.__init__(self)

        # Store project object and basic GUI setup
        self.project = project
        self.project_name = self.project.name
        cfg.project_name = self.project_name #TODO: change that later
        self.setWindowTitle('Pygoda - %s' % (self.project_name))
        self.setObjectName(self.project_name)
        self.id = id(self) # used to 'sign' signals

        # Read infos for the project
        self.project.readProject()

        # Load the configuration (and make it global)
        self.project.loadConfig(set_globals=True)

        # Load theme
        cfg.themes = thm.Themes(self.project.themes_filepaths)

        # Create the dataset object
        #TODO: make this cleaner
        cfg.basedir = self.project.basedir
        cfg.basedir_cat = self.project.cat_lists_path
        cfg.stations_list = self.project.stations
        cfg.nsta_max = self.project.nsta_max
        cfg.dataset = dataset.DataSetObject(self.project.data_path,
                                            self.project.data_desc)

        # Load the data
        load_params = {'stalist': cfg.stations_list,
                       'nsta_max': cfg.nsta_max}
        print('Loading the data...')
        cfg.dataset.loadData(load_on_the_fly=cfg.load_on_the_fly,
                             load_nsta=cfg.load_nsta,
                             **load_params)

        # Create config shortcuts for CONSTANT data
        cfg.dataset.createConfigShortcuts()

        # Define some global variables for NON-CONSTANT properties
        # Proxy to stalist taking into account sorting and filtering
        cfg.stalist = cfg.stalist_all.copy()
        cfg.sta_category_all = cfg.dataset.getCategories()
        cfg.sta_category = cfg.sta_category_all.copy()
        cfg.nsta = len(cfg.stalist)
        cfg.plotted_sta = {staname: False for staname in cfg.stalist_all}

        # Set the default data component to display
        #TODO: set that in the project config file
        cfg.data_component = cfg.dataset.getData(cfg.stalist[0]).main_component

        # Menu
        self.menu = self.menuBar()

        # Project
        self.project_menu = self.menu.addMenu("Project")
        self.open_folder = QtWidgets.QAction("Open project folder")
        path = QtCore.QDir.toNativeSeparators(cfg.basedir)
        self.open_folder.triggered.connect(functools.partial(\
                                                QtGui.QDesktopServices.openUrl, \
                                                QtCore.QUrl.fromLocalFile(path)))
        self.project_menu.addAction(self.open_folder)
        self.export_menu = self.project_menu.addMenu("Export...")
        self.export_list = QtWidgets.QAction("List of stations with attributes")
        self.export_list.triggered.connect(self.exportList)
        self.export_menu.addAction(self.export_list)
        self.export_data = QtWidgets.QAction("Data set")
        self.export_data.triggered.connect(self.exportData)
        self.export_menu.addAction(self.export_data)
        # Exit QAction
        self.close_action = QtWidgets.QAction("Close project", self)
        # self.close_action.setShortcut("Ctrl+Q")
        self.close_action.triggered.connect(self.closeProject)
        self.project_menu.addSeparator()
        self.project_menu.addAction(self.close_action)

        # Time series selection, corrections...
        self.ts_menu = self.menu.addMenu("Time series")
        # self.components_menu = self.ts_menu.addMenu("Select component")
        # self.components_actions = dict()
        self.corrections_menu = self.ts_menu.addMenu("Toggle corrections")
        # for name, description in fit_data.timeseries_models_names.items():
        #     self.models_actions[name] = QtWidgets.QAction(description, self)
        #     self.models_actions[name].triggered.connect(functools.partial(self.fitModel, name))
        #     self.inversion_menu.addAction(self.models_actions[name])
        self.events_menu = self.ts_menu.addMenu("Toggle events")


        # Dataset informations, processing...
        #self.data_menu = self.menu.addMenu("Dataset")
        #self.compute = QtWidgets.QAction("Compute...", self)
        #self.data_menu.addAction(self.compute)
        #self.inversion_menu = self.data_menu.addMenu("Fit a model...")
        #self.models_actions = dict()
        #for name, description in fit_data.timeseries_models_names.items():
        #    self.models_actions[name] = QtWidgets.QAction(description, self)
        #    self.models_actions[name].triggered.connect(functools.partial(self.fitModel, name))
        #    self.inversion_menu.addAction(self.models_actions[name])
        #self.show_metadata = QtWidgets.QAction("Show metadata", self)
        #self.data_menu.addAction(self.show_metadata)

        # Features
        self.features_menu = self.menu.addMenu("Features")
        # self.plot_features_menu = QtWidgets.QMenu("Plots...")
        # self.features_menu.addMenu(self.plot_features_menu)
        self.features_plot = []
        self.plot_single = QtWidgets.QAction("Feature vs Stations")
        self.plot_single.triggered.connect(functools.partial(self.plotFeatures, False))
        self.features_menu.addAction(self.plot_single)
        # self.plot_features_menu.addAction(self.plot_single)
        # self.plot_multi = QtWidgets.QAction("Feature2 vs Feature1")
        # self.plot_multi.triggered.connect(functools.partial(self.plotFeatures, True))
        # self.plot_features_menu.addAction(self.plot_multi)

        # Category
        self.category_menu = self.menu.addMenu("Categories")
        self.manage_categories = QtWidgets.QAction("Manage categories...", self)
        self.category_menu.addAction(self.manage_categories)
        self.set_category_actions = dict()
        self.set_all_category_menu = self.category_menu.addMenu("Set *all* stations in the dataset to...")
        self.set_nonfiltered_category_menu = self.category_menu.addMenu("Set *non-filtered* stations to...")
        self.set_plotted_category_menu = self.category_menu.addMenu("Set *plotted/visible* stations to...")
        #self.set_selected_category_menu = self.category_menu.addMenu("Set *selected* stations to...")
        self.kbd_mouse_actions = dict()
        self.space_key_menu = self.category_menu.addMenu("Assign SPACE key...")
        self.left_btn_menu = self.category_menu.addMenu("Assign SHIFT + LEFT CLICK...")
        self.right_btn_menu = self.category_menu.addMenu("Assign SHIFT + RIGHT CLICK...")
        for group in cfg.CATEGORIES:
            self.addCategories(self.set_all_category_menu, group, 'all')
            self.addCategories(self.set_nonfiltered_category_menu, group, 'nonfiltered')
            self.addCategories(self.set_plotted_category_menu, group, 'plotted')
            #self.addCategories(self.set_selected_category_menu, group, 'selected')
            self.addKbdMouseCategories(self.space_key_menu, QtCore.Qt.Key_Space, group)
            self.addKbdMouseCategories(self.left_btn_menu, QtCore.Qt.MouseButton.LeftButton, group)
            self.addKbdMouseCategories(self.right_btn_menu, QtCore.Qt.MouseButton.RightButton, group)

        # Grid plot configuration
        self.grid_menu = self.menu.addMenu("Grid")
        self.set_grid_geometry = QtWidgets.QAction("Grid geometry", self)
        self.grid_geometry = grid.GridGeometryWidget()
        self.set_grid_geometry.triggered.connect(self.grid_geometry.show)
        self.grid_menu.addAction(self.set_grid_geometry)
        # self.customize_grid_theme = QtWidgets.QAction("Customize...", self)
        # self.grid_theme_menu.addAction(self.customize_grid_theme)
        self.auto_advance = QtWidgets.QAction("Auto-advance")
        self.auto_advance.setCheckable(True)
        self.auto_advance.setChecked(cfg.auto_advance)
        self.auto_advance.triggered.connect(self.setAutoAdvance)
        self.grid_menu.addAction(self.auto_advance)
        self.grid_theme_menu = self.grid_menu.addMenu("Theme...")
        self.theme_actions = dict()
        for theme in cfg.themes.iterateThemes():
            self.theme_actions[theme] = QtWidgets.QAction(theme, self)
            self.theme_actions[theme].triggered.connect(\
                                        functools.partial(\
                                            self.setTheme, main_theme_name=theme))
            self.grid_theme_menu.addAction(self.theme_actions[theme])

        # Map configuration
        self.map_menu = self.menu.addMenu("Map")
        # self.map_bg_menu = self.map_menu.addMenu("Theme")
        # self.set_default_map_bg = QtWidgets.QAction("Default", self)
        # self.map_bg_menu.addAction(self.set_default_map_bg)
        # self.set_light_map_bg = QtWidgets.QAction("Light", self)
        # self.map_bg_menu.addAction(self.set_light_map_bg)
        # self.set_dark_map_bg = QtWidgets.QAction("Dark", self)
        # self.map_bg_menu.addAction(self.set_dark_map_bg)
        # self.customize_map_bg = QtWidgets.QAction("Customize...", self)
        # self.map_bg_menu.addAction(self.customize_map_bg)
        # self.map_mk_menu = self.map_menu.addMenu("Markers")
        # self.set_default_markers_style = QtWidgets.QAction("Default", self)
        # self.map_mk_menu.addAction(self.set_default_markers_style)
        # self.customize_markers_style = QtWidgets.QAction("Customize...", self)
        # self.map_mk_menu.addAction(self.customize_markers_style)
        self.map_layers = self.map_menu.addMenu("Show layers...")
        self.show_layers = dict()
        for name, layer in cfg.map_overlays.items():
            self.show_layers[name] = QtWidgets.QAction(name, self)
            self.show_layers[name].setCheckable(True)
            self.show_layers[name].setChecked(layer['display'])
            self.show_layers[name].triggered.connect(functools.partial(self.setPlotLayer, name))
            self.map_layers.addAction(self.show_layers[name])
        self.show_legend = QtWidgets.QAction("Show legend", self)
        self.show_legend.setCheckable(True)
        self.show_legend.setChecked(False)
        self.map_menu.addAction(self.show_legend)
        self.map_theme_menu = self.map_menu.addMenu("Theme...")
        self.map_theme_actions = dict()
        for theme in cfg.themes.iterateThemes():
            self.map_theme_actions[theme] = QtWidgets.QAction(theme, self)
            self.map_theme_actions[theme].triggered.connect(\
                                            functools.partial(\
                                                self.setTheme, map_theme_name=theme))
            self.map_theme_menu.addAction(self.map_theme_actions[theme])

        # Docks
        self.dock_menu = self.menu.addMenu("Docks")

        # Create the main component: the grid
        self.ts_features_sort_widget = features_widgets.FeaturesWidget()
        self.cat_group_widget = category_widgets.CategoryGroupWidget()
        self.data_component_widget = data_widgets.DataComponentWidget()
        #TODO: for now, only get the min and max date of the *loaded* time series
        t0, t1 = np.inf, -np.inf
        for sta in cfg.stalist_all:
            if not cfg.dataset.hasData(sta):
                continue
            if cfg.dataset.getData(sta).t[0] < t0:
                t0 = cfg.dataset.getData(sta).t[0]
            if cfg.dataset.getData(sta).t[-1] > t1:
                t1 = cfg.dataset.getData(sta).t[-1]
        timespan = [t0, t1]
        grid_controls = {'page_control': grid_widgets.GridControlWidget(),
                         'yrange': grid_widgets.GridYRangeWidget(),
                         'timerange': grid_widgets.GridTimeRangeWidget(timespan=timespan)}
        highlevel_controls = {'category_group': self.cat_group_widget,
                              'data_component': self.data_component_widget,
                              'features_sort': self.ts_features_sort_widget}
        self.grid = grid.GridPanel(grid_widgets=grid_controls,
                                   highlevel_widgets=highlevel_controls,
                                   parent=self)
        self.setCentralWidget(self.grid)
        # Note that we connect the grid itself with the other components, not the grid_panel
        self.data_grid = self.grid.getGrid()
        self.grid_geometry.connectToGrid(self.data_grid)

        # Docks: large plot and map
        self.docks = dict()
        self.large_plot = largeplot.LargePlot()
        self.docks['plot'] = self.createDockWindow(self.large_plot, "Zoom plot")
        self.sta_map = mapcartopy.MapPanel()
        self.sta_map.setMinimumWidth(100)
        self.sta_map.setMinimumHeight(100)
        self.docks['map'] = self.createDockWindow(self.sta_map, "Map")
        self.leaflet_map = mapleaflet.LeafletMapPanel()
        self.docks['leaflet_map'] = self.createDockWindow(self.leaflet_map, "Leaflet Map")
        self.sta_filter = filter_widgets.FilterWidget()
        self.docks['filter'] = self.createDockWindow(self.sta_filter, "Filter", visible=False)
        for dock in self.docks:
            self.docks[dock].setObjectName(dock)

        # self.features_plot = ts_features.FeaturesPlotPanel()
        # self.docks['feat_plot'] = self.createDockWindow(self.features_plot, "Features plot", visible=False)

        # self.sta_map.setMinimumWidth(50)
        # self.sta_map.setMinimumHeight(200)
        # self.resizeDocks([self.docks['map']], [800], QtCore.Qt.Vertical)
        # self.resizeDocks(list(self.docks.values()), [400, 400], QtCore.Qt.Horizontal)
        # self.resizeDocks(list(self.docks.values()), [200, 600], QtCore.Qt.Vertical)
        # self.saveState()

        # Create the controller for signals management (Controller in MVC pattern)
        self.controller = ctl.SignalDispatcher()

        # View -> Controller for any interaction
        # Note: the object triggering the signal sometimes update itself first
        # Connect the grid subplots, map and filter (senders) to the controller
        self.gui_to_ctrl.connect(self.controller.receiveSignal)
        self.cat_group_widget.gui_to_ctrl.connect(self.controller.receiveSignal)
        self.data_component_widget.gui_to_ctrl.connect(self.controller.receiveSignal)
        self.ts_features_sort_widget.gui_to_ctrl.connect(self.controller.receiveSignal)
        self.data_grid.gui_to_ctrl.connect(self.controller.receiveSignal)
        self.sta_map.gui_to_ctrl.connect(self.controller.receiveSignal)
        self.leaflet_map.gui_to_ctrl.connect(self.controller.receiveSignal)
        self.sta_filter.controllerConnect(self.controller.receiveSignal)
        # self.features_plot.gui_to_ctrl.connect(self.controller.receiveSignal)

        # Controller -> View for quick signal broadcasting (short-term GUI updates)
        # Note: the object triggering the signal may be already updated.
        # If it is the case, it receives the broadcast anyway but ignores it.
        # Connect the controller to the grid, large plot and map (receivers)
        self.controller.ctrl_to_gui.connect(self.data_grid.updatePlots)
        self.controller.ctrl_to_gui.connect(self.sta_map.updateMap)
        self.controller.ctrl_to_gui.connect(self.leaflet_map.updateMap)
        self.controller.ctrl_to_gui.connect(self.large_plot.updatePlot)

        # Controller -> Model for dataset update
        # Connect the controller to the dataset
        self.controller.ctrl_to_dataset.connect(cfg.dataset.updateDataset)

        # Model -> View for long-lasting GUI updates
        # Connect the dataset to the grid and map
        cfg.dataset.data_to_gui.connect(self.data_grid.updatePlots)
        cfg.dataset.data_to_gui.connect(self.sta_map.updateMap)
        cfg.dataset.data_to_gui.connect(self.leaflet_map.updateMap)

        # Status bar
        self.status = self.statusBar()
        self.general_info = QtWidgets.QLabel("Pygoda - beta version")
        self.mode_info = QtWidgets.QLabel(cst.MODES_NAME[cfg.mode])
        self.grid_info = QtWidgets.QLabel("{:d}/{:d} stations".format(cfg.nplots, cfg.nsta))
        self.status.addPermanentWidget(self.general_info)
        self.status.addPermanentWidget(self.mode_info)
        self.status.addPermanentWidget(self.grid_info)
        self.status.showMessage("Loading...", 2000)
        self.controller.ctrl_to_status.connect(self.updateStatus)

        # Restore docks position and geometry
        self.readSettings()

        # Let's go!
        self.data_grid.setup()

    def createDockWindow(self, new_dock, dock_name, visible=True):
        dock = QtWidgets.QDockWidget(dock_name, self)
        dock.setWidget(new_dock)
        self.dock_menu.addAction(dock.toggleViewAction())
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        if not visible:
            dock.hide()

        return dock

    # def eventFilter(self, obj, event):
    #     result = False
    #     if event.type() == QtCore.QEvent.KeyPress:
    #         print('key press!')
    #         self.keyPressEvent(event)
    #         result = True
    #     elif event.type() == QtCore.QEvent.KeyRelease:
    #         print('key release!')
    #         self.keyReleaseEvent(event)
    #         result = True
    #     else:
    #         result = obj.eventFilter(self, event)
    #     return result

    @QtCore.Slot()
    def updateStatus(self, message_dict):
        if 'main_status' in message_dict:
            self.status.showMessage(message_dict['main_status'])
        if 'mode_status' in message_dict:
            self.mode_info.setText(message_dict['mode_status'])
        if 'grid_status' in message_dict:
            self.grid_info.setText(message_dict['grid_status'])

    def setBtnKey(self, btn, group, new_category):
        print('Select category', new_category, 'in', group)
        for category in self.kbd_mouse_actions[btn][group]:
            if category != new_category:
                self.kbd_mouse_actions[btn][group][category].setChecked(False)

        if btn == QtCore.Qt.MouseButton.LeftButton:
            cfg.cat_shift_left[group] = new_category
        elif btn == QtCore.Qt.MouseButton.RightButton:
            cfg.cat_shift_right[group] = new_category
        elif btn == QtCore.Qt.Key_Space:
            cfg.cat_switch[group] = new_category

    def addKbdMouseCategories(self, menu, btn, group):
        if btn not in self.kbd_mouse_actions:
            self.kbd_mouse_actions[btn] = dict()
        self.kbd_mouse_actions[btn][group] = dict()

        if btn == QtCore.Qt.Key_Space:
            categories = cfg.cat_names[group].copy()
            if cfg.CAT_DEFAULT in categories:
                del categories[cfg.CAT_DEFAULT]
        else:
            categories = {'+': 'Next category', '-': 'Previous category'}
            categories.update(cfg.cat_names[group])

        group_menu = menu.addMenu('for ' + cfg.grp_names[group] + ' to...')
        for category, name in categories.items():
            set_button = QtWidgets.QAction(name, self)
            set_button.setCheckable(True)
            # Doesn't work, category passed by referenced
            # space_key_lambda = lambda: self.setSpaceKey(category)
            button_lambda = functools.partial(self.setBtnKey, btn, group, category)
            set_button.triggered.connect(button_lambda)
            group_menu.addAction(set_button)
            self.kbd_mouse_actions[btn][group][category] = set_button
            if btn == QtCore.Qt.MouseButton.LeftButton and \
               category == cfg.cat_shift_left[group]:
                set_button.setChecked(True)
            elif btn == QtCore.Qt.MouseButton.RightButton and \
                 category == cfg.cat_shift_right[group]:
                set_button.setChecked(True)
            elif btn == QtCore.Qt.Key_Space and \
                 category == cfg.cat_switch[group]:
                set_button.setChecked(True)
            if category == '-':
                group_menu.addSeparator()

    def addCategories(self, menu, group, subset):
        self.set_category_actions[group] = dict()
        group_menu = menu.addMenu(cfg.grp_names[group])
        for category, cat_name in cfg.cat_names[group].items():
            set_category = QtWidgets.QAction(cat_name, self)
            set_category.triggered.connect(functools.partial(self.setCategory, group, category, subset))
            group_menu.addAction(set_category)
            self.set_category_actions[group][category] = set_category

    def setCategory(self, group, category, subset):
        if subset == 'all':
            sta_cat_list = [(sta, group, category) for sta in cfg.stalist_all]
        elif subset == 'nonfiltered':
            sta_cat_list = [(sta, group, category) for sta in cfg.stalist]
        elif subset == 'plotted':
            sta_cat_list = []
            for sta, plotted in cfg.plotted_sta.items():
                if plotted:
                    sta_cat_list.append((sta, group, category))
        #TODO: not possible yet, selected stations are not known globally
        #elif subset == 'selected':
        #    sta_cat_list = [(sta, group, category) for sta in cfg.selected_sta]

        self.send({'CATEGORY_CHANGED': sta_cat_list})

    def setPlotLayer(self, layer_name):
        cfg.map_layers[layer_name]['display'] = not cfg.map_layers[layer_name]['display']
        self.sta_map.map_.updateOverlays(names=layer_name)

    def setAutoAdvance(self):
        cfg.auto_advance = not cfg.auto_advance

    def setTheme(self, main_theme_name=None, map_theme_name=None):
        cfg.themes.applyThemes(main_theme_name, map_theme_name)
        if main_theme_name:
            self.data_grid.setup()
        elif map_theme_name:
            self.sta_map.createMap()

    def fitModel(self, name):
        # Fit the selected model
        cfg.models[name].fitModel()

        #TODO: Update a menu to display the fitted model

    def plotFeatures(self, multi=False):
        self.features_plot.append(features.FeaturesPlotPanel(feat_id1=cfg.sort_by, multi=multi))
        self.features_plot[-1].gui_to_ctrl.connect(self.controller.receiveSignal)
        self.features_plot[-1].show()

    def exportList(self):
        suggested_output = os.path.join(cfg.basedir, str(cfg.nsta) + 'stations_' + cfg.project_name + '.txt')
        types_list = "ASCII/Text file (*.txt);; CSV file (*.csv);; All files (*)"
        filepath, ftype = QtWidgets.QFileDialog.getSaveFileName(self, "Export stations list",
                                                                suggested_output,
                                                                types_list)
        if '.csv' in ftype:
            sep = ','
        else:
            sep = ' '
        export_data.exportAttributes(filepath, cfg.stalist, attrs=['lon', 'lat'], sep=sep)

    def exportData(self):
        pass

    def readSettings(self):
        settings = QtCore.QSettings("GlobalMass", "Pygoda")
        try:
            print('Restore window state')
            # self.restoreGeometry(settings.value(cfg.project_name + "/ProjectWindow/geometry"))
            self.setGeometry(settings.value(cfg.project_name + "/ProjectWindow/geometry"))
            self.restoreState(settings.value(cfg.project_name + "/ProjectWindow/windowState"))
        except:
            print('Warning: could not reload window state')

        # 2022-09-30: storing and restoring docks state is not needed anymore
        # for dock in self.docks:
        #     try:
        #         print('Restore %s state' % dock)
        #         dock_name = cfg.project_name + '/' + dock + "Dock/"
        #         value_name = dock_name + "isFloating"
        #         self.docks[dock].setFloating(settings.value(value_name) == 'true')
        #         # Not needed in theory
        #         value_name = dock_name + "geometry"
        #         print(dock_name, settings.value(value_name))
        #         self.docks[dock].setGeometry(settings.value(value_name))
        #         # value_name = cfg.project_name + '/' + dock + "Dock/geometry"
        #         # self.docks[dock].restoreGeometry(QtCore.QByteArray.fromBase64(settings.value(value_name)))
        #     except:
        #         print('Warning: could not reload %s dock state' % dock)

        # for name, dock in self.docks.items():
        #     dock.restoreGeometry(settings.value(dock + "/geometry".toByteArray()))
        #     dock.restoreState(settings.value(dock + "/windowState".toByteArray(), version=cfg.project_id))

    def closeEvent(self, event):
        settings = QtCore.QSettings("GlobalMass", "Pygoda")
        print('Store state')

        # 2022-09-30: storing and restoring docks state is not needed anymore
        # Qt bugs, see:
        # https://stackoverflow.com/questions/34732872/qt-pyside-savegeometry-savestate
        # https://stackoverflow.com/questions/44005852/qdockwidgetrestoregeometry-not-working-correctly-when-qmainwindow-is-maximized
        for dock in self.docks:
            dock_name = cfg.project_name + '/' + dock + "Dock/"
            is_floating = self.docks[dock].isFloating()
            value_name = dock_name + "isFloating"
            settings.setValue(value_name, is_floating)
            #self.docks[dock].setFloating(True) # needed for some reason
            # Not needed in theory
            dock_geometry = self.docks[dock].geometry()
            value_name = dock_name + "geometry"
            settings.setValue(value_name, dock_geometry)
            # value_name = cfg.project_name + '/' + dock + "Dock/geometry"
            # print(self.docks[dock].saveGeometry().toBase64())
            # print(type(self.docks[dock].saveGeometry()))
            # print(settings.value(value_name) == self.docks[dock].saveGeometry().toBase64())
            # settings.setValue(value_name, self.docks[dock].saveGeometry().toBase64())

        # settings.setValue(cfg.project_name + "/ProjectWindow/geometry", self.saveGeometry())
        settings.setValue(cfg.project_name + "/ProjectWindow/geometry", self.geometry())
        settings.setValue(cfg.project_name + "/ProjectWindow/windowState", self.saveState())
        # for dock in self.docks.values():
        #     settings.setValue("geometry", dock.saveGeometry())
        #     settings.setValue("windowState", dock.saveState(version=cfg.project_id))

        for dock in self.docks.values():
            dock.close()
        for feature_plot in self.features_plot:
            feature_plot.close()
        super().closeEvent(event)

    @QtCore.Slot()
    def closeProject(self):
        self.close()

    def send(self, message):
        message['FROM'] = self.id
        self.gui_to_ctrl.emit(message)
