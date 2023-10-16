# coding: utf-8

import numpy as np
import scipy as sp

import cartopy.feature as cfeature
import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature
import matplotlib.transforms as transforms
#from shapely.geometry import shape, Point, MultiPoint, Polygon, MultiPolygon
import shapely.geometry as geom
from shapely import wkt

PROJ_CARREE = ccrs.PlateCarree()
PROJ_GEODETIC = ccrs.Geodetic()
PROJ2CARTOPY = {'carree': ccrs.PlateCarree()} # populated in config.py

def transformProj(lon, lat, proj_new, proj_src=PROJ_CARREE, single_array=False):

    lon, lat = np.asarray(lon), np.asarray(lat)
    lonlat_new = proj_new.transform_points(proj_src, lon, lat)

    if single_array:
        return lonlat_new[:, :2]
    else:
        return lonlat_new[:, 0], lonlat_new[:, 1]

def transformExtentProj(extent, proj_new, proj_src=PROJ_CARREE):

    x, y = np.asarray(extent[:2]), np.asarray(extent[2:])
    xy_proj = proj_new.transform_points(proj_src, x, y)
    return [xy_proj[0, 0], xy_proj[1, 0], xy_proj[0, 1], xy_proj[1, 1]]

def convexHull(lon, lat):
    """Compute the convex hull of a network of stations"""

    sta_multipoint = geom.MultiPoint(list(zip(lon, lat)))

    # print(dir(self.sta_convex_hull))
    # for i, lonlat in enumerate(list(self.sta_convex_hull)):
        # lonlat_proj = self.proj.transform_points(ccrs.PlateCarree(), lonlat[0], lontlat[1])
        # self.sta_convex_hull[i] = lonlat_proj
    # print(self.sta_convex_hull)

    return sta_multipoint.convex_hull
