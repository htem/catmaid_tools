#!/usr/bin/env python
"""
Get an attribute for a list of skeleton ids (or all skeletons)

Example Usage:
    # get center of mass for all skeletons and output to stdout
    get_attribute -a center_of_mass

    # or output to a file (supports json and pickle output)
    get_attribute -a center_of_mass -o com.txt

    # or get for only certain skeleton ids
    get_attribute -a center_of_mass 12345 123456 1234567
"""

import argparse
import logging
import os

import catmaid

# turn on some extra debugging output
logging.basicConfig(level=logging.DEBUG)

# options
# - source (directory for file source?)
# - file with list of neuron ids to fetch
parser = argparse.ArgumentParser()
parser.add_argument(
    '-s', '--source', default=None,
    help="Source from which to fetch neurons, can be left blank")
parser.add_argument(
    '-i', '--idfile', default=None,
    help="File with list of skeleton ids (one per line) to process")
parser.add_argument(
    '-c', '--column', default=0,
    help="Column of input file that contains skeleton ids")
parser.add_argument(
    '-o', '--outputfile', default=None,
    help="Output file in which to save results")
parser.add_argument(
    '-a', '--attribute', default='center_of_mass',
    help="Neuron attribute to compute")
parser.add_argument(
    'sids', type=int, nargs='*',
    help="Skeleton ids to fetch (ignored if idfile is not None)")
opts = parser.parse_args()

# get the neuron source
# if opts.source is a directory, a local file source will be created that
# loads skeletons from json files rather than fetching them from a server
# if opts.source is None, than a server source will be created
source = catmaid.get_source(opts.source)

# find what ids to fetch
sids = opts.sids
if opts.idfile is not None:
    sids = []  # overwrite any ids provided on the command line
    ext = os.path.splitext(opts.idfile)[1].lower()
    if ext in ('.p', '.pickle', '.pkl'):
        # assume these are pickled iterators
        import cPickle as pickle
        with open(opts.idfile, 'r') as f:
            sids = pickle.load(f)
    elif ext in ('.json', '.js'):
        import json
        with open(opts.idfile, 'r') as f:
            sids = json.load(f)
    elif ext in ('.mat'):
        import scipy.io
        d = scipy.io.loadmat(opts.idfile)
        # try to use filename as key
        key = os.path.splitext(os.path.basename(opts.idfile))[0]
        if key not in d.keys():
            # look for a key that doesn't start with '_'
            for k in d.keys():
                if k[0] != '_':
                    key = k[0]
                    continue
        sids = d[key][:, opts.column].astype(int)
    else:  # assume it's a text file with 1 id per line
        with open(opts.idfile, 'r') as f:
            for l in f:
                if len(l.strip()) != 0:
                    sids.append(int(l))

# if no skeleton ids were provided, then fetch them all
if len(sids) == 0:
    sids = source.skeleton_ids()

# fetch an attribute for all neurons
results = []
for sid in sids:
    logging.debug("Getting %s for %s", opts.attribute, sid)
    n = source.get_neuron(sid)
    try:
        na = getattr(n, opts.attribute)
    except Exception as e:
        logging.error(
            "Failed to fetch attribut %s for %s with %s",
            opts.attribute, sid, e)
        na = None
    results.append([sid, na])

# output results
if opts.outputfile is None or opts.outputfile == '-':
    # print to stdout
    for sid, na in results:
        print "%s, %s" % (sid, na)
else:
    # save to file
    fn = opts.outputfile
    ext = os.path.splitext(fn)[1].lower()
    if ext in ('.p', '.pickle', '.pkl'):
        # pickle the data
        import cPickle as pickle
        with open(fn, 'w') as f:
            pickle.dump(results, f)
    elif ext in ('.json', '.js'):
        # treat this like a json file
        import json
        with open(fn, 'w') as f:
            json.dump(results, f)
    else:
        # just write it like a text file
        with open(fn, 'w') as f:
            for sid, na in results:
                f.write('%s, %s\n' % (sid, na))
