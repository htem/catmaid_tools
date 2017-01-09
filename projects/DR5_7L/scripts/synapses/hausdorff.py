#!/usr/bin/env python

import os

import joblib

import catmaid


def hausdorff(a, d, s):
    na = s.get_neuron(a)
    nd = s.get_neuron(d)
    return catmaid.algorithms.population.distance.hausdorff(
        na, nd, resample_distance=40)


n_jobs = -1
output_file = '../../results/synapses/hausdorff.csv'
function = hausdorff

pairs_fn = '../../results/synapses/functional_pairs.csv'

sids = []
with open('../../results/lists/functional_sids.txt', 'r') as f:
    for l in f:
        if l.strip() != '':
            sids.append(l.strip())

s = catmaid.get_source('../../data/skeletons')
s._cache = None
pairs = []
if os.path.exists(pairs_fn):
    print("Loading pairs from csv")
    with open(pairs_fn, 'r') as f:
        for l in f:
            if l.strip() != '':
                pairs.append(map(int, l.strip().split(',')))
else:
    print("Finding pairs from source")
    ns = {int(sid): s.get_neuron(sid) for sid in sids}

    axons = []
    dendrites = []
    for n in ns.values():
        sid = n.skeleton_id
        if len(n.axons) == 1:
            axons.append(sid)
            # axons[sid] = n.axons.values()[0]['tree']
        elif len(n.axons) == 0:
            print("Skeleton {} has 0 axons".format(sid))
        elif len(n.axons) > 0:
            print("Skeleton {} has {} axons".format(sid, len(n.axons)))
        dendrites.append(sid)
        # dendrites[sid] = n.dendrites

    del ns

    pairs = []
    for a in axons:
        for d in dendrites:
            if a != d:
                pairs.append((a, d))

    if not os.path.exists(os.path.dirname(pairs_fn)):
        os.makedirs(os.path.dirname(pairs_fn))
    with open(pairs_fn, 'w') as f:
        for p in pairs:
            f.write('{},{}\n'.format(p[0], p[1]))


rs = joblib.parallel.Parallel(n_jobs=n_jobs, verbose=2)(
    joblib.parallel.delayed(function)(
        a, d, s) for (a, d) in pairs)

if output_file is not None:
    if not os.path.exists(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))
    with open(output_file, 'w') as f:
        for p, r in zip(pairs, rs):
            f.write('{},{},{}\n'.format(p[0], p[1], r))
