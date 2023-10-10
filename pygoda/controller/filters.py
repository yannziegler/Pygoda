# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import re

import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature
import geopandas as gpd
import shapely
from shapely import geometry as shapely_geom

import config as cfg

class CategoryFilter():

    def __init__(self):

        self.stalist = cfg.stalist_all

    def applyFilter(self, checked_categories, operator):

        if operator == 'AND':
            # AND between different groups
            self.stalist = self.andFilter(checked_categories)
        elif operator == 'OR':
            # OR between different groups
            self.stalist = self.orFilter(checked_categories)

        return self.stalist

    def andFilter(self, checked_categories):

        # Station selection from quality
        stalist_all = []
        checked_qualities = checked_categories[cfg.GRP_QUALITY]
        if not checked_qualities:
            # Ignore the filtering by quality
            stalist_all = cfg.stalist_all
        else:
            for sta in cfg.stalist_all:
                if cfg.sta_category[sta][cfg.GRP_QUALITY] in checked_qualities:
                    stalist_all.append(sta)
            del checked_categories[cfg.GRP_QUALITY]

        # Station selection from categories
        stalist = []
        for sta in stalist_all:
            filtered_out = False
            for grp, cats in checked_categories.items():
                if not cats:
                    continue
                if cfg.sta_category[sta][grp] not in cats:
                    filtered_out = True
                    break
            if not filtered_out:
                stalist.append(sta)

        return stalist

    def orFilter(self, checked_categories):

        stalist_all = cfg.stalist_all
        if not checked_categories[cfg.GRP_QUALITY]:
            # Select all the stations (for consistency)
            return stalist_all

        # Station selection from qualities or categories
        stalist = []
        for sta in stalist_all:
            filtered_out = True
            for grp, cats in checked_categories.items():
                if cfg.sta_category[sta][grp] in cats:
                    filtered_out = False
                    break
            if not filtered_out:
                stalist.append(sta)

        return stalist


class GeoFilter():

    def __init__(self):

        self.stalist = cfg.stalist_all

    def applyFilter(self, territory_tree, state):

        # Only keep the top-most level territories
        territory_tree = territory_tree['Planet Earth']['children']
        #print(territory_tree)
        self.pruneTerritories(territory_tree)
        #print(territory_tree)

        # Flatten the tree to get the simplest list of territories
        territories = self.flattenTree(territory_tree)
        #print(territories)

        # Load the polygons for the selected territories
        osm_regions = self.loadTerritoryPolygons(territories)
        regions = list(osm_regions.values())
        #print(osm_regions)

        # Union of all the MultiPolygons
        region = shapely.ops.unary_union(regions)

        # Filter
        self.stalist = []
        for sta in cfg.stalist_all:
            sta_data = cfg.dataset.getData(sta)
            lon, lat = sta_data.lon, sta_data.lat
            point = shapely_geom.Point(lon, lat)
            #print(sta, point)
            outside_region = not (state == QtCore.Qt.Checked)
            if region.contains(point) ^ outside_region:
                # (1) region is region of interest, outside_region = False:
                #     append when region contains station
                # (2) region is complement of ROI, outside_region = True:
                #     append when region does *not* contains station
                self.stalist.append(sta)

        return self.stalist

    def pruneTerritories(self, territory_tree):

        for territory, sub_tree in territory_tree.items():
            is_unsd_m49 = re.fullmatch('[0-9]{3}', territory) is not None
            if ('DEP_' not in territory) and \
               ('ADMIN_' not in territory) and \
               (not is_unsd_m49) and \
               sub_tree['state'] in (QtCore.Qt.Checked, QtCore.Qt.Unchecked):
                # No need to keep all the children separately,
                # unless it's an artificial group with no general polygon
                del territory_tree[territory]['children']
            else:
                self.pruneTerritories(territory_tree[territory]['children'])

    def flattenTree(self, territory_tree, territories=None):

        if territories is None:
            territories = {}

        for territory, sub_tree in territory_tree.items():
            is_unsd_m49 = re.fullmatch('[0-9]{3}', territory) is not None
            if ('DEP_' not in territory) and \
               ('ADMIN_' not in territory) and \
               (not is_unsd_m49) and \
               (sub_tree['state'] != QtCore.Qt.PartiallyChecked):
                territories[territory] = sub_tree['data']
            if 'children' in sub_tree:
                self.flattenTree(sub_tree['children'], territories)

        return territories

    def loadTerritoryPolygons(self, territories):
        wkt_name_one = "%s.wkt"
        wkt_name_two = "%s_%s.wkt"

        osm_regions = dict()

        for territory, fields in territories.items():
            if not fields.get('wikidata', ''):
                print('[Error] missing Wikidata ID for %s.' % territory)
                continue

            print('Loading poly for %s...' % territory, end='', flush=True)

            wikidata_id = fields['wikidata']
            if wikidata_id[0] == '~':
                wikidata_id = wikidata_id[1:]

            try:
                wkt_name = wkt_name_two % (wikidata_id, re.sub("[' ]", "+", territory))
                with open('data/WKT/' + wkt_name, 'r') as wkt_file:
                    wkt_content = wkt_file.read()
            except FileNotFoundError:
                try:
                    wkt_name = wkt_name_one % wikidata_id
                    with open('data/WKT/' + wkt_name, 'r') as wkt_file:
                        wkt_content = wkt_file.read()
                except FileNotFoundError:
                    print('\n [Error] no WKT file found.')
                    continue

            wkt_multipoly = wkt_content.split(';')[1]
            osm_regions[territory] = shapely.wkt.loads(wkt_multipoly)

            print("done")

        return osm_regions
