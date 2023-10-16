# coding: utf-8

import copy
import functools
import os

# import cartopy.geodesic as geod
# from geod import geometry_length
import numpy as np
from shapely.geometry import Point, MultiPoint
import strictyaml as yaml

import constants as cst
import config as cfg
from . import fit_data
from . import timeseries

def spherical_distance(p1, p2):
    lam_1, phi_1 = np.radians(p1)
    lam_2, phi_2 = np.radians(p2)
    h = (np.sin(.5*(phi_2 - phi_1))**2
            + np.cos(phi_1) * np.cos(phi_2) * np.sin(.5*(lam_2 - lam_1))**2)
    return 2 * 6371 * np.arcsin(np.sqrt(h))

def load_features_desc():
    with open('datasets/timeseries_features.yaml', mode='r', encoding='utf8') as f:
        features_desc = yaml.load(f.read()).data

    return features_desc

def largestOffsetCustom(data, sig):
    Z, stdZ = data, sig
    offsets = np.min([np.abs(np.diff(Z[:-1:2])),\
                      np.abs(np.diff(Z[1::2]))],\
                     axis=0)
    return np.max(offsets)

def nanlen(v):
    if np.any(np.isnan(v)):
        v = np.asarray(v)
        return len(v[~np.isnan(v)])
    else:
        return len(v)

def timeSpan(t, data):
    t_nonan = t[~np.isnan(data)]
    if len(t_nonan) == 0:
        return 0.0
    elif len(t_nonan) == 1:
        it = np.where(~np.isnan(data))[0]
        return np.diff(t[it:min(it+1, len(t))])
    else:
        return t_nonan[-1] - t_nonan[0]

def largestGap(t, data):
    t = t[~np.isnan(data)]
    if len(t) < 2:
        return np.nan
    else:
        return np.max(np.diff(t))

def minSkipNan(t, data):
    t = t[~np.isnan(data)]
    if not len(t):
        return np.nan
    else:
        return np.min(t)

def maxSkipNan(t, data):
    t = t[~np.isnan(data)]
    if not len(t):
        return np.nan
    else:
        return np.max(t)

def nanmin(v):
    return np.nanmin(v) if v else np.nan

def nanmax(v):
    return np.nanmax(v) if v else np.nan


