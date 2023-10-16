# coding: utf-8

# Everything in this file is hard-coded and *never* modified.

from PySide2 import QtCore
import os #, xdg bug with my xdg installation
import platform

APPNAME = 'Pygoda'
AUTHOR = 'Yann Ziegler'
AUTHOR_URL = 'https://yannziegler.com'
BIRTHPLACE = 'the University of Bristol'
BIRTHPLACE_URL = 'https://www.bristol.ac.uk/geography/research/bgc/'
LICENCE = 'EUPL-v1.2'
LICENCE_URL = 'https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12'
DOCUMENTATION = 'https://pygoda.readthedocs.io/en/latest'
GITHUB = 'https://github.com/yannziegler/Pygoda'
DEVELOP = True # develop, unstable version if True
VERSION = '0.1.0-alpha' # last release if DEVELOP
VERSION_URL = f'{GITHUB}/releases/tag/{VERSION}'
DATE = '2023-10-16'

QT_KEYS = {'ENTER': QtCore.Qt.Key_Enter,
           # 'ESC': QtCore.Qt.Key_Escape,
           # 'ESCAPE': QtCore.Qt.Key_Escape,
           'RETURN':QtCore.Qt.Key_Return,
           'DEL': QtCore.Qt.Key_Delete,
           'DELETE': QtCore.Qt.Key_Delete,
           'SPC': QtCore.Qt.Key_Space,
           'SPACE': QtCore.Qt.Key_Space,
           '+': QtCore.Qt.Key_Plus,
           '-': QtCore.Qt.Key_Minus,
           '0': QtCore.Qt.Key_0,
           '1': QtCore.Qt.Key_1,
           '2': QtCore.Qt.Key_2,
           '3': QtCore.Qt.Key_3,
           '4': QtCore.Qt.Key_4,
           '5': QtCore.Qt.Key_5,
           '6': QtCore.Qt.Key_6,
           '7': QtCore.Qt.Key_7,
           '8': QtCore.Qt.Key_8,
           '9': QtCore.Qt.Key_9}

# States of the stations in the GUI
DEFAULT = 0
HOVERED = 1
SELECTED = 2
# DEFAULT+HOVERED == HOVERED
# DEFAULT+SELECTED == SELECTED... convenient!
# HOVERED+SELECTED = 3, thus next states would be 4, 8, ...

STATES = {DEFAULT, HOVERED, SELECTED}
STATES_ID = {'DEFAULT': DEFAULT,
             'HOVERED': HOVERED,
             'SELECTED': SELECTED}
STATE_EVENTS = {HOVERED, ~HOVERED,
                SELECTED, ~SELECTED}

## Determine the kind of interactions the user has with the display
# Visualisation:
MODE_VISUALISATION = 0 # enter with ESC (default at startup)
#  - no selection
#  - change pages with arrows
#  - change category with +/- and 0-9
#  - set category for hovered
#  - delete key filters out
# Inspection:
MODE_INSPECTION = 1 # enter with 'I' or left-click, leave with ESC or right-click
#  - direct selection or multi-selection with Ctrl
#  - change pages with Ctrl+arrows
#  - change selection with arrows
#  - change category with +/- and 0-9
#  - set category for selected
#  - delete key filters out
# Categorisation:
MODE_CATEGORISATION = 2 # enter with 'C', leave with ESC
#  - single and multi-selection with Ctrl only, or no selection
#  - change pages with Ctrl+arrows
#  - change single selection with left/right arrows
#  - change category with up/down arrows, +/-, 0-9 or mouse buttons
#  - set category for hovered or selected
#  - delete key flags

MODE_DEFAULT = MODE_VISUALISATION # default at startup
MODES_NAME = {MODE_VISUALISATION: 'VISUALISATION',
              MODE_INSPECTION: 'INSPECTION',
              MODE_CATEGORISATION: 'CATEGORISATION'}
MODES_KEY = {MODE_VISUALISATION: 'Escape',
             MODE_INSPECTION: 'I',
             MODE_CATEGORISATION: 'C'}

# Default categories in the Generic group that can be enabled or disabled by the user
DEFAULT_CATEGORIES = {'CAT_1', 'CAT_2', 'CAT_3',
                      'CAT_4', 'CAT_5', 'CAT_6',
                      'CAT_7', 'CAT_8', 'CAT_9'}

# Config folder
if 'APPDATA' in os.environ:
    # Windows
    CONFIG_PATH = os.path.join(os.environ['APPDATA'], APPNAME.lower())
else:
    # GNU/Linux family
    # config_path = xdg.save_config_path('pygoda')
    CONFIG_PATH = os.path.join(os.environ['HOME'], '.config')
    CONFIG_PATH = os.path.join(CONFIG_PATH, APPNAME.lower())

# Default config files (installed with the software, read-only)
DEFAULT_CONFIG_FILE = 'config.yaml'
DEFAULT_THEMES_FILE = os.path.join('themes', 'themes.yaml')

# Template files
DEFAULT_CONFIG_TEMPLATE = os.path.join('templates', 'config_user.yaml')
DEFAULT_THEMES_TEMPLATE = os.path.join('templates', 'themes_user.yaml')

# User config template files (copied in $HOME/.config/APPNAME.lower())
# They can be duplicated, renamed and modified
USER_CONFIG_TEMPLATE = 'template_config_global.yaml'
USER_CONFIG_TEMPLATE = os.path.join(CONFIG_PATH, USER_CONFIG_TEMPLATE)
USER_THEMES_TEMPLATE = 'template_themes_global.yaml'
USER_THEMES_TEMPLATE = os.path.join(CONFIG_PATH, USER_THEMES_TEMPLATE)

