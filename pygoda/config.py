# coding: utf-8

import copy
import os
import sys

import cartopy.crs as ccrs
import strictyaml as yaml

import constants as cst
from geo import geotools
from tools import yaml2bool


class ProjectConfiguration():

    def __init__(self, config_filepaths):

        self.config_filepaths = config_filepaths

        # Flag for first configuration
        self.startup = True

        # Hard-coded fallback values

        # Grid
        self.nrows, self.ncols = 6, 4 # geometry of the grid
        self.auto_adjust_geometry = False # fill the view when nsta < nplots
        self.auto_advance = False # move to next station after selecting a category
        self.auto_switch_page = True # update the grid automatically when clicking on the map

        # Subplots
        self.subplot_type = 'scatter' # only option is 'scatter' for now

        # Large/Big plot (I may use 'big' in the code because it's shorter)
        self.largeplot_type = 'scatter' # only option is 'scatter' for now

        # Map
        self.proj = ''
        self.map_resolution = ''
        self.proj_options = dict()
        self.map_extent = None

        self.map_overlays = dict()

        # Performances
        self.load_nsta = -1 # load this number of stations at startup (-1 == all)
        self.load_first_page = True # always load all the data for the first grid page
        self.load_on_the_fly = False # load the data only when needed
        #self.max_in_memory = -1 # keep no more than this number of stations in memory (-1 == no limit)
        self.downsampling_rate = 1 # no downsampling by default
        self.downsampling_threshold = 1000 # no subsampling if there are less than n data
        self.downsampling_method = 'naive' # only option is 'naive' for now
        self.best_quality_on_hover = True # remove downsampling when hovering/selecting
        self.keep_best_quality = True # make previous option persistent
        self.largeplot_update_threshold = 10000 # don't auto update big plot if len(data) > threshold

        # Anything related to the categories
        self.CATEGORIES = dict()
        self.GRP_VAR = dict() # map between group IDs and Python/yaml variables names
        self.GRP_ID = dict() # map between Python/yaml variables names and group IDs
        self.CAT_VAR = dict() # map between category IDs and Python/yaml variables names
        self.CAT_ID = dict() # map between Python/yaml variables names and category IDs
        self.ALL_CAT_ID = dict()
        self.ALL_CAT_VAR = dict()
        self.N_GRP_CAT = 0
        self.N_CAT = 0
        # Some default ID
        self.GRP_QUALITY = None
        self.GRP_GENERIC = None
        self.CAT_DEFAULT = 0
        self.CAT_BAD = -1
        self.CAT_NEUTRAL = 0
        self.CAT_GOOD = 1
        # For display in GUI
        self.grp_names = dict()
        self.cat_names = dict()
        # Keyboard-related
        self.grp_keys = dict()
        self.cat_keys = dict()
        self.cat_switch = dict()
        self.cat_shift_left = dict()
        self.cat_shift_right = dict()
        self.cat_reset = dict()

    def loadConfig(self, set_globals=True):

        for config_file in self.config_filepaths:
            self._updateConfig(config_file)

        self.nplots = self.nrows * self.ncols # 9 * 15 = 135 ; 135 * 29 = 4000
        if self.load_on_the_fly and \
           self.load_first_page and \
           self.load_nsta < self.nplots:
            self.load_nsta = self.nplots

        # Create Cartopy map projections
        PROJ_FUNC = {'lcc': ccrs.LambertConformal, # Lambert Conformal Conic
                    'eqc': ccrs.EquidistantConic} # Equidistant Conic
        for proj, f in PROJ_FUNC.items():
            if self.proj == proj:
                geotools.PROJ2CARTOPY[proj] = f(**self.proj_options)
            else:
                geotools.PROJ2CARTOPY[proj] = f() # default options

        # Keys assignement for category switching
        for grp_id, cat in self.cat_switch.items():
            if not cat:
                # Take the first category
                cat = list(self.CAT_VAR[grp_id].values())[0]
            # Replace Python/yaml variables names by category IDs
            self.cat_switch[grp_id] = self.CAT_ID[grp_id][cat]
        for grp_id, cat in self.cat_reset.items():
            if cat:
                # Replace Python/yaml variables names by category IDs
                self.cat_reset[grp_id] = self.CAT_ID[grp_id][cat]

        # Remove the default categories which were missing in the last config
        # for cat in cst.DEFAULT_self.CATEGORIES:
        #     if cat not in last_categories:
        #         cat_id = self.CAT_ID[cat]
        #         del self.CATEGORIES[self.CATEGORIES.index(cat_id)]
        #         del self.CAT_VAR[cat_id]
        #         del self.CAT_ID[cat]
        #         del self.cat_names[cat_id]
        #         del self.cat_keys[list(self.cat_keys.keys())[list(self.cat_keys.values()).index(cat_id)]]

        # Convenient variables for categories
        self.ALL_CAT_ID = {}
        for grp_id, cats in self.CAT_ID.items():
            grp = self.GRP_VAR[grp_id]
            self.ALL_CAT_ID.update({grp + '.' + cat: cat_id for cat, cat_id in cats.items()})
        self.ALL_CAT_VAR = {}
        for grp_cat in self.CAT_VAR.values():
            self.ALL_CAT_VAR.update(grp_cat)

        self.N_GRP_CAT = len(self.CATEGORIES)
        self.N_CAT = 0
        for grp_cat in self.CATEGORIES.values():
            self.N_CAT += len(grp_cat)

        if set_globals:
            self.setGlobals()

    def _updateConfig(self, config_file):

        with open(config_file, 'r') as f:
            cfg = yaml.load(f.read()).data

        is_default = config_file == cst.DEFAULT_CONFIG_FILE

        if 'GRP_CATEGORIES' in cfg:
            self._loadCategoriesGroup(cfg['GRP_CATEGORIES'],
                                      is_default=is_default)

        if 'CATEGORIES' in cfg:
            self._loadCategories(cfg['CATEGORIES'], is_default=is_default)

        # Virtual categories
        default_grpcat = cfg.get('CAT_DEFAULT', 'GRP_QUALITY.CAT_NEUTRAL')
        default_grp, default_cat = default_grpcat.split('.')
        self.CAT_DEFAULT = self.CAT_ID[self.GRP_ID[default_grp]][default_cat]
        # self.cat_reset = int(cfg[cfg['cat_reset']]['ID'])

        if 'PERFORMANCES' in cfg:
            self.load_nsta = int(cfg['PERFORMANCES'].get('load_nsta', -1))
            self.load_first_page = yaml2bool(cfg['PERFORMANCES'].get('load_first_page', True))
            self.load_on_the_fly = yaml2bool(cfg['PERFORMANCES'].get('load_on_the_fly', False))
            #self.max_in_memory = int(cfg['PERFORMANCES'].get('max_in_memory', -1))
            self.downsampling_rate = int(cfg['PERFORMANCES'].get('downsampling_rate', 1))
            self.downsampling_threshold = int(cfg['PERFORMANCES'].get('downsampling_threshold', 0))
            self.downsampling_method = cfg['PERFORMANCES'].get('downsampling_method', 'naive')
            self.best_quality_on_hover = yaml2bool(cfg['PERFORMANCES'].get('best_quality_on_hover', 'True'))
            self.keep_best_quality = yaml2bool(cfg['PERFORMANCES'].get('keep_best_quality', 'True'))
            self.largeplot_update_threshold = int(cfg['PERFORMANCES'].get('largeplot_update_threshold', 10000))

        if 'SUBPLOTS' in cfg:
            self.subplot_type = cfg['SUBPLOTS'].get('plot_type', 'scatter')

        if 'LARGEPLOT' in cfg:
            self.largeplot_type = cfg['LARGEPLOT'].get('plot_type', 'scatter')

        if 'GRID' in cfg:
            self.nrows = int(cfg['GRID'].get('nrows', self.nrows))
            self.ncols = int(cfg['GRID'].get('ncols', self.ncols))
            self.auto_adjust_geometry = cfg['GRID'].get('auto_adjust_geometry', 'False')
            self.auto_adjust_geometry = yaml2bool(self.auto_adjust_geometry)
            self.auto_advance = cfg['GRID'].get('auto_advance', 'False')
            self.auto_advance = yaml2bool(self.auto_advance)

        if 'MAP' in cfg:
            self._loadMap(cfg)

        if 'MAP_OVERLAYS' in cfg:
            for layer, content in cfg['MAP_OVERLAYS'].items():
                self.map_overlays[layer] = copy.deepcopy(content)
                self.map_overlays[layer]['display'] = yaml2bool(self.map_overlays[layer]['display'])
                # self.map_overlays[layer]['load_at_startup'] = yaml2bool(self.map_overlays[layer]['load_at_startup'])
                self.map_overlays[layer]['alpha'] = float(self.map_overlays[layer].get('alpha', 1.))
                self.map_overlays[layer]['simplify'] = float(self.map_overlays[layer].get('simplify', 0.))

    def _loadCategoriesGroup(self, groups, is_default=False):

        # Default groups
        if is_default:
            # Default groups have an 1 <= ID < 10000 with step of 1000
            self.GRP_QUALITY = int(groups['GRP_QUALITY']['ID']) * 1000 # 1 * 1000
            self.GRP_GENERIC = int(groups['GRP_GENERIC']['ID']) * 1000 # 2 * 1000

        i = 1
        for group, params in groups.items():
            # Not modified at runtime (maybe in the future with custom groups)
            if group not in self.GRP_VAR.values():
                # Get or generate an ID
                if 'ID' in params:
                    grp_id = 1000 * int(params['ID'])
                else:
                    # User-defined groups have an ID > 10000 with step of 1000
                    grp_id = 10000 + 1000 * i
                    i += 1

                self.CATEGORIES[grp_id] = [] # dict with group IDs (unique integers) as keys
                self.GRP_VAR[grp_id] = group # map between group IDs and Python/yaml variables names
                self.CAT_VAR[grp_id] = dict()
                self.GRP_ID[group] = grp_id # map between Python/yaml variables names and group IDs
                self.CAT_ID[grp_id] = dict()
                self.cat_names[grp_id] = dict()
                self.cat_keys[grp_id] = dict()
            else:
                grp_id = self.GRP_ID[group]

            # Can be modified at runtime
            self.grp_name = params.get('name', group)
            self.grp_names[grp_id] = self.grp_name # map between IDs and group names

            # Keys assignment for category switching
            self.cat_switch[grp_id] = params.get('cat_switch', None)
            self.cat_reset[grp_id] = params.get('cat_reset', None)

            # Keys assignement for category shifting
            self.cat_shift_left[grp_id] = params.get('cat_shift_left', '+')
            if self.cat_shift_left[grp_id] not in ('+', '-'):
                self.cat_shift_left[grp_id] = self.CAT_ID['GRP_QUALITY'][self.cat_shift_left[grp_id]]
            self.cat_shift_right[grp_id] = params.get('cat_shift_right', '-')
            if self.cat_shift_right[grp_id] not in ('+', '-'):
                self.cat_shift_right[grp_id] = self.CAT_ID['GRP_QUALITY'][self.cat_shift_right[grp_id]]

    def _loadCategories(self, grp_categories, is_default=False):

        # Default categories
        if is_default:
            # Default categories have an ID < 100
            self.CAT_BAD = int(grp_categories['GRP_QUALITY']['CAT_BAD']['ID']) # -1
            self.CAT_NEUTRAL = int(grp_categories['GRP_QUALITY']['CAT_NEUTRAL']['ID']) # 0
            self.CAT_GOOD = int(grp_categories['GRP_QUALITY']['CAT_GOOD']['ID']) # 1
            # CAT_1 to CAT_9 have IDs 11 to 19

        last_categories = [] # to detect categories which are missing in the last config file
        for group, categories in grp_categories.items():
            grp_id = self.GRP_ID[group]

            # Category list and names
            i = 1
            last_categories += list(categories.keys())
            for cat, params in categories.items():
                # Not modified at runtime (maybe in the future with custom categories)
                if cat not in self.CAT_VAR[grp_id].values():
                    # Get or generate an ID
                    if 'ID' in params:
                        cat_id = int(params['ID'])
                    else:
                        # User-defined categories have an ID > 100
                        cat_id = 100 + i
                        i += 1

                    self.CATEGORIES[grp_id].append(cat_id) # list of IDs (unique integers)
                    self.CAT_VAR[grp_id][cat_id] = cat # map between IDs and Python/yaml variables names
                    self.CAT_ID[grp_id][cat] = cat_id # map between Python/yaml variables names and IDs
                else:
                    cat_id = self.CAT_ID[grp_id][cat]

                # Can be modified at runtime
                self.cat_name = params.get('name', cat)
                self.cat_names[grp_id][cat_id] = self.cat_name # map between IDs and category names

                self.cat_key = params.get('key', '')
                if not self.cat_key and cat[-2] == '_' and cat[-1] in '123456789':
                    # Auto key assignment for CAT_1 ... CAT_9
                    self.cat_key = cat[-1]
                self.cat_key = cst.QT_KEYS.get(self.cat_key, None)
                if self.cat_key:
                    self.cat_keys[grp_id][self.cat_key] = cat_id # map between Qt keys and IDs

    def _loadMap(self, cfg):

        self.proj = cfg['MAP'].get('projection', 'carree')
        self.map_resolution = cfg['MAP'].get('resolution', '110m')
        self.proj_options = cfg['MAP'].get('proj_options', dict())
        for option, value in self.proj_options.items():
            if value.lower() == 'none':
                self.proj_options[option] = None
            elif ',' in value:
                values = value.strip('() ').split(',')
                try:
                    self.proj_options[option] = [float(v) for v in values]
                except ValueError:
                    raise ValueError(f'Value of cartopy option {option} for ' \
                                     f'projection {proj} is invalid: {value}')
            else:
                try:
                    self.proj_options[option] = float(value)
                except ValueError:
                    pass

        if 'map_extent' in cfg['MAP']:
            self.map_extent = [None]*4
            self.map_extent[0] = float(cfg['MAP']['map_extent']['min_lon'])
            self.map_extent[1] = float(cfg['MAP']['map_extent']['max_lon'])
            self.map_extent[2] = float(cfg['MAP']['map_extent']['min_lat'])
            self.map_extent[3] = float(cfg['MAP']['map_extent']['max_lat'])
        else:
            self.map_extent = None

    def setGlobals(self):

        global nrows
        global ncols
        global auto_adjust_geometry
        global auto_advance
        global auto_switch_page

        # Subplots
        global subplot_type

        # Large/Big plot (I may use 'big' in the code because it's shorter)
        global largeplot_type

        # Map
        global proj
        global map_resolution
        global proj_options
        global map_extent

        global map_overlays

        # Performances
        global load_nsta
        global load_first_page
        global load_on_the_fly
        #global max_in_memory
        global downsampling_rate
        global downsampling_threshold
        global downsampling_method
        global best_quality_on_hover
        global keep_best_quality
        global largeplot_update_threshold

        # Anything related to the categories
        global CATEGORIES
        global GRP_VAR
        global GRP_ID
        global CAT_VAR
        global CAT_ID
        global ALL_CAT_ID
        global ALL_CAT_VAR
        global N_GRP_CAT
        global N_CAT
        # Some default IDs
        global GRP_QUALITY
        global GRP_GENERIC
        global CAT_DEFAULT
        global CAT_BAD
        global CAT_NEUTRAL
        global CAT_GOOD
        # For display in GUI
        global grp_names
        global cat_names
        # Keyboard-related
        global grp_keys
        global cat_keys
        global cat_switch
        global cat_shift_left
        global cat_shift_right
        global cat_reset

        global nplots

        ## Set the variables

        nrows = self.nrows
        ncols = self.ncols
        auto_adjust_geometry = self.auto_adjust_geometry
        auto_advance = self.auto_advance
        auto_switch_page = self.auto_switch_page

        # Subplots
        subplot_type = self.subplot_type

        # Large/Big plot (I use 'big' in the code because it's shorter)
        largeplot_type = self.largeplot_type

        # Map
        proj = self.proj
        map_resolution = self.map_resolution
        proj_options = self.proj_options
        map_extent = self.map_extent

        map_overlays = self.map_overlays

        # Performances
        load_nsta = self.load_nsta
        load_first_page = self.load_first_page
        load_on_the_fly = self.load_on_the_fly
        #max_in_memory = self.max_in_memory
        downsampling_rate = self.downsampling_rate
        downsampling_threshold = self.downsampling_threshold
        downsampling_method = self.downsampling_method
        best_quality_on_hover = self.best_quality_on_hover
        keep_best_quality = self.keep_best_quality
        largeplot_update_threshold = self.largeplot_update_threshold

        # Anything related to the categories
        CATEGORIES = self.CATEGORIES
        GRP_VAR = self.GRP_VAR
        GRP_ID = self.GRP_ID
        CAT_VAR = self.CAT_VAR
        CAT_ID = self.CAT_ID
        ALL_CAT_ID = self.ALL_CAT_ID
        ALL_CAT_VAR = self.ALL_CAT_VAR
        N_GRP_CAT = self.N_GRP_CAT
        N_CAT = self.N_CAT
        # Some default IDs
        GRP_QUALITY = self.GRP_QUALITY
        GRP_GENERIC = self.GRP_GENERIC
        CAT_DEFAULT = self.CAT_DEFAULT
        CAT_BAD = self.CAT_BAD
        CAT_NEUTRAL = self.CAT_NEUTRAL
        CAT_GOOD = self.CAT_GOOD
        # For display in GUI
        grp_names = self.grp_names
        cat_names = self.cat_names
        # Keyboard-related
        grp_keys = self.grp_keys
        cat_keys = self.cat_keys
        cat_switch = self.cat_switch
        cat_shift_left = self.cat_shift_left
        cat_shift_right = self.cat_shift_right
        cat_reset = self.cat_reset

        nplots = self.nplots

        if self.startup:
            # Select default group at startup
            global current_grp
            current_grp = self.GRP_QUALITY
            self.startup = False


