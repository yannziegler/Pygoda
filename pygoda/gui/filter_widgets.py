# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import copy
import time
import strictyaml as yaml

import geopandas as gpd
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely import wkt

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature

import matplotlib.pyplot as plt

from . import trees
import config as cfg
from controller import filters

class FilterWidget(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self, controller_slot=None):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals

        self.layout = QtWidgets.QVBoxLayout()
        self.filters_layout = QtWidgets.QHBoxLayout()

        # Category filter
        self.category_filter_widget = CategoryFilterWidget(controller_slot)
        self.filters_layout.addWidget(self.category_filter_widget)

        # Geographical filter
        self.geo_filter_widget = GeoFilterWidget(controller_slot)
        self.filters_layout.addWidget(self.geo_filter_widget)

        self.layout.addLayout(self.filters_layout)

        self.apply_filter = QtWidgets.QPushButton("Apply all filters")
        self.apply_filter.clicked.connect(self.applyAllFilter)
        self.layout.addWidget(self.apply_filter)

        self.setLayout(self.layout)

        if controller_slot:
            self.gui_to_ctrl.connect(controller_slot)

    def controllerConnect(self, controller_slot):

        self.category_filter_widget.controllerConnect(controller_slot)
        self.geo_filter_widget.controllerConnect(controller_slot)
        self.gui_to_ctrl.connect(controller_slot)

    def applyAllFilter(self):

        stalist_cat = self.category_filter_widget.updateFilter(no_signal=True)
        stalist_geo = self.geo_filter_widget.updateFilter(no_signal=True)

        stalist = [sta for sta in stalist_cat if sta in stalist_geo]

        if not stalist:
            no_station = QtWidgets.QMessageBox(self)
            no_station.setWindowTitle("Filters")
            no_station.setText("The filters exclude all the stations!")
            button = no_station.exec_()
        else:
            self.send({'FILTER': stalist})

        return stalist

    def send(self, message):
        message['FROM'] = self.id
        self.gui_to_ctrl.emit(message)


