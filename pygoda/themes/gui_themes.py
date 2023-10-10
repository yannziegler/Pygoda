# coding: utf-8

import os, copy

import strictyaml as yaml

# plt.rcParams['toolbar'] = 'none'

import constants as cst
import config as cfg

# Actually not necessary
# def hex2mpl(color):
#     if '#' not in color:
#         return color # not an hexa color
#     color = color.lstrip('#')
#     return tuple(int(color[i:i+2], 16)/255 for i in (0, 2, 4))

ax_color = ''
ax_spines_color = ''
ax_spines_width = 0.0
data_color = ''
markers_color = ''
station_name_color = ''
events_color = ''
stations_color = ''
stations_shape = ''
stations_size = ''
ax_color = ''
ax_spines_color = ''
ax_spines_width = ''
data_color = ''
station_name_color = ''
markers_color = ''
events_color = ''
stations_color = ''
stations_shape = ''
stations_size = 0
figure_color = ''
figure_color = ''
map_colors = ''

class Themes():

    def __init__(self, themes_files):

        self.selected_main_theme = ''
        self.selected_map_theme = ''

        # Prepare the dicts for each themed feature
        self.ax_color, self.ax_spines_color, self.ax_spines_width = dict(), dict(), dict()
        self.data_color, self.markers_color, self.station_name_color, self.events_color = dict(), dict(), dict(), dict()
        self.stations_color, self.stations_shape, self.stations_size = dict(), dict(), dict()
        for cat in cfg.ALL_CAT_ID.values():
            # plot
            self.ax_color[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            self.ax_spines_color[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            self.ax_spines_width[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            self.data_color[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            self.station_name_color[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            self.markers_color[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            self.events_color[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            # map
            self.stations_color[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            self.stations_shape[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
            self.stations_size[cat] = {cst.DEFAULT: None, cst.HOVERED: None, cst.SELECTED: None}
        self.figure_color = dict()
        self.figure_color['background'] = '#273746'
        self.map_colors = dict()
        self.map_colors['continents'] = '#2A2A28'
        self.map_colors['oceans'] = '#88adc8'

        # Fallback values
        self.ocean_color_raw = self.map_colors['oceans']
        self.continent_color_raw = self.map_colors['continents']

        self.palettes = dict()
        self.themes = dict()
        self.cat_themes = dict()
        # /!\ CAT_NEUTRAL first as it is the fallback category
        self.cat_desc = {cfg.CAT_NEUTRAL: dict()}
        self.cat_desc.update({cat: dict() for cat in cfg.ALL_CAT_ID.values() if cat != cfg.CAT_NEUTRAL})
        self.cat_generic = dict()

        # (1) Load the palettes, themes, categories themes and categories descriptions

        for theme_file in themes_files:

            with open(theme_file, 'r') as f:
                thm = yaml.load(f.read()).data

            if 'DEFAULT_THEME' in thm:
                # Last selected overwrite the previous ones
                self.DEFAULT_THEME = thm['DEFAULT_THEME']

            if 'theme' in thm:
                # Last selected overwrite the previous ones
                self.selected_main_theme = thm['theme']

            if 'PALETTES' in thm:
                self.palettes.update(thm['PALETTES'])

            if 'THEMES' in thm:
                self.themes.update(thm['THEMES'])

            if 'CATEGORIES_THEMES' in thm:
                self.cat_themes.update(thm['CATEGORIES_THEMES'])

            if 'CATEGORIES' in thm:
                for cat in self.cat_desc:
                    cat_var = cfg.ALL_CAT_VAR[cat]
                    feat = thm['CATEGORIES'].get(cat_var, dict())
                    if feat:
                        self.cat_desc[cat] = copy.deepcopy(feat)
                    elif self.cat_desc[cat]:
                        # This category was defined in another file
                        continue
                    elif 'CAT_GENERIC' in thm['CATEGORIES']:
                        # Category is missing but CAT_GENERIC is defined
                        self.cat_desc[cat] = copy.deepcopy(thm['CATEGORIES']['CAT_GENERIC'])

            if 'MAP' in thm:
                if 'theme' in thm['MAP']:
                    self.selected_map_theme = thm['MAP']['theme']
                if 'ocean_color' in thm['MAP']:
                    self.ocean_color_raw = thm['MAP']['ocean_color']
                if 'continent_color' in thm['MAP']:
                    self.continent_color_raw = thm['MAP']['continent_color']

        # Check that a theme is selected
        if not self.selected_main_theme:
            self.selected_main_theme = self.DEFAULT_THEME

        if not self.selected_map_theme:
            self.selected_map_theme = self.selected_main_theme

        # Check that all categories have a theme
        for cat, feat in self.cat_desc.items():
            if not feat:
                cat_var = cfg.ALL_CAT_VAR[cat]
                raise ValueError('Category %s has no theme definition: define %s or CAT_GENERIC.' % (cat_var, cat_var))

        # (2a) Get the color values from the palettes for the categories

        # First, get the DEFAULT colors
        if 'palette' in self.cat_themes['DEFAULT']:
            palette = self.palettes[self.cat_themes['DEFAULT']['palette']]
            del self.cat_themes['DEFAULT']['palette']
            for cat, color in self.cat_themes['DEFAULT'].items():
                if color in palette:
                    self.cat_themes['DEFAULT'][cat] = palette[color]
                else:
                    assert color[0] == '#' or color in ('white', 'black')

        # Then, complete all the themes with the default values
        # and get all the colors for the themes
        for theme_name, theme in self.cat_themes.items():
            if theme_name == 'DEFAULT':
                continue
            # Use DEFAULT colors as fallback for missing categories
            for cat in cfg.ALL_CAT_VAR.values():
                if cat != 'CAT_NEUTRAL' and cat not in theme:
                    self.cat_themes[theme_name][cat] = self.cat_themes['DEFAULT'][cat]
            if 'palette' in theme:
                palette = self.palettes[theme['palette']]
                del self.cat_themes[theme_name]['palette']
                for cat, color in theme.items():
                    if color in palette:
                        self.cat_themes[theme_name][cat] = palette[color]
                    else:
                        assert color[0] == '#' or color in ('white', 'black')

        # (2b) Get the color values from the palettes for the main themes
        #      We also import the category colors in the main themes

        # First, get the DEFAULT colors
        if 'palette' in self.themes[self.DEFAULT_THEME]:
            palette = self.palettes[self.themes[self.DEFAULT_THEME]['palette']]
            del self.themes[self.DEFAULT_THEME]['palette']
            for param, value in self.themes[self.DEFAULT_THEME].items():
                if param == 'category':
                    continue
                if value in palette: # 'value' is a color!
                    self.themes[self.DEFAULT_THEME][param] = palette[value]
                else:
                    assert value[0] == '#' or value in ('white', 'black')
        self.themes[self.DEFAULT_THEME].update(self.cat_themes[self.themes[self.DEFAULT_THEME]['category']])
        del self.themes[self.DEFAULT_THEME]['category']

        # Then, complete all the themes with the default values
        for theme_name, theme in self.themes.items():
            if theme_name == self.DEFAULT_THEME:
                continue
            # Use DEFAULT colors as fallback for missing params
            for param in self.themes[self.DEFAULT_THEME]:
                if param not in theme:
                    self.themes[theme_name][param] = self.themes[self.DEFAULT_THEME][param]
            if 'palette' in theme:
                palette = self.palettes[theme['palette']]
                # del theme['palette']
                for param, value in theme.items():
                    if param == 'palette' or param == 'category':
                        continue
                    if value in palette: # 'value' is a color!
                        theme[param] = palette[value]
                    else:
                        assert value[0] == '#' or value in ('white', 'black')
            self.themes[theme_name].update(self.cat_themes[theme.get('category', 'DEFAULT')])
            del self.themes[theme_name]['category']

        # (3) Setup the selected theme
        self.applyThemes(self.selected_main_theme, self.selected_map_theme)

    def setupSelectedTheme(self, cat, state, elements):

        if state in (cst.HOVERED, cst.SELECTED):
            # Inherit missing values from DEFAULT state of the *same* category
            fallback_cat = cat
        else: # DEFAULT
            # Inherit missing values from DEFAULT state of CAT_NEUTRAL
            fallback_cat = cfg.CAT_NEUTRAL

        for element in ('plot', 'map'):
            if element not in elements:
                elmt = dict()
            else:
                elmt = copy.deepcopy(elements[element])

            for feature, value in elmt.items():
                if value == 'CAT_COLOR':
                    # SELF.CAT_COLOR is a generic placeholder for the current category color
                    # Note that from now on, we know that 'value' *must be* in 'theme'
                    value = cfg.ALL_CAT_VAR[cat]

                if value in self.theme:
                    elmt[feature] = self.theme[value]

            if element == 'plot':
                self.ax_color[cat][state] = elmt.get('ax_color',
                                                self.ax_color[fallback_cat][cst.DEFAULT])
                self.ax_spines_color[cat][state] = elmt.get('ax_spines_color',
                                                    self.ax_spines_color[fallback_cat][cst.DEFAULT])
                self.ax_spines_width[cat][state] = int(elmt.get('ax_spines_width',
                                                        self.ax_spines_width[fallback_cat][cst.DEFAULT]))
                self.data_color[cat][state] = elmt.get('data_color',
                                                  self.data_color[fallback_cat][cst.DEFAULT])
                self.markers_color[cat][state] = elmt.get('markers_color',
                                                  self.markers_color[fallback_cat][cst.DEFAULT])
                self.station_name_color[cat][state] = elmt.get('station_name_color',
                                                        self.station_name_color[fallback_cat][cst.DEFAULT])
                self.events_color[cat][state] = elmt.get('events_color',
                                                self.events_color[fallback_cat][cst.DEFAULT])
            elif element == 'map':
                self.stations_color[cat][state] = elmt.get('stations_color',
                                                    self.stations_color[fallback_cat][cst.DEFAULT])
                self.stations_shape[cat][state] = elmt.get('stations_shape',
                                                    self.stations_shape[fallback_cat][cst.DEFAULT])
                self.stations_size[cat][state] = int(elmt.get('stations_size',
                                                    self.stations_size[fallback_cat][cst.DEFAULT]))

    def applyThemes(self, main_theme_name=None, map_theme_name=None):

        if main_theme_name:
            self.selected_main_theme = main_theme_name

            print('Applying %s theme...' % self.selected_main_theme)
            self.theme = copy.deepcopy(self.themes[self.selected_main_theme])

            for cat, states in self.cat_desc.items():
                for state_name, state_id in cst.STATES_ID.items():
                    self.setupSelectedTheme(cat, state_id, states[state_name])

            if 'figure' in self.theme:
                self.figure_color['background'] = self.theme['figure']

        if map_theme_name:
            self.selected_map_theme = map_theme_name

            print('Applying %s theme to the map...' % self.selected_map_theme)
            self.map_theme = copy.deepcopy(self.themes[self.selected_map_theme])

            if self.ocean_color_raw in self.map_theme:
                self.map_colors['oceans'] = self.map_theme[self.ocean_color_raw]
                if 'palette' in self.map_theme and self.map_colors['oceans'] in self.map_theme['palette']:
                    self.map_colors['oceans'] = self.map_theme['palette'][self.map_colors['oceans']]
            else:
                 self.map_colors['oceans']= self.ocean_color_raw

            if self.continent_color_raw in self.map_theme:
                self.map_colors['continents'] = self.map_theme[self.continent_color_raw]
                if 'palette' in self.map_theme and self.map_colors['continents'] in self.map_theme['palette']:
                    self.map_colors['continents'] = map_theme['palette'][self.map_colors['continents']]
            else:
                self.map_colors['continents'] = self.continent_color_raw

        self.setGlobals()

    def iterateThemes(self):
        for theme in self.themes:
            yield theme

    def setGlobals(self):

        global ax_color, ax_spines_color, ax_spines_width
        global data_color, markers_color, station_name_color, events_color
        global stations_color, stations_shape, stations_size
        global ax_color
        global ax_spines_color
        global ax_spines_width
        global data_color
        global station_name_color
        global markers_color
        global events_color
        global stations_color
        global stations_shape
        global stations_size
        global figure_color
        global figure_color
        global map_colors

        ax_color = self.ax_color
        ax_spines_color = self.ax_spines_color
        ax_spines_width = self.ax_spines_width
        data_color = self.data_color
        markers_color = self.markers_color
        station_name_color = self.station_name_color
        events_color = self.events_color
        stations_color = self.stations_color
        stations_shape = self.stations_shape
        stations_size = self.stations_size
        ax_color = self.ax_color
        ax_spines_color = self.ax_spines_color
        ax_spines_width = self.ax_spines_width
        data_color = self.data_color
        station_name_color = self.station_name_color
        markers_color = self.markers_color
        events_color = self.events_color
        stations_color = self.stations_color
        stations_shape = self.stations_shape
        stations_size = self.stations_size
        figure_color = self.figure_color
        figure_color = self.figure_color
        map_colors = self.map_colors