## Convenient functions

def getNextCategory(staname, group=None):
    if not group:
        group = current_grp
    category = sta_category[staname][group]
    if category is not None:
        icategory = CATEGORIES[group].index(category)
        if icategory + 1 >= len(CATEGORIES[group]):
            return category
        return CATEGORIES[group][icategory + 1]
    else:
        return CATEGORIES[group][0]

def getPreviousCategory(staname, group=None):
    if not group:
        group = current_grp
    category = sta_category[staname][group]
    if category is not None:
        icategory = CATEGORIES[group].index(category)
        if icategory - 1 < 0:
            if group == GRP_QUALITY:
                return category
            else:
                return None
        return CATEGORIES[group][icategory - 1]
    else:
        return None

## Project-specific variables

# Grid
nrows, ncols = 6, 4 # geometry of the grid
auto_adjust_geometry = False # fill the view when nsta < nplots
auto_advance = False # move to next station after selecting a category
auto_switch_page = True # update the grid automatically when clicking on the map

# Subplots
subplot_type = 'scatter' # only option is 'scatter' for now

# Large/Big plot (I use 'big' in the code because it's shorter)
largeplot_type = 'scatter' # only option is 'scatter' for now

# Map
proj = ''
map_resolution = ''
proj_options = dict()
map_extent = None

