#!/usr/bin/env python

import csv
import warnings

has_numpy_and_scipy_io = False
try:
    import numpy
    import scipy.io
    has_numpy_and_scipy_io = True
except ImportError as E:
    warnings.warn("Failed to import numpy and scipy.io : %s" % E)


def load():
    pass


def load_mat(fn, key=None):
    if not has_numpy_and_scipy_io:
        raise Exception("Cannot load_mat without numpy and scipy.io")
    d = scipy.io.loadmat(fn)
    if key is None:
        # if no key was provided, try to find one that doesn't start with '_'
        for k in d.keys():
            if k[0] != '_':
                key = k[0]
                continue
        if key is None:
            return d
    return d[key]


def load_csv(fn, **kwargs):
    vs = []
    with open(fn, 'r') as f:
        r = csv.reader(f, **kwargs)
        for l in r:
            vs.append(l)
    return vs


def save():
    pass
