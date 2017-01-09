#!/usr/bin/env python
"""
trace a neuron with b
"""

import logging

logging.basicConfig(level=logging.DEBUG)

from . import ops

default_name_tests = {
    'axon': lambda n: 'axon' in n['labels'],
    'apical': lambda n: 'l5_apical' in n['labels'],
    # default state is dendrite
}


def test_name_transition(node, name, tests):
    for nt in tests:
        if nt == name:
            continue
        elif tests[nt](node):
            return True, nt
    return False, name


def trace_neuron(neuron, start=None, name='dendrite', curves=None,
                 name_tests=None, visited=None, vs=None):
    if curves is None:
        curves = {}
    if name_tests is None:
        name_tests = default_name_tests
    if visited is None:
        visited = []
    redges = neuron.redges
    nodes = neuron.nodes
    if start is None:
        nid = neuron.root
    else:
        nid = start
    if vs is None:
        vs = []
    while nid is not None:

        nc, nn = test_name_transition(nodes[nid], name, name_tests)
        if nc:
            logging.debug("Found name transition at %s: %s->%s", nid, name, nn)
            vs.append(ops.node_to_location(nodes[nid]))
            trace_neuron(
                neuron, nid, name=nn, curves=curves,
                name_tests=name_tests, visited=visited)
            break
        vs.append(ops.node_to_location(nodes[nid]))
        visited.append(nid)
        onid = nid
        nid = None
        if onid in redges:
            for i in redges[onid]:
                if i in visited:
                    continue
                if nid is None:
                    nid = i
                else:
                    logging.debug(
                        "Found branch point %s -> [%s]", onid, redges[onid])
                    trace_neuron(
                        neuron, i, name=name, curves=curves,
                        name_tests=name_tests, visited=visited,
                        vs=[vs[-1], ])
    if len(vs) > 1:
        curves[name] = curves.get(name, []) + [vs, ]
    return curves
