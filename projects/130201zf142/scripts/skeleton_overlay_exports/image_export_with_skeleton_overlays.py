"""This script takes an (x, y, z) coordinate and returns an image from catmaid
centered on that coordinate. This script also has the ability to
"""

import argparse
import catmaid
import requests
import numpy
import math
import json
import csv
import scipy.misc
import os
from PIL import Image
from StringIO import StringIO
import catmaid.algorithms.images as IM
from networkx.algorithms import shortest_path
from networkx import dag_longest_path
from scipy.spatial.distance import euclidean

# Color codes for MLF neurons
infile = 'ColorCodes_SUBSETnucMLFMauth.txt'
# Output directories
outdir = '../../results/skeleton_overlays/'
im_only_dir = '../../results/skeleton_overlays_imagesonly/'

# The skeleton IDs being used are for catmaid 3 SWiFT
skels_list = [396958, # Mauthner_L
              368156, # Mauthner_R
              385830, # MeLc_L
              364227, # MeLc_R
              358957, # MeLr_L
              384240, # MeLr_R
              384917, # MeLm_L
              358039, # MeLm_R
              347635, # MeMv_L
              382490, # MeMv_R
              367463, # MeMd_L
              374687] # MeMd_R
              ##349354, # RoM1R_L mlfVi
              #362943, # RoM1R_R mlfVi
              #366024, # RoM1C_L mlfVi
              #351711, # RoM1C_R mlfVi
              #355612, # RoM2L_L mlfDi
              #357287, # RoM2L_R mlfDi
              #380344, # RoM2M_L mlfDi
              #380210, # RoM2M_R mlfDi
              #359624, # RoM3L_L mlfDi
              #371125, # RoM3L_R mlfDi
              #372386, # RoM3M_L_1 mlfDi
              #357204, # RoM3M_L_2 mlfDi
              #396902, # RoM3M_R_1 mlfDi
              #368370, # RoM3M_R_2 mlfDi
              #353480, # RoV3_L_1 mlfVi
              #385251, # RoV3_L_2 mlfVi
              #386283, # RoV3_L_3 mlfVi
              #348431, # RoV3_L_4 mlfVi
              #351650, # RoV3_R_1 mlfVi
              #377256, # RoV3_R_2 mlfVi
              #355433, # RoV3_R_3 mlfVi
              #396927, # RoV3_R_4 mlfVi
              #388361, # MiR1_L mlfVi
              #384107, # MiR1_R mlfVi
              #370457, # MiM1_L_1 mlfDi
              #377848, # MiM1_L_2 mlfDi
              #381250, # MiM1_R_1 mlfDi
              #379945, # MiM1_R_2 mlfDi
              #358516, # MiV1_L_1 mlfVi
              #359074, # MiV1_L_2 mlfVi
              #364622, # MiV1_L_3 mlfVi
              #367021, # MiV1_L_4 mlfVi
              #368080, # MiV1_L_5 mlfVi
              #386727, # MiV1_L_6 mlfVi
              #354084, # MiV1_L_7 mlfVi
              #396872, # MiV1_R_1 mlfVi
              #367848, # MiV1_R_2 mlfVi
              #363119, # MiV1_R_3 mlfVi
              #372586, # MiV1_R_4 mlfVi
              #380373, # MiV1_R_5 mlfVi
              #379417, # MiV1_R_6 mlfVi
              #355568, # MiR2_L mlfVi
              #376343, # MiR2_R mlfVi
              #359641, # MiD2cm_L mlfDc
              #357769, # MiD2cm_R mlfDc
              #378554, # MiD2i_L mlfDi
              #369640, # MiD2i_R mlfDi
              #352707, # MiV2_L_1 mlfVi
              #386180, # MiV2_L_2 mlfVi
              #382065, # MiV2_L_3 mlfVi
              #356339, # MiV2_L_4 mlfVi
              #377304, # MiV2_L_5 mlfVi
              #374547, # MiV2_R_1 mlfVi
              #347581, # MiV2_R_2 mlfVi
              #369833, # MiV2_R_3 mlfVi
              #365006, # MiV2_R_4 mlfVi
              #355718, # MiD3cm_L mlfDc
              #374856, # MiD3cm_R mlfDc
              #368509, # MiD3i_L mlfDi
              #370759] # MiD3i_R mlfDi
              #364927, # CaV_L_1 mlfVi
              #369354, # CaV_R_1 mlfVi
              #347725, # RoL1_L_01 llfi
              #348843, # RoL1_L_02 llfi
              #369068, # RoL1_L_03 llfi
              #374512, # RoL1_L_04 llfi
              #353524, # RoL1_L_05 llfi; putative RoL1 but ends near RoL3
              #370640, # RoL1_R_01 llfi
              #383656, # RoL1_R_02 llfi
              #356121, # RoL1_R_03 llfi
              #350571, # RoL1_R_04 llfi
              #373518, # RoL1_R_05 llfi
              #376648, # RoL1_R_06 llfi
              #397019, # RoL2_L_1 llfc
              #367712, # RoL2_L_2 llfc
              #365036, # RoL2_L_3 llfc; soma more ventral and projection more caudal
              #375277, # RoL2_R_1 llfc
              #357739, # RoL2_R_2 llfc
              #364406, # RoL2_R_3 llfc; soma more ventral and projection more caudal
              #384048, # RoL3_L llfi
              #347222, # RoL3_R llfi
              #364026, # MiD2cl_L llfc
              #364799, # MiD2cl_R llfc; axon path unexpected
              #366559, # CaD_L llfc
              #352434, # CaD_R llfc

