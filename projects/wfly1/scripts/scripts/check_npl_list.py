#!/usr/bin/env python

import catmaid


pairs_fn = '../../data/npl_pairs.csv'
output_fn = '../../results/scripts/check_npl_list.csv'

pairs = []
with open(pairs_fn, 'r') as f:
    for l in f:
        if l.strip() != '':
            pairs.append(map(int, l.strip().split(',')))

s = catmaid.get_source('../../data/skeletons')
s._cache = None

results = []
# check all pairs [a, d]
for p in pairs:
    (a, d) = p
    try:
        na = s.get_neuron(a)
    except Exception as e:
        results.append((a, d, 'failed to load a: %s' % e))
        continue
    try:
        nd = s.get_neuron(d)
    except Exception as e:
        results.append((a, d, 'failed to load d: %s' % e))
        continue
    #if len(na.axons) != 1:
    #    results.append((a, d, 'len(a.axons) != 1[%s]' % len(na.axons)))
    #    continue
    #nan = na.axons.values()[0]['tree'].number_of_nodes()
    nan = na.dendrites.number_of_nodes()
    ndn = nd.dendrites.number_of_nodes()
    # return # of a and # of d nodes
    results.append((a, d, '%i/%i' % (nan, ndn)))

with open(output_fn, 'w') as f:
    for r in results:
        f.write('%i,%i,%s\n' % r)
