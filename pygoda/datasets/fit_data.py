# coding: utf-8

import inspect

import numpy as np
import scipy as sp
import h5py

import config as cfg

from . import models_lib

# 'LINEAR': 'Linear y(t) = At + B',
# 'QUADRATIC': 'Quadratic y(t) = At² + Bt + C',
# 'PW_LINEAR': 'Piecewise linear',
# 'ANNUAL': 'Annual y(t) = Acos(t) + Bsin(t)',
# 'ANNUAL_TREND': 'Annual + trend',
# 'SEASONAL': 'Seasonal y(t) = Acos(2t) + Bsin(2t)',
# 'SEASONAL_TREND': 'Seasonal + trend'
# 'PERIODIC': 'Periodic y(t) = Acos(ωt) + Bsin(ωt)',
# 'PERIODIC_TREND': 'Periodic + trend',
# 'EXP_INC': 'Exponential growth y(t) = Aexp(t/τ)',
# 'EXP_DEC': 'Exponential decrease y(t) = Aexp(-t/τ)'

timeseries_models = dict()
# timeseries_models['LINEAR'] =
# timeseries_models['QUADRATIC'] =
# timeseries_models['PW_LINEAR'] =
# timeseries_models['ANNUAL'] =
# timeseries_models['ANNUAL_TREND'] =
for name, obj in inspect.getmembers(models_lib):
    if inspect.isclass(obj) and name != 'GenericModel':
        try:
            foo = obj.params_list # check that the class is a model
            timeseries_models[obj.name] = obj
        except AttributeError:
            pass

#timeseries_models[models_lib.LinearTrend.name] = models_lib.LinearTrend
#timeseries_models[models_lib.SeasonalLinearTrend.name] = models_lib.SeasonalLinearTrend
#timeseries_models[models_lib.SeasonalFourier.name] = models_lib.SeasonalFourier
# timeseries_models['PERIODIC'] =
# timeseries_models['PERIODIC_TREND'] =
# timeseries_models['EXP_INC'] =
# timeseries_models['EXP_DEC'] =

timeseries_models_names = dict()
for name, model in timeseries_models.items():
    timeseries_models_names[name] = model.short_desc
