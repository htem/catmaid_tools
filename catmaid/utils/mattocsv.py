#!/usr/bin/env python

import warnings

has_numpy_and_scipy_io = False
try:
    import numpy
    import scipy.io
    has_numpy_and_scipy_io = True
except ImportError as E:
    warnings.warn("Failed to import numpy and scipy.io : %s" % E)


def mat_to_csv(matfn, csvfn, columns=None, label=None, sep=',', dtype=None):
    """Convert a .mat file to a .csv

    Parameters
    ----------
    matfn : input filename (read with scipy.io.loadmat)
    csvfn : output filename
    columns : list of column indices to convert, default all if None
    label : name of table in .mat file, will be guessed if None
    sep : field separator, ',' by default
    dtype : if provided, convert table to dtype before exporting
    """
    if not has_numpy_and_scipy_io:
        warnings.warn(
            "mat_to_csv returns None, need to import numpy and scipy.io")
        return None
    m = scipy.io.loadmat(matfn)
    if label is None:
        label = [k for k in m if k[0] != '_'][0]
    if label not in m:
        raise KeyError("label {} not in .mat file {} [{}]".format(
            label, matfn, m.keys()))
    t = m[label]
    if columns is None:
        columns = list(range(t.shape[1]))
    for c in columns:
        if c < 0 or c >= t.shape[1]:
            raise ValueError("Invalid column index {} not in [0, {}]".format(
                c, t.shape[1] - 1))
    t = t[:, columns]
    if isinstance(dtype, (tuple, list)):
        if len(dtype) != len(columns):
            raise ValueError("Invalid dtype len({}) != {}".format(
                dtype, len(columns)))
        if len(dtype) == 1:
            t = t.astype(dtype[0])
        else:
            dtype = ','.join(dtype)
            t = numpy.core.records.fromarrays(t.T, dtype=dtype)
    elif dtype:
        t = t.astype(dtype)
    fmt = sep.join(['{}'] * len(columns)) + '\n'
    if csvfn is None:
        def write(s):
            print(s[:-1])
        close = lambda: None
    else:
        outf = open(csvfn, 'w')
        write = outf.write
        close = outf.close
    for r in t:
        write(fmt.format(*r))
    close()