# Default projects file
DEFAULT_PROJECTS_FILE = 'projects.yaml'
DEFAULT_PROJECTS_FILE = os.path.join(CONFIG_PATH, DEFAULT_PROJECTS_FILE)

# Regex for field matching in data files
# Used as: matches = [x.group() for x in re.finditer(REGEX_STRING, text)]
# _U: unsigned (sign might be there but is not included in match)
# _I: integer (numbers with no decimal point are accepted)
REGEX = {
    'DECIMAL': r'[+-]?([0-9]+\.[0-9]*)|([0-9]*\.[0-9]+)',
    # -1.23, +045., .6780
    'DECIMAL_U': r'([0-9]+\.[0-9]*)|([0-9]*\.[0-9]+)',
    # 1.23, 045., .6780
    'DECIMAL_I': r'[+-]?([0-9]+\.[0-9]*)|([0-9]*\.[0-9]+)|([0-9]+)',
    # -1.23, +045., .6780, -91011
    'DECIMAL_UI': r'([0-9]+\.[0-9]*)|([0-9]*\.[0-9]+)|([0-9]+)',
    # 1.23, 045., .6780, 91011
    'DMS': r'[+-]?([0-9]{1,3}[D°][0-5]?[0-9][M′\'])(([0-5]?[0-9]\.?)|([0-5]?[0-9]\.[0-9]+)|(\.[0-9]+))([S″"]|\'\')',
    # +023°43′19.7″, 1°09'59'', -007D31M.428
    'DMS_NSWE': r'([0-9]{1,3}[D°][0-5]?[0-9][M′\'])(([0-5]?[0-9]\.?)|([0-5]?[0-9]\.[0-9]+)|(\.[0-9]+))([S″"]|\'\')[NSWOE]'
    # 023°43′19.7″N, 1°09'59''W, 007D31M.428SS
}

# From: https://en.wikipedia.org/wiki/UN_M49
UNSD_M49 = {
  '002': {
    '015': ('012', '434', '504', '729', '732', '788', '818'),
    '202': {
      '011': ('132', '204', '270', '288', '324', '384', '430', '466', '478', '562', '566', '624', '654', '686', '694', '768', '854'),
      '014': ('086', '108', '174', '175', '231', '232', '260', '262', '404', '450', '454', '480', '508', '638', '646', '690', '706', '716', '728', '800', '834', '894'),
      '017': ('024', '120', '140', '148', '178', '180', '226', '266', '678'),
      '018': ('078', '426', '516', '710', '748'),
    },
  },
  '010': ('010', ),
  '019': {
    #'003': ('013', '021', '029'),
    '021': ('060', '124', '304', '666', '840'),
    '419': {
      '005': ('032', '068', '074', '076', '152', '170', '218', '238', '239', '254', '328', '600', '604', '740', '858', '862'),
      '013': ('084', '188', '222', '320', '340', '484', '558', '591'),
      '029': ('028', '044', '052', '092', '136', '192', '212', '214', '308', '312', '332', '388', '474', '500', '531', '533', '534', '535', '630', '652', '659', '660', '662', '663', '670', '780', '796', '850'),
    },
  },
  '142': {
    '030': ('156', '344', '392', '408', '410', '446', '496'),
    '034': ('004', '050', '064', '144', '356', '364', '462', '524', '586'),
    '035': ('096', '104', '116', '360', '418', '458', '608', '626', '702', '704', '764'),
    '143': ('398', '417', '762', '795', '860'),
    '145': ('031', '051', '048', '196', '268', '275', '368', '376', '400', '414', '422', '512', '634', '682', '760', '792', '784', '887'),
  },
  '150': {
    '039': ('008', '020', '070', '191', '292', '300', '336', '380', '470', '499', '620', '674', '688', '705', '724', '807'),
    '151': ('100', '112', '203', '348', '498', '616', '642', '643', '703', '804'),
    '154': ('208', '233', '234', '246', '248', '352', '372', '428', '440', '578', '744', '752', '826', '833',
      {'830': ('831', '832', '680')}
    ),
    '155': ('040', '056', '250', '276', '438', '442', '492', '528', '756'),
  },
  '009': {
    '053': ('036', '162', '166', '334', '554', '574'),
    '054': ('090', '242', '540', '548', '598'),
    '057': ('296', '316', '520', '580', '581', '583', '584', '585'),
    '061': ('016', '184', '258', '570', '612', '772', '776', '798', '876', '882'),
  },
}

UNSD_M49_NAMES = {
'001': "World",
'002': "Africa",
'015': "Northern Africa",
'202': "Sub-Saharan Africa",
'011': "Western Africa",
'014': "Eastern Africa",
'017': "Middle Africa",
'018': "Southern Africa",
'010': "Antarctica",
'019': "Americas",
#'003': "North America",
'021': "Northern America",
'419': "Latin America and the Caribbean",
'005': "South America",
'013': "Central America",
'029': "Caribbean",
'142': "Asia",
'030': "Eastern Asia",
'034': "Southern Asia",
'035': "South-eastern Asia",
'143': "Central Asia",
'145': "Western Asia",
'150': "Europe",
'039': "Southern Europe",
'151': "Eastern Europe (w/Siberia)",
'154': "Northern Europe",
'830': "Channel Islands",
'155': "Western Europe",
'009': "Oceania",
'053': "Australia and New Zealand",
'054': "Melanesia",
'057': "Micronesia",
'061': "Polynesia"
}
