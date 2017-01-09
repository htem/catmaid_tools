#!/usr/bin/env python

import math
import logging

from . import morphology


def find_myelination(neuron, axid, result):
    if axid not in neuron.axons:
        logging.critical("Invalid axon id %s"
                         " not in %s", axid, neuron.axons.keys())
        raise ValueError(
            "Invalid axon id {} not in {}".format(axid,
                                                  neuron.axons.keys()))
    axon = neuron.axons[axid]
    if 'trunk' not in axon:
        logging.warn("Axon %s missing trunk", axid)
        result = {}  # axon does not have a trunk
    path = morphology.find_path(neuron, axid, axon['trunk'])
    dist = 0.
    myelinated = 0.
    # state = 0  # 0: un-myelinated, 1: myelinated
    state = int(bool('myelinated' in neuron.nodes[path[0]]['labels']))
    pmas = float('nan')
    p = path[0]
    for n in path[1:]:
        d = morphology.distance(neuron, p, n)
        if state == 1:
            myelinated += d
        if 'myelinated' in neuron.nodes[n]['labels']:
            if state == 1:
                logging.warn("myelinated tag at %s "
                             "when already myelinated", n)
            state = 1
            if math.isnan(pmas):
                logging.info("found pmas %s", n)
                pmas = dist
            logging.info("found myelinated %s", n)
        elif 'unmyelinated' in neuron.nodes[n]['labels']:
            if state == 0:
                logging.warn("unmeylinated tag at node %s"
                             "when already unmyelinated", n)
            state = 0
            logging.info("found unmyelinated %s", n)
        dist += d
        p = n
    result[axid] = dict(pmas=pmas, dist=dist, myelinated=myelinated)


def myelination(neuron, axid):
    """
    For each excitatory neuron with an axon:
    1) calculate axonal path length
        (all calculations on axonal trunk only; skip collaterals)
    2) calculate path length between node tagged "axon" to first node
        tagged "myelinated" this would be considered the
        premyelin axonal segment (PMAS)
    3) calculate path length between any pair of
        "myelinated" and "unmyelinated" tags
    4) calculate [myelination coverage]/[axonal path length]
    5) categorize cells as having "unmyelinated",
        "intermittently myelinated", or "long PMAS" axons
    6) test if (5) is related to function.
    """
    result = {}
    if axid is None:
        axids = neuron.axons.keys()
        for axid in axids:
            find_myelination(neuron, axid, result)
    else:
        find_myelination(neuron, axid, result)
    return result
