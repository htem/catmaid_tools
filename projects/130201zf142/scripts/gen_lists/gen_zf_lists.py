#!/usr/bin/env python

import catmaid

src = catmaid.get_source('../../data/skeletons', cache=False)

allsids, PLLnsids, Dnmsids, Onmsids, nucMLFsids, Mauthsids, Anmsids = ([], [], [],
                                                              [], [], [], [])
for sid in src.skeleton_ids():
    neu = src.get_neuron(sid)
    if not any([('Blacklist' in anno) for anno in neu.annotations]):
        allsids.append(neu.skeleton_id)

        # FIXME probably a better way to handle these
        # generate lists of mutually exclusive cell descriptions
        if any([('PLLn' in anno) for anno in neu.annotations]):
            PLLnsids.append(neu.skeleton_id)
        elif any([('Dorsal Neuromast' in anno) for anno in neu.annotations]):
            Dnmsids.append(neu.skeleton_id)
        elif any([('Anterior Neuromast' in anno) for anno in neu.annotations]):
            Anmsids.append(neu.skeleton_id)
        elif any([('Occipital Neuromast' in anno) for anno in neu.annotations]):
            Onmsids.append(neu.skeleton_id)
        elif any([('nucMLF' in anno) for anno in neu.annotations]):
            nucMLFsids.append(neu.skeleton_id)
        elif any([('Mauthner' in anno) for anno in neu.annotations]):
            Mauthsids.append(neu.skeleton_id)

nmsids = Dnmsids + Onmsids + Anmsids


fn = '../../results/lists/all_sids.txt'
with open(fn, 'w') as fil:
    for i in allsids:
        fil.write('{}\n'.format(i))

fn = '../../results/lists/PLLn_sids.txt'
with open(fn, 'w') as fil:
    for i in PLLnsids:
        fil.write('{}\n'.format(i))

fn = '../../results/lists/Dnm_sids.txt'
with open(fn, 'w') as fil:
    for i in Dnmsids:
        fil.write('{}\n'.format(i))

fn = '../../results/lists/Anm_sids.txt'
with open(fn, 'w') as fil:
    for i in Anmsids:
        fil.write('{}\n'.format(i))

fn = '../../results/lists/Onm_sids.txt'
with open(fn, 'w') as fil:
    for i in Onmsids:
        fil.write('{}\n'.format(i))

fn = '../../results/lists/nucMLF_sids.txt'
with open(fn, 'w') as fil:
    for i in nucMLFsids:
        fil.write('{}\n'.format(i))

fn = '../../results/lists/Mauthner_sids.txt'
with open(fn, 'w') as fil:
    for i in Mauthsids:
        fil.write('{}\n'.format(i))

fn = '../../results/lists/nm_sids.txt'
with open(fn, 'w') as fil:
    for i in nmsids:
        fil.write('{}\n'.format(i))
