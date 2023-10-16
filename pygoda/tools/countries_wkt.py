# coding: utf-8

import re, time
import strictyaml as yaml

import numpy as np

import geopandas as gpd
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely import wkt

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature

import matplotlib.pyplot as plt

shp_basins = gpd.read_file('data/RiverBasins/basins.shp')
print(shp_basins.keys())
print(shp_basins['NAME'])
print(shp_basins['geometry'])

proj = ccrs.PlateCarree()
fig = plt.figure()
ax = plt.axes(projection=proj)
ax.coastlines(resolution='110m')

for region in shp_basins['geometry']: # plot all the content of the Shapefile
    region_feature = ShapelyFeature([region,], proj)
    color = '#%02X%02X%02X' % tuple(np.random.randint(255, size=3))
    ax.add_feature(region_feature, edgecolor='black', facecolor=color, alpha=0.3, zorder=1e9)
print(dir(ax.bbox))
print(ax.bbox._bbox.x0)

rect = ax.bbox._bbox.x0, ax.bbox._bbox.y0, \
       ax.bbox._bbox.x1-ax.bbox._bbox.x0, \
       ax.bbox._bbox.y1-ax.bbox._bbox.y0
ax2 = fig.add_axes(rect, frameon=False) #, projection=proj)
# print(ax2)
# print(dir(ax2.patch))
ax2.patch.set_visible = False
ax2.set_xlim([-180, 180])
ax2.set_ylim([-90, 90])
ax2.scatter([0, 10, 20], [0, 10, 20], s=20, color='black')

plt.show()


exit()

# Load my country hierarchy
# countries_schema = yaml.Map({'dependencies': yaml.Seq(yaml.Str())})
with open('data/countries.yaml', 'r') as f:
    countries_tree = yaml.load(f.read()).data
# print(countries_tree)

# Use NaturalEarth Shapefiles (low resolution - 10m scale)
if False:
    # shp_file = gpd.read_file('data/ShapeFiles/ne_10m_admin_0_boundary_lines_land/ne_10m_admin_0_boundary_lines_land.shp')
    # shp_file = gpd.read_file('data/ShapeFiles/ne_10m_admin_0_countries_lakes/ne_10m_admin_0_countries_lakes.shp')
    # shp_dataframe = gpd.read_file('data/ShapeFiles/ne_10m_admin_0_scale_rank_minor_islands/ne_10m_admin_0_scale_rank_minor_islands.shp')
    # shp_dataframe = gpd.read_file('data/ShapeFiles/ne_10m_admin_0_map_units/ne_10m_admin_0_map_units.shp')
    shp_dataframe = gpd.read_file('data/ShapeFiles/ne_10m_admin_0_map_subunits/ne_10m_admin_0_map_subunits.shp')
    # print(shp_dataframe.keys())
    # print(shp_dataframe.crs) # epsg:4326

    # print(shp_dataframe['sr_subunit'])
    # print(shp_dataframe['scalerank'])
    # print(shp_dataframe['sr_gu_a3'])

    id_field = 'NAME' # 'sr_subunit'

    regions = dict()
    n_regions = 0
    list_countries = set(list(shp_dataframe[id_field].values))
    for country_code, fields in countries_tree.items():
        country_name = fields['fullname']

        # shp_df = shp_dataframe[shp_dataframe['scalerank'] < 3]
        shp_df = shp_dataframe

        if 'NAME' not in fields['naturalearth']:
            print('NAME field missing!', country_name)
            continue

        units = fields['naturalearth'][id_field]
        if not isinstance(units, list):
            units = [units]

        shp_indices = False
        for unit in units:
            shp_indices |= shp_df[id_field] == unit
            if shp_df[shp_df[id_field] == unit].shape[0]:
                list_countries.remove(unit)

        shp_df = shp_df[shp_indices]
        if npoly := shp_df.shape[0]:
            # print(country_name, npoly)
            n_regions += npoly
            regions[country_code] = shp_df['geometry'].values

    print('Remaining countries:')
    for country in list_countries:
        print('Not plotted:', country)
    print('Countries in Shapefile:', shp_dataframe.shape[0])
    print('Plotted countries:', n_regions)


