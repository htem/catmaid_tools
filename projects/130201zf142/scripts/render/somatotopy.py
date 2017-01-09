#!/usr/bin/env python
'''
Generates csv of skeletons with rgb color  correspondance to
    represent the position of neuromasts
'''

import catmaid
import numpy
from catmaid.algorithms.morphology import node_position
from colorsys import rgb_to_hls, hls_to_rgb

s = catmaid.get_source('../../data/skeletons/')
csvoutfile = '../../results/lists/somatotopy.csv'
hexoutfile = '../../results/lists/LLAfferent_Hex.txt'


def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb


# TODO pad to avoid white/black for extrema
def getColorfromcube(pt, vtxmin, dim):
    return 255.*(pt - vtxmin)/dim


def getColorfromcubez(pt, vtxmin, dim, hue=(70, 215, 77),
                      Lowoffset=(0., 0., 0.), Highoffset=(0., 0., 0.)):
    Lowoffset = numpy.array(Lowoffset)
    Highoffset = numpy.array(Highoffset)
    newmin = vtxmin - Lowoffset
    newdim = dim + Highoffset + Lowoffset
    newpt = pt + Lowoffset
    fracdisp = (newpt - newmin)/newdim

    hsvc = rgb_to_hls(hue[0]/255., hue[1]/255., hue[2]/255.)
    return numpy.array(hls_to_rgb(hsvc[0], (1. - fracdisp[2]), hsvc[2])) * 255.

sid2hex = {}
posdictR, posdictL = {}, {}
missing_conns, multi_conns = [], []
outs = []
for n in s.all_neurons_iter():
    if ('LLafferent' in n.name.split('_')):
        if n.connectors:
            if any([('right' in anno) for anno in n.annotations]):
                posdictR[n.skeleton_id] = node_position(n.connectors[n.connectors.keys()[0]])
            elif any([('left' in anno) for anno in n.annotations]):
                posdictL[n.skeleton_id] = node_position(n.connectors[n.connectors.keys()[0]])
            if not (len(n.connectors.keys()) == 1):
                multi_conns.append(n.skeleton_id)
        else:
            missing_conns.append(n.skeleton_id)

maxvtxL = numpy.max(numpy.array(posdictL.values()), axis=0)
minvtxL = numpy.min(numpy.array(posdictL.values()), axis=0)
spcL = maxvtxL - minvtxL

maxvtxR = numpy.max(numpy.array(posdictR.values()), axis=0)
minvtxR = numpy.min(numpy.array(posdictR.values()), axis=0)
spcR = maxvtxR - minvtxR

Hoff = 0.8 * spcR
Loff = 0.4 * spcR

for sid in posdictR.keys():
    pos = posdictR[sid]
    R, G, B = getColorfromcubez(pos, minvtxR, spcR, hue=(231, 41, 138),
                                Lowoffset=Loff, Highoffset=Hoff)
    outs.append('{}, {}, {}, {}, {}\n'.format(sid, 0.0, R, G, B))
    sid2hex[sid] = rgb_to_hex((R, G, B))

for sid in posdictL.keys():
    pos = posdictL[sid]
    R, G, B = getColorfromcubez(pos, minvtxL, spcL, hue=(231, 41, 138),
                                Lowoffset=Loff, Highoffset=Hoff)
    outs.append('{}, {}, {}, {}, {}\n'.format(sid, 0.0, R, G, B))
    sid2hex[sid] = rgb_to_hex((R, G, B))

with open(csvoutfile, 'w') as f:
    for ln in outs:
        f.write(ln)
with open(hexoutfile, 'w') as f:
    for sd, hx in sid2hex.items():
        f.write('{} {}\n'.format(sd, hx))
