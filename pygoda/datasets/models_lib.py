# coding: utf-8

import numpy as np
import scipy as sp
import h5py
import strictyaml as yaml

# import matplotlib.pyplot as plt

ONE_YEAR = 1/(365.2425 * 86400) # t is in sec
TWO_PI_YEAR = 2 * np.pi * ONE_YEAR

def load_models_desc():
    with open('datasets/models_lib.yaml', mode='r', encoding='utf8') as f:
        models_desc = yaml.load(f.read()).data

    return models_desc

class GenericModel():

    # Model definition
    # Must be implemented in children
    name = 'GENERIC'
    short_desc = 'Generic model'
    description = 'Generic model to sub-class for creating actual models'
    # Note: params_list does not necessarily contains *all* the parameters,
    # only those that we want to display or re-use in the GUI.
    params_list = []
    metaparams_list = []

    def __init__(self, dataset):

        self.dataset = dataset
        self.stalist = dataset.getStationsList()
        self.data = None

        self.metaparams_list += ['RMS', 'WRMS']

        self.model_infos = load_models_desc()['MODELS'][self.name]

    def getData(self):
        # Input
        self.data = self.dataset
        self.t = {sta: self.data[sta].t for sta in self.stalist}
        self.y = {sta: self.data[sta].data for sta in self.stalist}
        self.sig = {sta: self.data[sta].data.std for sta in self.stalist}
        self.N = {sta: len(self.y[sta]) for sta in self.stalist}

        # Output
        self.fitted_params = {sta: dict() for sta in self.stalist}
        self.fitted_metaparams = {sta: dict() for sta in self.stalist}
        self.fitted_models = {sta: None for sta in self.stalist}

        self.rms = {sta: np.NaN for sta in self.stalist}
        self.wrms = {sta: np.NaN for sta in self.stalist}

    def RMS(self, sta):
        return self.rms[sta]

    def WRMS(self, sta):
        return self.wrms[sta]

    def setupModel(self, staname):
        # Must be implemented in children

        ## Least squares inversion

        # Problem:
        #   y   =   M   .   x   + errors
        # (Nx1) = (NxP) . (Px1) + errors
        # N data points, P parameters

        # Solution (Maximum a posteriori, see Tarantola...):
        # x = Cx . (M^t . CD^-1 . y + Ca^-1 . xa)
        # Model covariance Cx = (M^t . CD^-1 . M + Ca^-1)^-1
        # Data covariance CD
        # A priori model xa
        # A priori model covariance Ca

        # For now, no prior and data covariance assumed diagonal, thus:
        # x = (M^t . CD^-1 . M)^-1 . (M^t . CD^-1 . y)
        #   = M^-1 . CD . M^t^-1 . M^t . CD^-1 . y
        #   = M^-1 . y
        # and
        # Cx = (M^t . diag(CD)^-1 . M)

        # M = ...

        # return M

        return None

    def computeMetaParams(self, sta):
        # Must be implemented in children
        pass

    def computeRMS(self, sta):
        misfit = self.y[sta] - self.fitted_models[sta]
        if np.any(self.sig[sta] == 0.0):
            self.wrms[sta] = np.NaN
        else:
            sum_inv_sig = np.sum(1/self.sig[sta])
            weights = 1./(self.sig[sta] * sum_inv_sig)
            self.wrms[sta] = np.sqrt(np.sum(weights*misfit**2)/self.N[sta])
        self.rms[sta] = np.sqrt(np.sum(misfit**2)/self.N[sta])
        # if np.isnan(self.fitted_models[sta]).any() or np.isinf(self.fitted_models[sta]).any():
        #     print('ERROR')
        # if np.isnan(self.y[sta]).any() or np.isinf(self.y[sta]).any():
        #     print('ERROOOOOR')
        self.fitted_metaparams[sta]['RMS'] = self.rms[sta]
        self.fitted_metaparams[sta]['WRMS'] = self.wrms[sta]

    def fitModel(self):

        print('Fitting model %s...' % self.name)

        for sta in self.stalist:

            M = self.setupModel(sta)

            # Inversion
            try:
                x, residuals, rank, singval = np.linalg.lstsq(M, self.y[sta], rcond=self.rcond)

                nparams = len(self.params_list)
                for name, value in zip(self.params_list, x[:nparams]):
                    self.fitted_params[sta][name] = value

                self.fitted_models[sta] = np.dot(M, x)
                # plt.figure()
                # plt.plot(self.t[sta], self.fitted_models[sta])
                # plt.show()
                # break
                # return

                # Cx = np.linalg.inv(np.dot(np.dot(M.T, np.linalg.inv(cov)), M))
                # std = np.sqrt(np.diag(Cx))
                # corr = Cx/np.outer(std, std)

                # for i, p in enumerate(['trend', 'A', 'B', 'C', 'D'] + ['sc%d' % i for i in range(Ntrend)] + ['offset%d' % i for i in range(Noff)]):
                #     print(p, '= {:.4f} +/- {:.4f}'.format(x[i], std[i]))

                # jumps_corr = np.dot(M[:, ioff:], x[ioff:])
                # jumps_corr -= jumps_corr[0]
                # data_corrected = data - jumps_corr
            except np.linalg.LinAlgError:
                print('SVD did not converge in Linear Least Squares for station', sta)
                nparams = len(self.params_list)
                for name in self.params_list:
                    self.fitted_params[sta][name] = np.NaN
                self.fitted_models[sta] = self.y[sta] + np.NaN

            self.computeRMS(sta)
            self.computeMetaParams(sta)

        print('done')

    def getParam(self, sta, param):
        return self.fitted_params[sta][param]

    def getMetaParam(self, sta, param):
        return self.fitted_metaparams[sta][param]

    def getModel(self, sta):
        return self.fitted_model[sta]

    def getInfo(self, infos=''):
        if infos:
            if '/' not in infos:
                return self.model_infos[infos]
            infos = infos.split('/')
            info_result = self.model_infos[infos[0]]
            for info in infos[1:]:
                info_result = info_result[info]
            return info_result
        else:
            return self.model_infos


