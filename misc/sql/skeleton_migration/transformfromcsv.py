'''
This script applies node-level translations from a csv to a set of catmaid
    nodes generated with "export_skeletons.py"
    -- currently assumes csv xyz is in pixel values.

    TODO:
        Better input of resolution Data
'''

import numpy
import json
import os
import csv
import copy

inall = './20160503_export_FromDB.json'
outall = './20160503_export_FromDB_transformed.json'
transformcoordfn = './20160503_newnodedump.txt'

with open(inall, 'r') as f:
    proj = json.load(f)

resXYZ = numpy.array([18.85, 18.85, 60.])

sidnidpxvals = {}
with open(transformcoordfn, 'r') as f:
    for ln in csv.reader(f, delimiter=' '):
        sid = (ln[0] if (ln[0] == 'connector') else int(float(ln[0])))

        if sid not in sidnidpxvals.keys():
            sidnidpxvals[sid] = {}
        sidnidpxvals[sid].update({int(float(ln[1])): numpy.array(
                [float(i) for i in ln[3:]])})

transformedproj = copy.copy(proj)

for sid in transformedproj['reconstructions']['skeletons']:
    skel = transformedproj['reconstructions']['skeletons'][sid]
    for nid in skel['trace'].keys():
        # TODO allow disparities in db and transform
        xpx, ypx, zpx = sidnidpxvals[int(sid)][int(nid)]
        xnm, ynm, znm = sidnidpxvals[int(sid)][int(nid)] * resXYZ

        skel['trace'][str(int(nid))].update(
            {'xpix': xpx, 'ypix': ypx, 'zpix': zpx,
             'xnm': xnm, 'ynm': ynm, 'znm': znm})

for cid in proj['reconstructions']['connectors']:
    xpx, ypx, zpx = sidnidpxvals['connector'][int(float(cid))]
    xnm, ynm, znm = sidnidpxvals['connector'][int(float(cid))] * resXYZ

    transformedproj['reconstructions']['connectors'][str(int(cid))].update(
        {'xpix': xpx, 'ypix': ypx, 'zpix': zpx,
         'xnm': xnm, 'ynm': ynm, 'znm': znm})


with open(outall, 'w') as f:
    json.dump(transformedproj, f)
