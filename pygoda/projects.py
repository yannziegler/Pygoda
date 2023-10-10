# coding: utf-8

from PySide2 import QtCore

import os

import strictyaml as yaml

import config as cfg
import constants as cst

class Projects():

    def __init__(self,
                 projects_filepath,
                 default_config=None,
                 default_themes=None):

        self.projects_filepath = projects_filepath

        self.projects = {}

        # Default config files
        if default_config:
            if isinstance(default_config, list):
                self.config_filepaths = default_config
            else:
                self.config_filepaths = [default_config]

        # Default theme files
        if default_themes:
            if isinstance(default_themes, list):
                self.themes_filepaths = default_themes
            else:
                self.themes_filepaths = [default_themes]

        self.loadProjectsList()

    def loadProjectsList(self):

        with open(self.projects_filepath, mode='r', encoding='utf8') as f:
            projects = yaml.load(f.read()).data

            assert 'PROJECTS' in projects
            self.projects = projects['PROJECTS']

    def getProjectsList(self):

        return list(self.projects.keys())

    def getProject(self, name=''):

        if not name:
            name = list(self.projects.keys())[0] # first one by default

        if name not in self.projects.keys():
            projects_list = ','.join(list(self.projects.keys()))
            print(f'Project "{name}" does not exist in {projects_file}, '
                  f'available projects are: {projects_list}')
            os.exit(1)

        project = Project(name,
                          self.projects[name]['basedir'],
                          default_config=self.config_filepaths,
                          default_themes=self.themes_filepaths)

        return project


class Project():

    def __init__(self,
                 name,
                 path,
                 default_config=None,
                 default_themes=None):

        self.name = name
        self.fullname = ''
        self.description = ''

        # Some directory and file paths
        self.project_path = path
        filepath = os.path.join(self.project_path, name + '.yaml')
        self.project_filepath = filepath # project file location
        self.basedir = '' # base directory of the project
        self.cat_lists_path = '' # where category lists are stored
        self.data_path = '' # data directory
        self.data_desc_filepath = '' # data description file
        self.stations_filepath = '' # station list file

        # Default and additional config files:
        # (1) Default Pygoda config.yaml
        # (2) User-defined global config*.yaml
        self.config_filepaths = []
        if default_config:
            if isinstance(default_config, list):
                self.config_filepaths += default_config
            else:
                self.config_filepaths = [default_config]
        # (3) Project-specific config {project_name}.yaml
        self.config_filepaths.append(self.project_filepath)
        # (4) Other files specified in project configuration
        # ...appended in self.readProject()

        # Default and additional theme files
        self.themes_filepaths = []
        if default_themes:
            if isinstance(default_themes, list):
                self.themes_filepaths += default_themes
            else:
                self.themes_filepaths = [default_themes]

        self.project = ''
        self.data_desc = ''
        self.stations = []
        self.nsta_max = 0

        self.config = None

    def _loadProjectYaml(self):

        with open(self.project_filepath, mode='r', encoding='utf8') as f:
            self.project = yaml.load(f.read()).data

    def readProject(self):

        if not self.project:
            self._loadProjectYaml()

        assert self.name == self.project['name']
        # Take the hash (int64) and keep the last 16 bits (uint16)
        # self.project_id = hash(self.name) & 0xFFFF
        self.fullname = self.project['fullname']
        self.description = self.project['description']

        self.basedir = self.project.get('basedir', self.project_path)
        self.cat_lists_path = os.path.join(self.basedir, self.name + '_lists')
        os.makedirs(self.cat_lists_path, exist_ok=True)

        self.data_path = self.project['DATA']['path']
        if not os.path.isabs(self.data_path):
            self.data_path = os.path.join(self.basedir, self.data_path)

        default_desc = os.path.splitext(self.data_path)[0] + ".yaml"
        self.data_desc_filepath = self.project['DATA'].get('descriptor',
                                                           default_desc)
        if not os.path.isabs(self.data_desc_filepath):
            self.data_desc_filepath = os.path.join(self.basedir, self.data_desc_filepath)
        with open(self.data_desc_filepath, mode='r', encoding='utf8') as f:
            self.data_desc = yaml.load(f.read()).data

        #TODO: implement stations list (Python-like), not external file
        stations_list = self.project['DATA'].get('stations_list', [])
        if isinstance(stations_list, str):
            # Path to file with list of stations
            self.stations_filepath = stations_list
            if not os.path.isabs(self.stations_filepath):
                self.stations_filepath = os.path.join(self.basedir,
                                                      self.stations_filepath)
            with open(self.stations_filepath, mode='r') as f:
                content = f.readlines()
            self.stations = [x.strip().split()[0] for x in content
                             if x[0] not in ('%', '#')]

        # Number of stations selected from the dataset; mostly useful for
        # quick testing/debugging with large datasets.
        # Not to be confused with the number of stations loaded *at startup*,
        # which depend on the parameters in PERFORMANCES section!
        self.nsta_max = int(self.project['DATA'].get('nsta_max', 0))

        if 'CONFIG' in self.project:

            # Project file which can contain both additional config and themes.
            # In such case, they will override everything else (append last).

            user_config = self.project['CONFIG'].get('config', '')
            if user_config:
                if not os.path.isabs(user_config):
                    user_config = os.path.join(self.basedir, user_config)
                self.config_filepaths.append(user_config)

            user_themes = self.project['CONFIG'].get('themes', '')
            if user_themes:
                if not os.path.isabs(user_themes):
                    user_themes = os.path.join(self.basedir, user_themes)
                self.themes_filepaths.append(user_themes)

    def loadConfig(self, set_globals=True):

        if not self.basedir:
            # We haven't read the project yet, we need to do it now,
            # otherwise some config files might be missing.
            self.readProject()

        self.config = cfg.ProjectConfiguration(self.config_filepaths)
        self.config.loadConfig(set_globals=set_globals)

        return self.config

