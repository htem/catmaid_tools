#!/usr/bin/env python

import json
import os
import sys

import catmaid


if len(sys.argv) < 2:
    outfile = '../../results/scripts/sid_by_annotation.json'
else:
    outfile = sys.argv[1]

c = catmaid.connect()

nids = c.neuron_ids()
nid_to_sid = c.nid_to_sid_map()

annotations = {}
for nid in nids:
    try:
        annotation = c.annotation_table(nid)
        annotations[nid] = annotation
    except Exception as e:
        print("Failed to fetch annotations for: %s" % nid)


sid_by_annotation = {}
for nid in annotations:
    for annotation in annotations[nid]:
        a = annotation[0]  # get annotation text
        if a not in sid_by_annotation:
            sid_by_annotation[a] = []
        # convert nid to sids
        for sid in nid_to_sid[nid]:
            sid_by_annotation[a].append(sid)

# write out results
dname = os.path.dirname(outfile)
if dname.strip() != '':
    if not os.path.exists(dname):
        os.makedirs(dname)
with open(outfile, 'w') as f:
    json.dump(sid_by_annotation, f)