class LinearTrend(GenericModel):

    # Model definition
    name = 'LINEAR'
    short_desc = 'Linear trend'
    description = 'Linear trend'
    # Note: params_list does not necessarily contains *all* the parameters,
    # only those that we want to display or re-use in the GUI.
    # y(t) = at + b
    params_list = ['a', 'b']
    metaparams_list = ['trend', 'y-intercept']

    def __init__(self, dataset):
        GenericModel.__init__(self, dataset)

        self.rcond = None

    def setupModel(self, sta):

        if not self.data:
            self.getData()

        t = self.t[sta]
        N = self.N[sta]

        # Inversion preparation

        # M
        # a + b = 2 parameters
        M = np.empty((N, 2))
        M[:, 0] = t # at
        M[:, 1] = 0*t + 1. # b

        return M

    def computeMetaParams(self, sta):
        self.fitted_metaparams[sta]['trend'] = self.fitted_params[sta]['a']
        self.fitted_metaparams[sta]['y-intercept'] = self.fitted_params[sta]['b']


class SeasonalLinearTrend(GenericModel):

    # Model definition
    name = 'SEASONAL_LINEAR'
    short_desc = 'Seasonal + linear trend'
    description = 'Seasonal (annual, semi-annual) + linear trend'
    # Note: params_list does not necessarily contains *all* the parameters,
    # only those that we want to display or re-use in the GUI.
    # y(t) = at + b + Asin(t) + Bcos(t) + Csin(2t) + Dcos(2t) + ...
    params_list = ['a', 'b', 'A', 'B', 'C', 'D']
    metaparams_list = ['trend',
                       'y-intercept',
                       'annual-amp',
                       'semi-annual-amp']

    def __init__(self, dataset):
        GenericModel.__init__(self, dataset)

        self.rcond = None

    def setupModel(self, sta):

        if not self.data:
            self.getData()

        t = self.t[sta]
        N = self.N[sta]

        # Inversion preparation
        sint, cost = np.sin(TWO_PI_YEAR*t), np.cos(TWO_PI_YEAR*t)
        sintt, costt = np.sin(2*TWO_PI_YEAR*t), np.cos(2*TWO_PI_YEAR*t)

        # M
        # a + b + A + B + C + D = 6 parameters
        M = np.empty((N, 6))
        M[:, 0] = t # at
        M[:, 1] = 0*t + 1. # b
        M[:, 2] = sint # Asin(t)
        M[:, 3] = cost # Bcos(t)
        M[:, 4] = sintt # Csin(2t)
        M[:, 5] = costt # Dcos(2t)

        return M

    def computeMetaParams(self, sta):
        self.fitted_metaparams[sta]['trend'] = self.fitted_params[sta]['a']
        self.fitted_metaparams[sta]['y-intercept'] = self.fitted_params[sta]['b']
        A, B = self.fitted_params[sta]['A'], self.fitted_params[sta]['B']
        C, D = self.fitted_params[sta]['C'], self.fitted_params[sta]['D']
        self.fitted_metaparams[sta]['annual-amp'] = np.sqrt(A**2 + B**2)
        self.fitted_metaparams[sta]['semi-annual-amp'] = np.sqrt(C**2 + D**2)