# Use WKT files
if True:
    wkt_name_one = '%s.wkt'
    wkt_name_two = '%s_%s.wkt'

    osm_regions = dict()

    for country, fields in countries_tree.items():
        if not fields['wikidata']:
            print('Warning: missing Wikidata ID for %s.' % country)
            continue

        print('Loading poly for %s...' % country, end='', flush=True)

        wikidata_id = fields['wikidata']
        if wikidata_id[0] == '~':
            wikidata_id = wikidata_id[1:]
        try:
            wkt_name = wkt_name_two % (wikidata_id, re.sub("[' ]", "+", country))
            with open('data/WKT/'+wkt_name, 'r') as wkt_file:
                wkt_content = wkt_file.read()
        except FileNotFoundError:
            try:
                wkt_name = wkt_name_one % wikidata_id
                with open('data/WKT/'+wkt_name, 'r') as wkt_file:
                    wkt_content = wkt_file.read()
            except FileNotFoundError:
                print(' [Warning] no WKT file found.')
                continue

        wkt_multipoly = wkt_content.split(';')[1]
        osm_regions[country] = wkt.loads(wkt_multipoly)
        print('done')


# Use Water polygon Shapefile (high resolution, extracted from OSM)
if False:
    print('Loading water shp...', end='', flush=True)
    shp_water = gpd.read_file('data/ShapeFiles/water-polygons-split-4326/water_polygons.shp')
    print('done')

    regions = dict()
    regions['FRA'] = osm_regions['FRA']
    print('Converting to MultiPoly...', end='', flush=True)
    poly_union = None
    i = 0
    for poly in shp_water['geometry'].values:
        if i % 100 == 0:
            print(i)
        shape_poly = shape(poly)
        if not shape_poly.is_valid:
            print(i, 'not valid')
            shape_poly = shape_poly.buffer(0)
        if shape_poly.intersects(geom):
            if not poly_union:
                poly_union = shape_poly
            else:
                poly_union.union(shape_poly)
        i += 1
    geom_water = MultiPolygon([poly_union])
    print(type(geom_water))
    print('done')
    print('Computing intersection...', end='', flush=True)
    water = geom.intersection(geom_water)
    print('done')
    regions['FRA_Water'] = MultiPolygon([water])
    regions['FRA_Land'] = geom.difference(water)

# country_tree = dict()
# self.recursiveShapefileLoad(country_tree, 1, shp_dataframe)
# print(country_tree)
# print(len(country_tree))

# for NAME, GEOUNIT, SUBUNIT in zip(shp_dataframe['NAME'], shp_dataframe['GEOUNIT'], shp_dataframe['SUBUNIT']):
#     print(NAME)#, GEOUNIT, SUBUNIT)

# Plot with Cartopy
proj = ccrs.PlateCarree()
fig = plt.figure()
ax = plt.axes(projection=proj)
ax.coastlines(resolution='110m')

# for region_code, region in regions.items():
# # for region in shp_dataframe['geometry'].values: # plot all the content of the Shapefile
#     region_feature = ShapelyFeature(region, proj)
#     color = '#%02X%02X%02X' % tuple(np.random.randint(255, size=3))
#     ax.add_feature(region_feature, edgecolor='black', facecolor=color, alpha=0.3, zorder=1e9)

for region_code, region in osm_regions.items():
# for region in shp_dataframe['geometry'].values: # plot all the content of the Shapefile
    region_feature = ShapelyFeature(region, proj)
    color = '#%02X%02X%02X' % tuple(np.random.randint(255, size=3))
    ax.add_feature(region_feature, edgecolor='black', facecolor=color, alpha=0.3, zorder=1e9)

plt.show()


def recursiveShapefileLoad(country_tree, target_rank, shp_dataframe):
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