map_overlays = dict()

# Performances
load_nsta = -1 # load this number of stations at startup (-1 == all)
load_first_page = True # always load all the data for the first grid page
load_on_the_fly = False # load the data only when needed
#max_in_memory = -1 # keep no more than this number of stations in memory (-1 == no limit)
downsampling_rate = 1 # no downsampling by default
downsampling_threshold = 1000 # no subsampling if there are less than n data
downsampling_method = 'naive' # only option is 'naive' for now
best_quality_on_hover = True # remove downsampling when hovering/selecting
keep_best_quality = True # make previous option persistent
largeplot_update_threshold = 10000 # don't auto update big plot if len(data) > threshold

# Anything related to the categories
CATEGORIES = dict()
GRP_VAR = dict() # map between group IDs and Python/yaml variables names
GRP_ID = dict() # map between Python/yaml variables names and group IDs
CAT_VAR = dict() # map between category IDs and Python/yaml variables names
CAT_ID = dict() # map between Python/yaml variables names and category IDs
GRP_QUALITY = None
GRP_GENERIC = None
ALL_CAT_ID = dict()
ALL_CAT_VAR = dict()
N_GRP_CAT = 0
N_CAT = 0
# Some default IDs
GRP_QUALITY = None
GRP_GENERIC = None
CAT_DEFAULT = 0
CAT_BAD = -1
CAT_NEUTRAL = 0
CAT_GOOD = 1
# For display in GUI
grp_names = dict()
cat_names = dict()
# Keyboard-related
grp_keys = dict()
cat_keys = dict()
cat_switch = dict()
cat_shift_left = dict()
cat_shift_right = dict()
cat_reset = dict()

nplots = 0

## Global variables used and modified at runtime

# Modal state
mode = cst.MODE_DEFAULT

# selected_sta = None # station selected with keyboard
plotted_sta = dict() # stations whose time series are currently displayed
sta_category = dict()
current_grp = GRP_QUALITY

# Dataset hook and shortcuts for things defined in dataset.py
dataset = None # TimeSeries instance: dataset.getData()
data = None # dict instance: data[staname] = ...
stalist = []
nsta = 0

# Selected data component
data_component = ''

# Filter history, read when a filter is reset
filter_history = dict()

# For fitted models
models = dict()

# Timeseries features for sorting and plotting
reference_point = (0, 0)
displayed_feature = ''
sort_by = '.DEFAULT'
sort_asc = True
pending_sort = False