class GeoFilterWidget(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self, controller_slot=None):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals

        self.filter = filters.GeoFilter()
        self.stalist = cfg.stalist_all.copy()

        self.layout = QtWidgets.QVBoxLayout()

        self.all_none_layout = QtWidgets.QHBoxLayout()
        self.select_all = QtWidgets.QPushButton("All")
        self.select_all.setToolTip("Check all")
        self.select_all.clicked.connect(self.checkAll)
        self.select_none = QtWidgets.QPushButton("None")
        self.select_none.setToolTip("Uncheck all")
        self.select_none.clicked.connect(self.uncheckAll)
        #self.select_reverse = QtWidgets.QPushButton("Reverse")
        #self.select_reverse.setToolTip("Toggle selection")
        #self.select_reverse.clicked.connect(self.toggleAll)
        self.all_none_layout.addWidget(self.select_all)
        self.all_none_layout.addWidget(self.select_none)
        #self.all_none_layout.addWidget(self.select_reverse)
        self.layout.addLayout(self.all_none_layout)

        self.geography_search = QtWidgets.QLineEdit()
        self.geography_search.setClearButtonEnabled(True)
        self.geography_search.setPlaceholderText("Look for a place...")
        self.layout.addWidget(self.geography_search)

        self.geography_tree = QtWidgets.QTreeView()
        # self.admin_levels = self.loadAdministrativeLevels()
        self.countries_tree = self.loadCountries()
        self.display_mode = 'geographic' # 'admin'
        self.geography_tree_model = trees.GeographyTreeModel(self.countries_tree,
                                                             display_mode=self.display_mode,
                                                             dependencies_key='dependencies',
                                                             geounits_key='geounits',
                                                             subdivisions_key='subdivisions')
        self.tree_proxy = trees.TreeProxyModel()
        self.tree_proxy.setSourceModel(self.geography_tree_model)
        self.geography_tree.setModel(self.tree_proxy)
        self.layout.addWidget(self.geography_tree)

        self.apply_filter = QtWidgets.QPushButton("Apply filter")
        self.apply_filter.clicked.connect(self.updateFilter)
        self.layout.addWidget(self.apply_filter)

        self.geography_search.textChanged.connect(self.geographyTreeSearch)

        self.setLayout(self.layout)

        if controller_slot:
            self.gui_to_ctrl.connect(controller_slot)

    def checkAll(self):
        self.geography_tree_model.checkAll()

    def uncheckAll(self):
        self.geography_tree_model.uncheckAll()

    def toggleAll(self):
        self.geography_tree_model.toggleAll()

    def controllerConnect(self, controller_slot):
        self.gui_to_ctrl.connect(controller_slot)

    def geographyTreeSearch(self):
        # self.geography_tree.expandAll()
        self.geography_tree_proxy.\
            setFilterRegExp(QtCore.QRegExp(self.geography_search.text(),
                                           QtCore.Qt.CaseInsensitive,
                                           QtCore.QRegExp.FixedString))
        if not self.geography_search.text():
            return
        self.geography_tree.expandAll()
        # self.geography_tree.collapseAll();
        # accepted_indices = self.geography_tree_proxy.getAcceptedIndices();
        # print('Indices', accepted_indices, flush=True)
        # for index in accepted_indices:
        #     index = self.geography_tree_proxy.mapFromSource(index)
        #     parent_index = index.parent()
        #     while parent_index.isValid():
        #         print('Expanding', self.geography_tree.model().sourceModel().data(parent_index, QtCore.Qt.DisplayRole))
        #         self.geography_tree.expand(parent_index)
        #         parent_index = parent_index.parent()

    # def loadAdministrativeLevels(self):
    #     # Fake for testing
    #     return {'North America':
    #             {'United States':
    #              ['California', 'Texas', 'Florida'],
    #              'Canada':
    #              ['Quebec', 'Nunavit']},
    #             'Europe':
    #             ['United Kingdom', 'France', 'Portugal', 'Macedonia']}

    def loadCountries(self, max_level=20):
        print("Loading countries lists...", end="")

        with open('data/countries.yaml', mode='r', encoding='utf8') as f:
            countries_tree = yaml.load(f.read()).data

        with open('data/countries_geounits.yaml', mode='r', encoding='utf8') as f:
            geounits_tree = yaml.load(f.read()).data

        with open('data/countries_subdivisions.yaml', mode='r', encoding='utf8') as f:
            subdivs_tree = yaml.load(f.read()).data

        self.countries = dict()

        # Add countries and their dependencies,
        # along with geounits and subdivisions
        for country_code, fields in countries_tree.items():
            country = copy.deepcopy(fields)
            # country_name = country['fullname']
            # country_wikidata = country['wikidata']
            # country_dep = country['dependencies']
            # country_sub = country['subdivisions']
            # world_region_name = country['world_region']
            # world_region_m49 = country['unsd_m49']

            if 'parent' in fields:
                # Dependency handled by its parent (MUST be after it)
                # We only add geounits here
                #parent_country_code = fields['parent']
                #parent_country = self.countries[parent_country_code]
                #self.addGeounits(parent_country['dependencies'][country_code], geounits_tree)
                continue

            # Replace dependencies list by actual dependencies
            country['dependencies'] = dict()
            for dep in fields.get('dependencies', []):
                # name = countries_tree[dep]['fullname']
                country['dependencies'][dep] = countries_tree[dep]

            # Replace geounits and subdivisions lists by actual entries (recursive)
            self.addSubTerritories(country, geounits_tree, subdivs_tree)

            self.countries[country_code] = country

        print("done")

        # self.countries = dict(sorted(self.countries.items()))
        # self.countries = {k: self.countries[k] for k in sorted(self.countries.items(), lambda x: x['fullname'])}
        return self.countries

    def addSubTerritories(self, country, geounits_tree, subdivs_tree):
        geounits_list = list(country.get('geounits', '')).copy()
        subdivs_list = list(country.get('subdivisions', '')).copy()

        if geounits_list:
            country['geounits'] = dict()
        if subdivs_list:
            country['subdivisions'] = dict()

        for geo in geounits_list:
            country['geounits'][geo] = geounits_tree[geo]
            self.addSubTerritories(country['geounits'][geo],
                                   geounits_tree, subdivs_tree)

        for geo in subdivs_list:
            country['subdivisions'][geo] = subdivs_tree[geo]
            self.addSubTerritories(country['subdivisions'][geo],
                                   geounits_tree, subdivs_tree)

    def recursiveShapefileLoad(self, country_tree, target_rank, shp_dataframe):
        selected_units = shp_dataframe['scalerank'] == target_rank
        shp_df = shp_dataframe[selected_units]

        if not shp_df.shape[0]:
            return

        # print('Rank:', target_rank, flush=True)
        # for sov, adm0, gu, su, subu, brk, br in zip(shp_df['sr_sov_a3'],
        #                                       shp_df['sr_adm0_a3'],
        #                                       shp_df['sr_gu_a3'],
        #                                       shp_df['sr_su_a3'],
        #                                       shp_df['sr_subunit'],
        #                                       shp_df['sr_brk_a3'],
        #                                       shp_df['sr_br_name']):
        #     print('Units:', sov, adm0, gu, su, subu, brk, br, flush=True)
        # # print('Shape:', shp_df.shape, '\n', flush=True)
        # print('')
        # time.sleep(1)
        for unit, parent, geometry in zip(shp_df['sr_subunit'], shp_df['sr_sov_a3'], shp_df['featurecla']):
            if not unit:
                continue
            if unit not in country_tree.keys():
                country_tree[unit] = dict()
            selected_units = shp_dataframe['sr_sov_a3'] == parent
            current_df = shp_dataframe[selected_units]
            selected_units = current_df['scalerank'] > target_rank
            shp_df = current_df[selected_units]
            # print('Recursive call for', unit, 'with rank', target_rank, flush=True)
            # self.recursiveShapefileLoad(country_tree[unit], target_rank+1, shp_df)

    def updateFilter(self, no_signal=False):

        #tree_data = self.geography_tree_model.getTreeData()

        # Use either checked or unchecked territories to minimise computation
        keys = ('geounits', 'subdivisions', 'dependencies') # remove from data field
        tree_data_checked = self.geography_tree_model.getCheckedData(remove_keys=keys)
        tree_data_unchecked = self.geography_tree_model.getUncheckedData(remove_keys=keys)
        if len(tree_data_checked['Planet Earth']['children']) <= \
           len(tree_data_unchecked['Planet Earth']['children']):
            state = QtCore.Qt.Checked
            tree_data = tree_data_checked
        else:
            state = QtCore.Qt.Unchecked
            tree_data = tree_data_unchecked

        self.stalist = self.filter.applyFilter(tree_data, state)

        if not no_signal:
            if not self.stalist:
                no_station = QtWidgets.QMessageBox(self)
                no_station.setWindowTitle("Geographic filter")
                no_station.setText("The filter excludes all the stations!")
                button = no_station.exec_()
            else:
                self.send({'FILTER': self.stalist})

        return self.stalist

    def send(self, message):
        message['FROM'] = self.id
        self.gui_to_ctrl.emit(message)