class SeasonalFourier(GenericModel):

    # Model definition
    name = 'SEASONAL_FOURIER'
    short_desc = 'Seasonal + low-freq. Fourier coeff.'
    description = 'Seasonal (annual, semi-annual) + smoothly evolving trend'
    # Note: params_list does not necessarily contains *all* the parameters,
    # only those that we want to display or re-use in the GUI.
    # y(t) = at + b + Asin(t) + Bcos(t) + Csin(2t) + Dcos(2t) + ...
    params_list = ['a', 'b', 'A', 'B', 'C', 'D']
    metaparams_list = ['trend',
                       'y-intercept',
                       'annual-amp',
                       'semi-annual-amp']

    def __init__(self, dataset):
        GenericModel.__init__(self, dataset)

        self.rcond = None

    def setupModel(self, sta):

        if not self.data:
            self.getData()

        t = self.t[sta]
        N = self.N[sta]
        # one_day = np.min(np.diff(t))

        # t0 = t[0]
        # cov = sig**2 * np.eye()
        # offdates = jumps
        # Noff = len(offdates) + 1 # add an initial offset

        # Inversion preparation
        sint, cost = np.sin(TWO_PI_YEAR*t), np.cos(TWO_PI_YEAR*t)
        sintt, costt = np.sin(2*TWO_PI_YEAR*t), np.cos(2*TWO_PI_YEAR*t)

        # offsets_matrix = np.zeros((Noff, N))
        # ioffsets = [np.argmin(np.abs(t-offdate)) for offdate in offdates]
        # ioffsets.insert(0, 0) # initial offset
        # for i in range(Noff):
        #     # Each row is a shifted Heaviside function
        #     offsets_matrix[i, ioffsets[i]:] = 1.

        ## Time evolving trend: low frequency Fourier decomposition

        Tmax = 2 * (t[-1] - t[0])*ONE_YEAR # Longest period in yr
        Tmin = 3. # Shortest period in yr

        f = np.r_[1/Tmax:1/Tmin:1/Tmax]
        T = 1/f
        Ntrend = 2*len(T)

        sin_trend = np.empty((N, Ntrend//2))
        cos_trend = np.empty((N, Ntrend//2))
        for i, T in enumerate(T):
            sin_trend[:, i] = np.sin(TWO_PI_YEAR/T * t)
            cos_trend[:, i] = np.cos(TWO_PI_YEAR/T * t)

        evolving_trend = np.empty((N, Ntrend))
        evolving_trend[:, 0::2] = np.asarray(sin_trend)
        evolving_trend[:, 1::2] = np.asarray(cos_trend)

        M = np.empty((N, 6 + Ntrend))
        M[:, 0] = t # at
        M[:, 1] = 0*t + 1. # b
        M[:, 2] = sint # Asin(t)
        M[:, 3] = cost # Bcos(t)
        M[:, 4] = sintt # Csin(2t)
        M[:, 5] = costt # Dcos(2t)
        M[:, 6:Ntrend+6] = evolving_trend # Fourrier coefficients

        return M

    def computeMetaParams(self, sta):
        self.fitted_metaparams[sta]['trend'] = self.fitted_params[sta]['a']
        self.fitted_metaparams[sta]['y-intercept'] = self.fitted_params[sta]['b']
        A, B = self.fitted_params[sta]['A'], self.fitted_params[sta]['B']
        C, D = self.fitted_params[sta]['C'], self.fitted_params[sta]['D']
        self.fitted_metaparams[sta]['annual-amp'] = np.sqrt(A**2 + B**2)
        self.fitted_metaparams[sta]['semi-annual-amp'] = np.sqrt(C**2 + D**2)
