# coding: utf-8

import numpy as np
import scipy as sp
import h5py

import config as cfg

def exportAttributes(filepath, stalist, attrs=[], sep=' '):

    ## Export a list of stations with some attributes

    header = "# {:d} stations from project {:s}".format(len(stalist), cfg.project_name)

    if attrs:
        header += "\n# NAME"

    for attr in attrs:
        header += sep + attr.upper()

    if attrs:
        header += '\n'

    # if sep != ' ':
    #     sep += ' '

    print('Exporting station list...')

    with open(filepath, 'w') as out:
        out.write(header)

        for sta in stalist:
            out_line = "{:s}".format(sta)
            for attr in attrs:
                out_line += sep + "{:{s}.3f}".format(getattr(cfg.data[sta], attr), s=' 8' if sep == ' ' else '')
            out.write(out_line + '\n')

    print('done')


def exportHDF5GlobalMass(hd5filepath, stalist, attrs=[], fields=[]):

    ## Create HDF5 file with everything included
    compression = 'gzip' # 'lzf'

    if not attrs:
        attrs = ['lon', 'lat', 'h']

    if not fields:
        fields = ['t', 'Z', 'stdZ', 'jumps']

    print('Exporting to HDF5 file...')

    with h5py.File(hd5filename, 'w') as hdf5file:
        for staname in stalist:
            station = cfg.dataset.getData(staname)
            stagrp = hdf5file.create_group(staname)

            for attr in attrs:
                stagrp.attrs[attr] = station[attr].to_numpy()[0]

            for field in fields:
                data = station[field]
                stagrp.create_dataset(field, data.shape, data=data.to_numpy(),
                                      dtype='f', compression=compression)

            print(staname)

    print('done')