class TimeSeriesFeatures():

    FEATURE_CAST = {
        'str': lambda x, y: x,
        'string': lambda x, y: x,
        'int': lambda x, y: f'{x:d}',
        'integer': lambda x, y: f'{x:d}',
        'float': lambda x, y: f'{x:.5G}',
        'amplitude': lambda x, y: timeseries.Scalar(x, **y),
        'angle': lambda x, y: timeseries.Angle(x),
        'date': lambda x, y: timeseries.Date(x),
        'duration': lambda x, y: timeseries.Duration(x),
        'timespan': lambda x, y: timeseries.Duration(x),
    }

    def __init__(self, dataset, models):

        self.data = dataset
        self.stalist = dataset.getStationsList().copy()
        #self.stalist.sort()

        self.models = models

        features_desc = load_features_desc()
        self.features_infos = features_desc['FEATURES']
        self.features_infos['MODELS'] = fit_data.timeseries_models_names

        # Dict of functions to compute each feature
        self.features = dict()

        self.features['.DEFAULT'] = self.stalist
        self.features['.NAMES'] = sorted(self.stalist)
        self.features['SPACE.LON'] = lambda ts: ts.lon
        self.features['SPACE.LAT'] = lambda ts: ts.lat
        self.features['SPACE.COLAT'] = lambda ts: 90.0 - ts.lat
        self.features['SPACE.HEIGHT'] = lambda ts: ts.h
        self.features['SPACE.D0'] = lambda ts: spherical_distance((ts.lon, ts.lat), cfg.reference_point)
        self.features['TIME.SPAN'] = lambda ts: timeSpan(ts.t, ts.data)
        self.features['TIME.MIN'] = lambda ts: minSkipNan(ts.t, ts.data)
        self.features['TIME.MAX'] = lambda ts: maxSkipNan(ts.t, ts.data)
        self.features['TIME.DENSITY'] = lambda ts: nanlen(ts.data)/(ts.t[-1] - ts.t[0])
        self.features['TIME.GAPS'] = lambda ts: np.nansum(np.diff(ts.t[~np.isnan(ts.data)]))/len(ts.t)
        self.features['TIME.LARGEST_GAP'] = lambda ts: largestGap(ts.t, ts.data)
        self.features['DATA.N'] = lambda ts: len(ts.data[~np.isnan(ts.data)])
        self.features['DATA.MIN'] = lambda ts: np.nanmin(ts.data)
        self.features['DATA.MAX'] = lambda ts: np.nanmax(ts.data)
        self.features['DATA.MINMAX'] = lambda ts: np.nanmax(ts.data) - np.nanmin(ts.data)
        self.features['DATA.MEDIAN'] = lambda ts: np.nanmedian(ts.data)
        self.features['DATA.VAR_MEDIAN'] = lambda ts: np.nansum(np.abs(ts.data - np.nanmedian(ts.data)))/len(ts.t)
        self.features['DATA.OFFSET_MIN'] = lambda ts: np.nanmin(np.abs(np.diff(ts.data)))
        self.features['DATA.OFFSET_MAX'] = lambda ts: np.nanmax(np.abs(np.diff(ts.data)))
        self.features['DATA.OFFSET_MAX_SMART'] = lambda ts: largestOffsetCustom(ts.data, ts.std_data)
        self.features['SIGMA.SIGMA_MED'] = lambda ts: np.nanmedian(ts.std_data)
        self.features['SIGMA.SIGMA_MIN'] = lambda ts: np.nanmin(ts.std_data)
        self.features['SIGMA.SIGMA_MAX'] = lambda ts: np.nanmax(ts.std_data)
        self.features['EVENTS.N'] = lambda ts: ts.n_events

        for name, model in self.models.items():
            feat_id = 'MODELS.' + name
            #self.features[feat_id + '.' + 'RMS'] = model.RMS
            #self.features[feat_id + '.' + 'WRMS'] = model.WRMS
            for param in model.getInfo('metaparams'):
                #TODO: include params too, not just metaparams
                self.features[feat_id + '.' + param] = functools.partial(model.getMetaParam, param=param)

        # self.features['USER']

        # Features values for each station
        self.sta_features = {feat_id: dict() for feat_id in self.features.keys()}

        # self.computeFeatures(compute_models=False)

    def computeFeatures(self, names=None, compute_models=True):

        if names:
            if not isinstance(names, list):
                names = [names]
            features = {name: self.features[name] for name in names}
        else:
            features = self.features

        for feat_id, features in features.items():
            if feat_id[0] == '.':
                continue # Names are already stored
            elif 'MODELS.' in feat_id:
                # Dealing with a model
                if not compute_models:
                    continue
                _, model, param = feat_id.split('.')
                # Fit the model first
                # print(model, param)
                if not cfg.models[model].data or \
                   not cfg.models[model].fitted_metaparams[self.stalist[0]]:
                    cfg.models[model].fitModel()
                # Then get the params
                for sta in self.stalist:
                    self.sta_features[feat_id][sta] = self.features[feat_id](sta)
            else:
                #TODO: improve that
                for sta in self.stalist:
                    self.sta_features[feat_id][sta] = self.features[feat_id](self.data[sta])

    def sortByFeature(self, feature_id, order_asc,
                      return_list=True, store_result=True):

        if feature_id == '.DEFAULT':
            sorted_feat = {sta: sta for sta in self.stalist} # actually not sorted
        elif feature_id == '.NAMES':
            sorted_feat = {sta: sta for sta in sorted(self.stalist)}
        else:
            feature = self.sta_features[feature_id]
            if not feature:
                self.computeFeatures(feature_id)
                feature = self.sta_features[feature_id]
            if order_asc:
                sorted_feat = {k: v for k, v in \
                               sorted(feature.items(),
                                      key=lambda x: x[1]
                                          if not np.isnan(x[1]) else np.inf)}
            else:
                sorted_feat = {k: v for k, v in \
                               sorted(feature.items(),
                                      key=lambda x: -x[1]
                                          if not np.isnan(x[1]) else np.inf)}

            # if not order_asc:
            #     sorted_feat = {sta: sorted_feat[sta] \
            #                      for sta in list(sorted_feat.keys())[::-1]}

            # Put stations with no data at the end
            # sorted_feat_raw = sorted_feat.copy()
            # for k, v in sorted_feat_raw.items():
            #     if np.isnan(v) or v == '':
            #         del sorted_feat[k]
            #         sorted_feat.update({k: v})

        if store_result:
            self.sta_features[feature_id] = sorted_feat

        if return_list:
            sorted_feat = list(sorted_feat.keys())
            # Already reversed
            # if not order_asc:
            #     sorted_feat.reverse()

        return sorted_feat

    def getStationsFeature(self, feature_id, staname=None):
        if staname:
            return self.sta_features[feature_id][staname]
        else:
            return self.sta_features[feature_id]

    def formatFeature(self, feature_id, value):
        feature_info = self.getInfo(feature_id)

        # Model parameters
        if 'MODELS' in feature_id:
            group, model, param = feature_id.split('.')
            param_info = feature_info['metaparams'][param]
            value *= float(param_info.get('factor', 1.0))

        try:
            feature_type = feature_info['type']
        except KeyError:
            feature_type = 'float' # model parameter

        unit = self.data[self.stalist[0]].data.unit
        accuracy = self.data[self.stalist[0]].data.accuracy
        meta = {'unit': unit,
                'accuracy': accuracy}

        if feature_type in self.FEATURE_CAST:
            casted_value = self.FEATURE_CAST[feature_type](value, meta)
        else:
            casted_value = value

        return str(casted_value)

    def getDescription(self, feature_id, append_formula=False):
        if feature_id[0] == '.':
            return self.features_infos[feature_id[1:]]['desc']
        feature_id_list = feature_id.split('.')
        if len(feature_id_list) == 2:
            group, name = feature_id_list
            desc = self.features_infos[group][name]['desc']
            if append_formula:
                formula = self.features_infos[group][name].get('formula', '')
                if formula:
                    desc = f'{desc}: {formula}'
            return desc
        elif len(feature_id_list) == 3:
            # Dealing with a model
            group, model, param = feature_id_list
            # group == 'MODELS'
            desc_path = 'metaparams/' + param + '/desc'
            return self.models[model].getInfo(infos=desc_path)

    def getInfo(self, feature_id, model_info=''):
        if feature_id[0] == '.':
            return self.features_infos[feature_id[1:]]
        feature_id_list = feature_id.split('.')
        if len(feature_id_list) == 2:
            group, name = feature_id_list
            return self.features_infos[group][name]
        elif len(feature_id_list) == 3:
            # Dealing with a model
            group, model, param = feature_id_list
            # group == 'MODELS'
            if model_info:
                return self.models[model].getInfo(infos=model_info)
            else:
                return self.models[model].getInfo()

    def iterateFeatures(self, description=False, append_formula=False):
        for feat_id, feature in self.sta_features.items():
            if description:
                desc = self.getDescription(feat_id, append_formula=append_formula)
                yield feat_id, feature, desc
            else:
                yield feat_id, feature
