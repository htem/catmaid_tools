#!/usr/bin/env python

import catmaid

# get the pre-fetched skeletons
src = catmaid.get_source('../../data/skeletons')

PNsORNs = []
for sid in src.skeleton_ids():
    neu = src.get_neuron(sid)
    if any([
            (('DM6 ORN' in anno) or ('PN' in anno))
            for anno in neu.annotations]):
        PNsORNs.append(neu.skeleton_id)

fn = '../../results/lists/PNs_ORNs.txt'
with open(fn, 'w') as fil:
    for i in PNsORNs:
        fil.write('{}\n'.format(i))
