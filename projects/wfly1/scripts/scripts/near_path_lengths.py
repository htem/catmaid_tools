#!/usr/bin/env python

import os
import pickle
import sys

import joblib
import numpy
import scipy.io

import catmaid


# distance threshold
distance = 500.
resample_distance = 40.
pairs_fn = '../../data/npl_pairs.csv'

if len(sys.argv) > 1:
    distance = float(sys.argv[1])


def npl(a, d, s):
    na = s.get_neuron(a)
    #if len(na.axons) != 1:
    #    return float('nan')
    nd = s.get_neuron(d)
    try:
        #return catmaid.algorithms.population.distance.near_path_length(
        #    nd, na, g1=nd.dendrites, g2=na.axons.values()[0]['tree'],
        #    distance=distance, resample_distance=resample_distance)
        return catmaid.algorithms.population.distance.near_path_length(
            nd, na, g1=nd.dendrites, g2=na.dendrites,
            distance=distance, resample_distance=resample_distance)
    except Exception as e:
        return e


n_jobs = -1
output_file = '../../results/scripts/dendrite_near_path_lengths_%i_%i.csv' % (
    int(distance), int(resample_distance))

s = catmaid.get_source('../../data/skeletons')
s._cache = None
pairs = []
if os.path.exists(pairs_fn):
    print("Loading pairs from csv: %s" % pairs_fn)
    with open(pairs_fn, 'r') as f:
        for l in f:
            if l.strip() != '':
                pairs.append(map(int, l.strip().split(',')))
else:
    raise Exception
    sids = []
    with open('skels2pull.csv', 'r') as f:
        for l in f:
            if l.strip() != '':
                sids.append(l.strip())
    print("Finding pairs from source")
    ns = {int(sid): s.get_neuron(sid) for sid in sids}

    axons = []
    dendrites = []
    for n in ns.values():
        sid = n.skeleton_id
        if len(n.axons) == 1:
            axons.append(sid)
            #axons[sid] = n.axons.values()[0]['tree']
        elif len(n.axons) == 0:
            print("Skeleton {} has 0 axons".format(sid))
        elif len(n.axons) > 0:
            print("Skeleton {} has {} axons".format(sid, len(n.axons)))
        dendrites.append(sid)
        #dendrites[sid] = n.dendrites

    del ns

    pairs = []
    for a in axons:
        for d in dendrites:
            if a != d:
                pairs.append((a, d))

    with open(pairs_fn, 'w') as f:
        for p in pairs:
            f.write('{},{}\n'.format(p[0], p[1]))



rs = joblib.parallel.Parallel(n_jobs=n_jobs, verbose=50)(
    joblib.parallel.delayed(npl)(
        a, d, s) for (a, d) in pairs)

fails = []
if output_file is not None:
    with open(output_file, 'w') as f:
    	f.write("#distance=%s\n" % distance)
    	f.write("#resample_distance=%s\n" % resample_distance)
        for p, r in zip(pairs, rs):
            if isinstance(r, Exception):
                fails.append((p[0], p[1], r))
            else:
                f.write('{},{},{}\n'.format(p[0], p[1], r))

print "Failures:"
for f in fails:
    print f
ffn = '../../results/scripts/failures_%s_%s.p' % (distance, resample_distance)
with open(ffn, 'w') as f:
    pickle.dump(fails, f)
