#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kalman filter based smoothing for neuron objects.  Running as a script will
smooth all neurons in  a file source

special requirements:
pykalman

"""

# TODO:
#     Test for convergence for iterations

import argparse
import pykalman
import numpy
import networkx
import catmaid
from catmaid.algorithms.morphology import node_array, node_position, unique_neurites, gaussian_smooth_neuron
from catmaid.algorithms.skeleton_json_new_to_old import convert_new_to_old
import json
import os
import sys
import logging
import multiprocessing as mp


outdir = '../../data/skeletons_smooth'


def smoothKalman(arr, initstate=None, its=4):
    '''
    Generates and implements a kalman smoother for a 3D array.
        The state estimator iterations are set with the its variable.
    '''
    if initstate is None:
        initstate = arr[0]
        emvars = 'all'
    else:
        emvars = ['transition_matrices', 'observation_matrices',
                  'transition_offsets', 'observation_offsets',
                  'transition_covariance', 'observation_covariance',
                  'initial_state_covariance']

    kf = pykalman.KalmanFilter(initial_state_mean=initstate,
                               n_dim_obs=3,
                               n_dim_state=3)
    kf = kf.em(arr, n_iter=its, em_vars=emvars)

    (smoothed_means, smoothed_covars) = kf.smooth(arr)
    return smoothed_means, smoothed_covars


def mask_missing(arr, zres=60.):
    '''
    This function takes a numpy array of 3-space coordinates and
        outputs an array with masked values for kalman filtering
    '''
    zdiff = numpy.diff(arr[:, 2])/zres
    arggaps = sorted([i[0] for i in numpy.argwhere(zdiff > 1)])
    added = 1
    for arggap in arggaps:
        missing_measurements = int(zdiff[arggap])
        meas = numpy.empty([missing_measurements, 3]) * numpy.NaN
        arr = numpy.insert(arr, arggap + int(added), meas, 0)
        added += missing_measurements
    marr = numpy.ma.masked_invalid(arr)
    return marr


def array_pathlength(arr):
    return sum([numpy.linalg.norm(arr[obsidx] - obs)
                for obsidx, obs in enumerate(arr[1:])])


def smooth_tracing(trace, zres=None, firstpos=None, use_missing=True,
                   fix_applicate=False, QC='noQC'):
    '''
    This function takes an arbitrary list of 3d points and inserts
        masked states (missing measurements) until all states are sequential.
        Returns numpy array without mask of modified xy values.
    Args:
        trace = a list of node points
        zres = the resolution of the z axis
        firstpos = the first node designated as the start position
        use_missing = a flag to have missing data (over z axis) interpolated
                      and added to smoothing results
        fix_applicate = a flag used to have the z axis fixed during smoothing
        QC = a quality control metric ['noQC', 'strictLT']
    '''
    zs = trace[:, 2].copy()
    arr = mask_missing(trace) if use_missing else trace
    states = smoothKalman(arr, initstate=firstpos)[0]
    states = states[~arr.mask[:, 0]] if use_missing else states
    if fix_applicate:
        states[:, 2] = zs
    if QC == 'strictLT':
        if (array_pathlength(states) >= array_pathlength(trace)):
            logging.debug('found neurite with {} nodes which '
                          'was smoothed unsuccessfully.'.format(len(trace)))
            return trace
        else:
            return states
    else:
        return states


# TODO this does not need to generate a skeleton so explicitly....
def updateNodePosition(neu, posdict):
    nodelist, connectors = [], []
    for nid in neu.nodes.keys():
        try:
            p = neu.dedges[nid]
            assert len(p) == 1
            p = p[0]
        except:
            p = None
        r = neu.nodes[nid]['radius']
        c = neu.nodes[nid]['confidence']
        ct, et = None, None  # We don't use Edition/creation times
        if nid in posdict.keys():
            x, y, z = posdict[nid].flatten()
        else:
            x = neu.nodes[nid]['x']
            y = neu.nodes[nid]['y']
            z = neu.nodes[nid]['z']
        nodelist.append([nid, p, None, x, y, z, r, c, ct, et])
    connectors = []
    for stid in neu.skeleton['connectivity'].keys():
        for cid in neu.skeleton['connectivity'][stid].keys():
            t = neu.skeleton['connectivity'][stid][cid]['type']
            if not (t == 'neurite'):
                post = (t == 'postsynaptic_to')
                x = neu.skeleton['vertices'][cid]['x']
                y = neu.skeleton['vertices'][cid]['y']
                z = neu.skeleton['vertices'][cid]['z']
                ct = None
                connectors.append([stid, cid, post, x, y, z, ct])

    sk = [neu.name, nodelist, neu.tags, connectors, None,
          neu.skeleton_id, neu.skeleton['neuron']['id'], neu.annotations]
    skel = convert_new_to_old(sk)
    return catmaid.neuron.Neuron(skel)


def newbifurcs(neu, neurites, maxpts=8, minpts=3):
    bifpos = {}
    bifneurites = {neurite[0]: [] for neurite in neurites}
    bifneurites.update({neurite[-1]: [] for neurite in neurites})
    for neurite in neurites:
        if neurite[-1] in bifneurites.keys():
            bifneurites[neurite[-1]].append(neurite[::-1])
        elif neurite[0] in bifneurites.keys():
            bifneurites[neurite[0]].append(neurite)
    for bif in bifneurites.keys():
        bifpos[bif] = node_position(neu.nodes[bif])
        startpts, endpts = [], []
        for nrt in bifneurites[bif]:
            if len(nrt) > minpts:
                nopts = min((maxpts-1), len(nrt))
                lnst, lnend = defline(node_array(neu, nrt[:nopts]))
                startpts.append(lnst)
                endpts.append(lnend)
        # fewer trivial solutions
        if len(startpts) > 2:
            startpts = numpy.vstack(startpts)
            endpts = numpy.vstack(endpts)
            bifpos[bif][:2] = lineintersect3D(startpts, endpts)[:2]
    return bifpos


def defline(points):
    _, _, vv = numpy.linalg.svd(points - points.mean(axis=0))
    # TODO check this -- have had issues with order in the past
    return vv[0] * numpy.mgrid[-1:1:2j][:, numpy.newaxis] + points.mean(axis=0)


def lineintersect3D(PA, PB):
    '''
    numpy port of the MATLAB function by Anders Eikenes
        to find the closest intersection of N nonintersecting lines
    http://www.mathworks.com/matlabcentral/fileexchange/37192-intersection-point-of-lines-in-3d-space/content/lineIntersect3D.m

    more info:
    https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection
    Weisstein, Eric W. "Point-Line Distance--3-Dimensional."
        From MathWorld--A Wolfram Web Resource.
        http://mathworld.wolfram.com/Point-LineDistance3-Dimensional.html

    inputs:
        PA -- start points of N lines (Nx3)
        PB -- end points of N lines (Nx3)
    '''
    Si = PB - PA
    ni = Si/numpy.sqrt(numpy.sum(Si**2, axis=1))[:, None]
    # TODO fix linalg handling
    xx = ni[:, 0] ** 2 - 1
    yy = ni[:, 1] ** 2 - 1
    zz = ni[:, 2] ** 2 - 1
    xy = ni[:, 0] * ni[:, 1]
    xz = ni[:, 0] * ni[:, 2]
    yz = ni[:, 1] * ni[:, 2]
    Sxx = numpy.sum(xx)
    Syy = numpy.sum(yy)
    Szz = numpy.sum(zz)
    Sxy = numpy.sum(xy)
    Sxz = numpy.sum(xz)
    Syz = numpy.sum(yz)
    S = numpy.array([[Sxx, Sxy, Sxz], [Sxy, Syy, Syz], [Sxz, Syz, Szz]])

    Cx = numpy.sum(PA[:, 0] * xx + PA[:, 1] * xy + PA[:, 2] * xz)
    Cy = numpy.sum(PA[:, 0] * xy + PA[:, 1] * yy + PA[:, 2] * yz)
    Cz = numpy.sum(PA[:, 0] * xz + PA[:, 1] * yz + PA[:, 2] * zz)
    C = numpy.array([Cx, Cy, Cz])

    return numpy.linalg.solve(S, C)


def smoothnout_wrapper(args):
    ns, neuron, fn = args
    ns.smoothtoFile(neuron, fn)


def smoothn_gaussian(args):
    ns, neuron, fn = args
    ns.smooth_gaussian(neuron, fn)


def smoothn_everything(args):
    ns, neuron, main_dir = args
    print "smoothign {}".format(neuron)
    sid = neuron.skeleton_id
    # Smooth Kalman unmasked, applicate Fixing
    ns.use_missing = False
    ns.fix_applicate = True
    fn = '{}/skeletons_smooth_kalman_unmasked_fixed/{}.json'.format(
        main_dir, sid)
    # need to set params here
    ns.smoothtoFile(neuron, fn)
    # Smooth Kalman unmasked, not fixed
    ns.fix_applicate = False
    fn = '{}/skeletons_smooth_kalman_unmasked_not_fixed/{}.json'.format(
        main_dir, sid)
    ns.smoothtoFile(neuron, fn)
    ns.use_missing = True
    ns.fix_applicate = True
    # Smooth Kalman masked, applicate Fixing
    fn = '{}/skeletons_smooth_kalman_masked_fixed/{}.json'.format(
        main_dir, sid)
    ns.smoothtoFile(neuron, fn)
    # Smooth Kalman masked, not fixed
    ns.fix_applicate = False
    fn = '{}/skeletons_smooth_kalman_masked_not_fixed/{}.json'.format(
        main_dir, sid)
    ns.smoothtoFile(neuron, fn)
    # Smooth with Gaussian
    ns.fix_applicate = True
    fn = '{}/skeletons_smooth_gaussian_fixed/{}.json'.format(main_dir, sid)
    ns.smooth_gaussian(neuron, fn)
    # Smooth with gaussian not fixed
    ns.fix_applicate = False
    fn = '{}/skeletons_smooth_gaussian_not_fixed/{}.json'.format(main_dir, sid)
    ns.smooth_gaussian(neuron, fn)
    print "Successfully smoothed and saved {}".format(sid)


def directory(path):
    if not os.path.isdir(os.path.abspath(path)):
        err_msg = "path is not a directory (%s)"
        raise argparse.ArgumentTypeError(err_msg)
    return os.path.abspath(path)


class NeuronSmoother:
    # TODO replace "z" res with arbitrary dim
    '''NeuronSmoother to handle kalman smoothing parameters'''
    def __init__(self, zres, its=4, bifurc_interp_consider=(3, 8),
                 use_missing=True, fix_applicate=False, QC='strictLT'):
        self.iterations = its
        self.zres = zres
        self.minbifurc = min(bifurc_interp_consider)
        self.maxbifurc = max(bifurc_interp_consider)

        self.fix_applicate = fix_applicate  # TODO implement for other axes
        self.use_missing = use_missing
        # Gaussian values
        self.gaussian_sigma = 300.
        self.gaussian_min_effect = 1e-6

        if QC is None:
            QC = 'noQC'
        if QC not in ['noQC', 'strictLT']:
            logging.warning('{} is unknown QC mode.  Using "noQC"'.format(QC))
            self.QC = 'noQC'
        else:
            self.QC = QC

    def smooth(self, neuron):
        '''
        This function smooths all node positions in a catmaid_tools
         neuron object and returns a new skeleton object
        '''
        # neurites = segmentNeurites(neuron)  FIXME
        neurites = unique_neurites(neuron)
        smoothneurites = []
        smoothednodes = {}
        bifurcs = newbifurcs(neuron, neurites,
                             minpts=self.minbifurc,
                             maxpts=self.maxbifurc)
        for neurite in neurites:
            neuritepts = node_array(neuron, neurite)
            neuritepts[0] = bifurcs[neurite[0]]
            neuritepts[-1] = bifurcs[neurite[-1]]
            smoothneurites.append(smooth_tracing(
                neuritepts, zres=self.zres, firstpos=None,
                use_missing=self.use_missing, fix_applicate=self.fix_applicate,
                QC=self.QC))
            smoothpos = smoothneurites[-1]
            smoothednodes.update({nid: smoothpos[i]
                                  for i, nid in enumerate(neurite)})
        return updateNodePosition(neuron, smoothednodes)

    def smooth_gaussian(self, neuron, filename):
        '''
        This funciton smooths all node positions in a catmaid_tools
        neuron object with a gaussian filter. Returns a new skeleton object
        '''
        new_skel = gaussian_smooth_neuron(neuron, sigma=self.gaussian_sigma,
                                          min_effect=self.gaussian_min_effect,
                                          fix_axes=self.fix_applicate)
        new_neuron = catmaid.neuron.Neuron(new_skel)
        with open(filename, 'w') as f:
            json.dump(new_neuron.skeleton, f)

    def smoothtoFile(self, neuron, filename):
        sneu = self.smooth(neuron)
        with open(filename, 'w') as f:
            json.dump(sneu.skeleton, f)


if __name__ == "__main__":
    '''If run as a script, smooths a catmaid source'''
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s', '--source', type=directory, required=False,
        help="A path to a directory containing jsons of the skeletons"
             " to be used.[optional]")
    parser.add_argument(
        '-d', '--dest', type=directory, required=False,
        help="A path to the desired output directory.[optional]")
    parser.add_argument(
        '-t', '--threads', type=int, required=False,
        help="The number of threads to use for smoothing")
    opts = parser.parse_args()
    if opts.source:
        indir = opts.source
    else:
        indir = None
    if opts.dest:
        outdir = opts.dest
    else:
        print "Outdir not passed through. Reverting to default"
        outdir = outdir
    print "Connecting to source"
    s = catmaid.get_source(indir)
    if outdir[-1] != '/':
        outdir += '/'
    if opts.threads:
        cpu_count = mp.cpu_count()
        if opts.threads > cpu_count:
            cpu_count = int(cpu_count / 2)
        else:
            cpu_count = opts.threads
    else:
        cpu_count = int(mp.cpu_count() / 2)
    if cpu_count < 0:
        cpu_count = 1
    print "Creating pool operator with {} CPUS".format(cpu_count)
    pool = mp.Pool(processes=cpu_count)
    print "Creating Smoothing Object"
    zf_ns = NeuronSmoother(60.)
    print "Starting Smoothing Operation"
    pool.map(smoothn_everything,
             [(zf_ns, n, outdir) for n in s.all_neurons_iter()])