class CategoryFilterWidget(QtWidgets.QWidget):

    gui_to_ctrl = QtCore.Signal(dict)

    def __init__(self, controller_slot=None):
        QtWidgets.QWidget.__init__(self)

        self.id = id(self) # used to 'sign' signals

        self.filter = filters.CategoryFilter()
        self.stalist = cfg.stalist_all.copy()

        self.layout = QtWidgets.QVBoxLayout()
        self.visible_categories = cfg.CATEGORIES.copy() # default: show everything

        self.and_or_layout = QtWidgets.QHBoxLayout()
        self.and_or_layout.addWidget(QtWidgets.QLabel("Group combination: "))
        self.radio_and = QtWidgets.QRadioButton('AND')
        self.radio_and.setChecked(True)
        self.radio_and.setToolTip("For *each* group, the station must belong to one of the selected categories.\n" \
                                  "If no category are selected in a group, this group is ignored.")
        self.radio_or = QtWidgets.QRadioButton('OR')
        self.radio_or.setToolTip("For *at least one* group, the station must belong to one of the selected categories.\n" \
                                 "If no category are selected in a group, this group is ignored.")
        self.and_or_layout.addWidget(self.radio_and)
        self.and_or_layout.addWidget(self.radio_or)
        # self.radio_and.toggled.connect(self.toggleAndOr)
        # self.radio_or.toggled.connect(self.toggleAndOr)
        self.layout.addLayout(self.and_or_layout)

        #self.all_none_layout = QtWidgets.QHBoxLayout()
        self.all_none_layout = QtWidgets.QGridLayout()
        self.category_all = QtWidgets.QPushButton("All")
        self.category_all.setToolTip("Set the best initial state for filtering-by-removing\n(check all categories).")
        self.category_all.clicked.connect(self.checkAll)
        self.category_none = QtWidgets.QPushButton("None")
        self.category_none.setToolTip("Set the best initial state for filtering-by-adding\n(uncheck all categories).")
        self.category_none.clicked.connect(self.uncheckAll)
        self.category_reverse = QtWidgets.QPushButton("Reverse")
        self.category_reverse.setToolTip("Toggle selection")
        self.category_reverse.clicked.connect(self.toggleAll)
        self.category_undef = QtWidgets.QPushButton("undef.")
        self.category_undef.setToolTip("Toggle selection for default/undefined")
        self.category_undef.clicked.connect(self.toggleUndef)
        self.all_none_layout.addWidget(self.category_all, 0, 0)
        self.all_none_layout.addWidget(self.category_none, 0, 1)
        self.all_none_layout.addWidget(self.category_reverse, 1, 0)
        self.all_none_layout.addWidget(self.category_undef, 1, 1)
        self.layout.addLayout(self.all_none_layout)

        self.category_list = QtWidgets.QListWidget()
        # self.all_filter = QtWidgets.QAction("ALL", self)
        # self.all_filter.setCheckable(True)
        # self.all_filter.triggered.connect(lambda: self.setCategoryFilter(cfg.CATEGORIES))
        # self.filter_menu.addAction(self.all_filter)
        # self.none_filter = QtWidgets.QAction("NONE", self)
        # self.none_filter.setCheckable(True)
        # self.none_filter.triggered.connect(lambda: self.setCategoryFilter([]))
        # self.filter_menu.addAction(self.none_filter)
        # self.filter_menu.addSeparator()
        for group, categories in cfg.CATEGORIES.items():
            group_title = QtWidgets.QListWidgetItem('[{:s}]'.format(cfg.grp_names[group]))
            # group_title.setFont(QtGui.QFont('Verdana', bold=True))
            group_title.setData(QtCore.Qt.UserRole, group)
            # group_title.setCheckable(False)
            self.category_list.addItem(group_title)
            if group != cfg.GRP_QUALITY:
                category_filter = QtWidgets.QListWidgetItem('undefined', self.category_list)
                category_filter.setData(QtCore.Qt.UserRole, (group, None))
                category_filter.setCheckState(QtCore.Qt.Checked)
            for category in categories:
                category_name = cfg.cat_names[group][category]
                category_filter = QtWidgets.QListWidgetItem(category_name, self.category_list)
                category_filter.setData(QtCore.Qt.UserRole, (group, category))
                category_filter.setCheckState(QtCore.Qt.Checked)
                # category_filter.triggered.connect(lambda: self.setCategoryFilter(category))
                # self.category_filter.addItem(category_filter)
        # self.filter_bt = QtWidgets.QPushButton("Filter...")
        # self.filter_bt.setMenu(self.filter_menu)
        self.layout.addWidget(self.category_list)

        self.apply_filter = QtWidgets.QPushButton("Apply filter")
        self.apply_filter.clicked.connect(self.updateFilter)
        self.layout.addWidget(self.apply_filter)

        self.setLayout(self.layout)

        if controller_slot:
            self.gui_to_ctrl.connect(controller_slot)

    def controllerConnect(self, controller_slot):
        self.gui_to_ctrl.connect(controller_slot)

    # def toggleAndOr(self):
    #     pass

    def checkAll(self):
        for i in range(self.category_list.count()):
            cat = self.category_list.item(i)
            if isinstance(cat.data(QtCore.Qt.UserRole), tuple):
                # It's a category, not a group of categories
                cat.setCheckState(QtCore.Qt.Checked)

    def uncheckAll(self):
        for i in range(self.category_list.count()):
            cat = self.category_list.item(i)
            grp_cat = cat.data(QtCore.Qt.UserRole)
            if isinstance(grp_cat, tuple):
                # It's a category, not a group of categories
                cat.setCheckState(QtCore.Qt.Unchecked)
                #if self.radio_or.isChecked() and not grp_cat[1]:
                #    cat.setCheckState(QtCore.Qt.Checked)

    def toggleAll(self):
        for i in range(self.category_list.count()):
            cat = self.category_list.item(i)
            if isinstance(cat.data(QtCore.Qt.UserRole), tuple):
                # It's a category, not a group of categories
                state = QtCore.Qt.Unchecked if cat.checkState() else QtCore.Qt.Checked
                cat.setCheckState(state)

    def toggleUndef(self):
        for i in range(self.category_list.count()):
            cat = self.category_list.item(i)
            grp_cat = cat.data(QtCore.Qt.UserRole)
            if isinstance(grp_cat, tuple) and not grp_cat[1]:
                # It's a generic default or 'undefined' category
                state = QtCore.Qt.Unchecked if cat.checkState() else QtCore.Qt.Checked
                cat.setCheckState(state)

    def updateFilter(self, no_signal=False):
        # Category selection
        ncat = self.category_list.count()
        checked_categories = copy.deepcopy(cfg.CATEGORIES)
        for i in range(ncat):
            cat_item = self.category_list.item(i)
            grp_cat = cat_item.data(QtCore.Qt.UserRole)
            if isinstance(grp_cat, tuple):
                grp, cat = grp_cat
                if cat is None and cat_item.checkState():
                    checked_categories[grp].append(None)
                elif not cat_item.checkState() and cat is not None:
                    icat = checked_categories[grp].index(cat)
                    del checked_categories[grp][icat]

        operator = 'AND' if self.radio_and.isChecked() else 'OR'

        # self.progress_bar = ProgressBarWidget(self)

        self.stalist = self.filter.applyFilter(checked_categories, operator)

        if not no_signal:
            if not self.stalist:
                no_station = QtWidgets.QMessageBox(self)
                no_station.setWindowTitle("Category filter")
                no_station.setText("The filter excludes all the stations!")
                button = no_station.exec_()
            else:
                self.send({'FILTER': self.stalist})

        return self.stalist

    def send(self, message):
        message['FROM'] = self.id
        self.gui_to_ctrl.emit(message)


class ProgressBarWidget(QtWidgets.QWidget):

    progress_to_filter = QtCore.Signal()

    def __init__(self, filter_widget=None):
        QtWidgets.QWidget.__init__(self)

        self.overrideWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle('Filtering the stations...')

        # Setup the layout and its components
        self.layout = QtWidgets.QVBoxLayout()

        self.progress = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progress)

        self.bottom_layout = QtWidgets.QHBoxLayout()

        self.info = QtWidgets.QLabel("Filtering infos...")
        self.bottom_layout.addWidget(self.info)

        self.cancel = QtWidgets.QPushButton("Cancel")
        self.cancel.clicked.connect(self.cancelFilter)
        self.bottom_layout.addWidget(self.cancel)

        self.layout.addLayout(self.bottom_layout)
        self.setLayout(self.layout)

        if filter:
            self.connectToGrid(filter)

    def connectToGrid(self, filter_widget):
        self.filter_widget = filter_widget
        self.progress_to_filter.connect(self.filter_widget.cancel)

    def cancelFilter(self):
        self.progress_to_filter.emit()
        self.close()