# Resolution Transform
resXYZ = numpy.array([18.8, 18.8, 60.])
# Range of z's to pull images from
zstoget = numpy.arange(4765., 10000., 5.)  # range of z-planes (physical) to get
# Catmaid to Physical text file and dictionary

# Open catmaid connection and get souce
c = catmaid.connect()
s = catmaid.get_source(c)


def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

# Open color codes text file
with open(infile, 'r') as f:
    r = csv.reader(f, delimiter=' ', quotechar='"')
    colord = {int(row[0]): hex_to_rgb(row[1]) for row in r}


def soma_through_projection_to_leaf(source, skeleton_id=None, neuron=None):
    if not skeleton_id and not neuron:
        raise Exception("Must provide skeleton_id or neuron")
    if skeleton_id and not neuron:
        neuron = source.get_neuron(skeleton_id)
    try:
        soma = neuron.tags['soma']
    except KeyError:
        print ("Skipping skeleton %s. No soma found" % neuron.skeleton_id)
        return None
    if any([('axon' in tag) for tag in neuron.tags]):
        projection = neuron.tags['axon']
        projection_graph = neuron.axons[projection[0]]['tree']
    else:
        try:
            projection = neuron.tags['projection']
            projection_graph = neuron.projection[projection[0]]['tree']
        except:
            return None
    longest_path = dag_longest_path(projection_graph)
    soma_to_projection = shortest_path(neuron.graph, soma[0], projection[0])
    soma_to_projection.remove(projection[0])
    projection_path = soma_to_projection + longest_path
    return projection_path


def setup_skel_paths(source, skels_list):
    """
    Creates dictionaries in the format of 'Skel_ID: x,y,z coordinates'.
    Takes a source(catmaid) along with two lists of skeleton ids.
    Outputs a dictonary for the input skeletons.
    """
    paths = {}
    for skel_ID in skels_list:
        coordinate_dict = {}
        neu = source.get_neuron(skel_ID)
        projection_path = soma_through_projection_to_leaf(source, skel_ID)
        if projection_path is None:
            print ("Skipping {} because it does not have a "
                   "projection tag".format(skel_ID))
        else:
            for item in projection_path:
                xyz = numpy.array([neu.nodes[item]['x'],
                                   neu.nodes[item]['y'],
                                   neu.nodes[item]['z']]) / resXYZ
                coordinate_dict[item] = xyz
            paths[skel_ID] = coordinate_dict
    return paths


def setup_dicts(zstoget, paths, source):
    """
    Takes the dictionary created by the setup_skel_paths function and outputs
    a dictionary for the skels. The format of these dictionaries is
    'z_index: points, colors'.
    """
    Zdict = {}
    for z in zstoget:
        pts, cols = [], []
        for sid in paths.keys():
            nodes = paths[sid]
            for node in nodes:
                if nodes[node][2] == z:
                    zpts = numpy.array([int(sid), nodes[node][0], nodes[node][1]])
                    pts.append(zpts)
                    cols.append(colord[sid])
        if len(pts) > 1:
            Zdict[z] = {'pts': pts, 'cols': cols}
    return Zdict


def full_setup(source, skels_list):
    """
    A simple function that runs the dictionary setup to be used in
    pulling images from catmaid.
    """
    print "Setting up Skeleton Paths"
    paths = setup_skel_paths(source, skels_list)
    print "Creating dictionary of Skeleton nodes"
    Zdict = setup_dicts(zstoget, paths, source)
    return Zdict


def gen_imgs(connection, Zdict, image_copy=False):
    for z in Zdict:
        print "Outputting images for z: {}".format(int(z))
        zfn = str(int(z))
        file_name = '{}.png'.format(str(int(zfn)).zfill(5))
        pts = Zdict[z]['pts']
        cols = Zdict[z]['cols']
        X = [i[1] for i in pts]
        Y = [i[2] for i in pts]
        Xavg = (sum(X) / len(X))
        Yavg = (sum(Y) / len(Y))
        image, no_overlay = IM.img_from_catmaid(connection, int(Xavg),
                                                int(Yavg), int(z),
                                                imgshape=(4096, 3072),
                                                points=pts, colors=cols,
                                                stack_id=6, tiletype=4,
                                                add_points=True,
                                                image_copy=image_copy)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        scipy.misc.imsave((outdir + file_name), image)
        if no_overlay is not None:
            if not os.path.exists(im_only_dir):
                os.makedirs(im_only_dir)
            copy_name = '{}_no_overlay.png'.format(str(int(zfn)).zfill(5))
            scipy.misc.imsave((im_only_dir + copy_name), no_overlay)


def directory(path):
    if not os.path.isdir(path):
        err_msg = "path is not a directory (%s)"
        raise argparse.ArgumentTypeError(err_msg)
    return path


parser = argparse.ArgumentParser()
parser.add_argument(
   '-i', '--image_copy', action='store_true', required=False,
   help="A flag to have additional images output without overlay.[optional]")
opts = parser.parse_args()

image_copy = opts.image_copy


if __name__ == "__main__":
    Zdic = full_setup(s, skels_list)
    print skels_list
    print "Image copy is: {}".format(image_copy)
    print "Total number of skeletons in list: {}".format(len(skels_list))
    gen_imgs(c, Zdic, image_copy=image_copy)
