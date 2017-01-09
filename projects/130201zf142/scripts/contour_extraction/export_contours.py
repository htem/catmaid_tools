"""IMPORTANT! This script requires networkx version 1.10 or greater!"""

import argparse
import catmaid
import numpy
import os
import sys
from time import strftime
import catmaid.algorithms.morphology as morphology


# parse command line options
parser = argparse.ArgumentParser()
parser.add_argument(
   '-b', '--backbone_contour', required=False, action="store_true",
   help="Option flag to specify backbone to backbone contour detection."
        "[Optional]")
parser.add_argument(
   '-p', '--projection', required=False, action="store_true",
   help="Option flag to specify soma to project to leaf contour detection."
        "[Optional]")
parser.add_argument(
   '-pf', '--projection_file', required=False, type=str,
   help="A path to a specific file for projection contour detection exports."
        "[Optional]")
parser.add_argument(
   '-bf', '--backbone_file', required=False, type=str,
   help="A path to a specific file for backbone contour detection exports."
        "[Optional]")

opts = parser.parse_args()

detect_backbone = opts.backbone_contour
detect_projection = opts.projection
projection_outfile = opts.projection_file
backbone_outfile = opts.backbone_file


if not detect_backbone and not detect_projection:
    detect_backbone = True
    detect_projection = True


if detect_backbone:
    print "USING BACKBONE TO BACKBONE CONTOUR DETECTION"
if detect_projection:
    print "USING SOMA TO PROJECTION TO LEAF CONTOUR DETECTION"

if not backbone_outfile:
    backbone_outfile = ('../../results/exports/{}_130201zf142_'
                        'BACKBONE_dump_PHYScoord.txt'.format(
                            strftime('%y%m%dT%H%M')))
if not projection_outfile:
    projection_outfile = ('../../results/exports/{}_130201zf142_'
                          'PROJECTION_dump_PHYScoord.txt'.format(
                            strftime('%y%m%dT%H%M')))


c = catmaid.connect()
src = catmaid.get_source(c)

with open(backbone_outfile, 'w') as bf:
    with open(projection_outfile, 'w') as pf:
        for sid in src.skeleton_ids():
            neuron = src.get_neuron(sid)
            if detect_projection:
                projection = (
                    morphology.soma_through_projection_to_leaf(src,
                                                               neuron=neuron))
                if projection:
                    print "FOUND PROJECTION"
                    for nid in projection:
                        if nid == neuron.root:
                            parent = 'root'
                        else:
                            parent = neuron.dedges[nid][0]
                        xpx, ypx, zpx = numpy.array([neuron.nodes[nid]['x'],
                                                    neuron.nodes[nid]['y'],
                                                    neuron.nodes[nid]['z']])
                        pf.write('{} {} {} {} {} {}\n'.format(sid, nid,
                                                              str(parent), xpx,
                                                              ypx, int(zpx)))
                else:
                    print "No Projection contour"
            if detect_backbone:
                contour = morphology.backbone_to_backbone(src, neuron=neuron)
                if contour:
                    print "FOUND BACKBONE TAGS"
                    for nid in contour:
                        if nid == neuron.root:
                            parent = 'root'
                        else:
                            parent = neuron.dedges[nid][0]
                        xpx, ypx, zpx = numpy.array([neuron.nodes[nid]['x'],
                                                    neuron.nodes[nid]['y'],
                                                    neuron.nodes[nid]['z']])
                        bf.write('{} {} {} {} {} {}\n'.format(sid, nid,
                                                              str(parent), xpx,
                                                              ypx, int(zpx)))
                else:
                    print "No Backbone contour"
