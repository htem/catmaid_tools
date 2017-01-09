#!/usr/bin/env python

import os

import catmaid


conn = catmaid.connect()

sids = sorted(conn.skeleton_ids())

wd = conn.wiring_diagram()
wsids = []
for n in wd['data']['nodes']:
    wsids.append(n['id'])
wsids.sort()

fn = "../../results/lists/all_sids.txt"
if not os.path.exists(os.path.dirname(fn)):
    os.makedirs(os.path.dirname(fn))
with open(fn, 'w') as f:
    for i in sids:
        f.write('{}\n'.format(i))

fn = "../../results/lists/wired_sids.txt"
if not os.path.exists(os.path.dirname(fn)):
    os.makedirs(os.path.dirname(fn))
with open(fn, 'w') as f:
    for i in wsids:
        f.write('{}\n'.format(i))
