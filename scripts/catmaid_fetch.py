#!/usr/bin/env python

import argparse
import logging
import os

import catmaid

# enable some logging output
logging.basicConfig(level=logging.ERROR)

# parse the command line options
parser = argparse.ArgumentParser()
parser.add_argument(
    '-i', '--idfile', default=None,
    help="File with list of skeleton ids (one per line) to process")
parser.add_argument(
    '-c', '--column', default=0,
    help="Column of input file that contains skeleton ids")
parser.add_argument(
    '-o', '--outputdir', default='skeletons',
    help="Output directory in which to save results")
parser.add_argument(
    'sids', type=int, nargs='*',
    help="Skeleton ids to fetch (ignored if idfile is not None)")
parser.add_argument(
    '-w', '--wipe', action='store_true',
    help="Delete all locally existing skeletons from output directory"
         " prior to fetching updated skeletons")
parser.add_argument(
    '-a', '--attempts', default=1,
    help="Max number of attempts to fetch skeletons in case error encountered")
parser.add_argument(
    '-n', '--ignore_none_skeletons', action='store_true',
    help="Option to ignore fetching invalid skeletons with type None, "
         "such as those which have been deleted or merged "
         "since starting fetch.")
opts = parser.parse_args()

# create a skeleton source (which connects to catmaid)
# the server, user and project to use can be set by
# - environment variables (see README)
# - interactive command prompts
# - creating and passing in a connection (see catmaid.connect)
source = catmaid.get_source(ignore_none_skeletons=opts.ignore_none_skeletons)

# source is now a ServerSource that can fetch skeletons from catmaid

# check if only a subset of ids should be saved
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
    sids = None

# get the output directory
# make the output directory if it does not exist
if not os.path.exists(opts.outputdir):
    os.makedirs(opts.outputdir)

# now fetch all the skeletons (may take a while)
tries = max(1, int(opts.attempts))
for t in range(tries):
    if opts.wipe:
        source.wipe_skeletons(opts.outputdir)
    if t+1 < tries:
        try:
            source.save_skels(opts.outputdir, skels=sids)
            break
        except catmaid.source.SkeletonReadException as se:
            logging.warning('Encountered {} in attempt {}/{}'.format(se,
                                                                     (t + 1),
                                                                     tries))
            continue
    else:
        source.save_skels(opts.outputdir, skels=sids)


# all done!
# now that the skeletons are stored locally, try creating a FileSource
# by running something like:
#  source = catmaid.get_source('skeletons')
