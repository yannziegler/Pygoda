# coding: utf-8

import copy
import os
import datetime

import numpy as np

import constants as cst
import config as cfg

class CategoryDB():

    def __init__(self,
                 categories=None,
                 cat_names=None,
                 grp_vars=None,
                 cat_vars=None,
                 grp_names=None,
                 split_category=False):

        self.categories = categories if categories else copy.deepcopy(cfg.CATEGORIES)
        self.cat_names = cat_names if cat_names else copy.deepcopy(cfg.cat_names)
        self.grp_vars = grp_vars if grp_vars else copy.deepcopy(cfg.GRP_VAR)
        self.cat_vars = cat_vars if cat_vars else copy.deepcopy(cfg.CAT_VAR)
        self.grp_names = grp_names if grp_names else copy.deepcopy(cfg.grp_names)
        self.split_category = split_category

        if self.split_category:
            # Write several files with the category number in filename
            self.cat_files = dict()
            for group, categories in self.categories.items():
                grp_name = self.grp_names[group]
                grp_var = self.grp_vars[group]
                for category in categories:
                    cat_name = self.cat_names[group][category]
                    cat_var = self.cat_vars[group][category]
                    grp_cat = (group, category)
                    self.cat_files[grp_cat] = SingleCategoryFile(grp_cat,
                                                                 (grp_name, cat_name),
                                                                 (grp_var, cat_var))
        else:
            # ...otherwise write a single file with the category number for each station
            self.multicat_file = MultiCategoriesFile(self.categories,
                                                     grp_names=self.grp_names,
                                                     cat_names=self.cat_names)

    def __addCustomCategory(self, group, category, cat_name=None):
        #TODO: not working yet
        if not cat_name:
            cat_name = str(category)
        self.categories[group].append(category)
        self.cat_names[group].append(cat_name)

        if self.split_category:
            grp_name = self.grp_names[group]
            grp_cat = (group, category)
            self.cat_files[grp_cat] = SingleCategoryFile(grp_cat,
                                                         (grp_name, cat_name),
                                                         (grp_var, cat_var))
        else:
            self.multicat_file = MultiCategoriesFile(self.categories,
                                                     grp_names=self.grp_names,
                                                     cat_names=self.cat_names)

    def writeCategory(self, group, category):
        if self.split_category:
            self.cat_files[(group, category)].write()
        else:
            self.multicat_file.write()

    def writeAllCategories(self):
        if self.split_category:
            for group, categories in self.categories.items():
                for category in categories:
                    grp_cat = (group, category)
                    self.cat_files[grp_cat].write()
        else:
            self.multicat_file.write()

    def readCategories(self, stalist):
        sta_category = {sta: {group: None for group in self.categories} for sta in stalist}
        for sta in stalist:
            sta_category[sta][cfg.GRP_QUALITY] = cfg.CAT_DEFAULT

        if self.split_category:
            for group in self.categories:
                for category in self.categories[group]:
                    try:
                        grp_cat = (group, category)
                        list_sta = self.cat_files[grp_cat].read()
                    except FileNotFoundError:
                        list_sta = []
                    finally:
                        for sta in list_sta:
                            if sta in sta_category:
                                sta_category[sta][group] = category
        else:
            read_sta_category = self.multicat_file.read()
            for sta, categories in read_sta_category.items():
                if sta in sta_category:
                    sta_category[sta].update(categories)

        return sta_category


class SingleCategoryFile():

    def __init__(self, grp_cat, names, unique_names, write_header=True):

        self.group, self.category = grp_cat
        self.grp_name, self.cat_name = names
        self.grp_uid, self.cat_uid = unique_names

        self.write_header = write_header
        self.header = ""
        if self.write_header:
            self.header = self.makeHeader()

        self.filename = self.grp_uid + '_' + self.cat_uid + '.txt'
        self.category_file = os.path.join(cfg.basedir_cat, self.filename)

    def makeHeader(self):
        header = "# This file is part of the project %s\n" % cfg.project_name
        header += "# Last update: %s\n"
        header += "# The following stations are in %s/%s:\n" % (self.grp_name, self.cat_name)

        return header

    def read(self):

        try:
            with open(self.category_file, 'r') as f:
                list_sta = f.readlines()
            list_sta = [sta.strip() for sta in list_sta
                        if sta[0] != '#']
        except FileNotFoundError:
            list_sta = []

        return list_sta

    def write(self, sta_category=None):

        sta_category = sta_category if sta_category else cfg.sta_category

        empty_list = True
        with open(self.category_file, 'w') as f:
            if self.write_header:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(self.header % now)
            for staname in sta_category:
                if cfg.sta_category[staname][self.group] == self.category:
                    empty_list = False
                    f.write(staname+'\n')

        if empty_list and os.path.exists(self.category_file):
            os.remove(self.category_file)


class MultiCategoriesFile():

    def __init__(self,
                 categories,
                 grp_names=None,
                 cat_names=None,
                 write_header=True):

        self.categories = copy.deepcopy(categories)
        self.grp_names = copy.deepcopy(grp_names)
        self.cat_names = copy.deepcopy(cat_names)

        self.write_header = write_header
        self.header = ""
        if self.write_header:
            self.header = self.makeHeader()

        self.filename = cfg.project_name + '_categories.txt'
        self.categories_file = os.path.join(cfg.basedir_cat, self.filename)

    def makeHeader(self):
        header = "# This file is part of the project %s\n" % cfg.project_name
        header += "# Last update: %s\n"
        header += "# It stores the categories of each station for each group as:\n"
        header += "#  STATION ID_GRP_1:ID_CATEGORY_1,ID_GRP_2:ID_CATEGORY_2,...\n"
        header += "# Note: stations in default/no category are not listed.\n"
        if self.grp_names:
            header += "# Group/category IDs correspondances:\n"
            for grp in self.categories:
                grp_name = self.grp_names[grp]
                header += "# %d: %s" % (grp, grp_name)
                if not self.cat_names:
                    continue
                header += "\n"
                for cat in self.categories[grp]:
                    cat_name = self.cat_names[grp][cat]
                    header += "#  > %d: %s\n" % (cat, cat_name)
        if header[-1] != "\n":
            header += "\n"

        return header

    def read(self):

        try:
            with open(self.categories_file, 'r') as f:
                entries = f.readlines()
            entries = [entry.strip() for entry in entries
                       if entry[0] != '#']
        except FileNotFoundError:
            return {}

        stalist = []
        sta_category = {}
        for entry in entries:
            staname, categories = entry.split(' ')
            stalist.append(staname)
            sta_category[staname] = {group: None for group in self.categories}
            grp_cat_list = categories.split(',')
            for grp_cat in grp_cat_list:
                group, category = grp_cat.split(':')
                group, category = int(group), int(category)
                sta_category[staname][group] = category

        for sta in stalist:
            if not sta_category[sta][cfg.GRP_QUALITY]:
                sta_category[sta][cfg.GRP_QUALITY] = cfg.CAT_DEFAULT

        return sta_category

    def write(self):

        sta_category = cfg.sta_category

        with open(self.categories_file, 'w') as f:
            if self.write_header:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(self.header % now)
            for staname in sta_category:
                str_categories = ''
                for group, category in sta_category[staname].items():
                    if not category or (group == cfg.GRP_QUALITY and category == cfg.CAT_DEFAULT):
                        continue
                    if str_categories:
                        str_categories += ','
                    str_categories += str(group) + ':' + str(category)
                    f.write("{:s} {:s}\n".format(staname, str_categories))
