#!/usr/bin/env python
"""
Convert a neuron to a intermediate format to then be fed into blender
The reason for the intermediate format is so that blender
doesn't have to do anything like:
    - trace out skeleton trees
    - find root/soma/synapses/etc...

NOTE these notes are out of date, and should be checked against the source
The intermediate format is a 'tree' made up of

{
    'neuron_id': nid, // neuron id
    'skeleton_id': sid, // skeleton id
    'tags': [], // only rendering relavant tags TODO
    'curves': {
        // name sets material & options
        'axon': [[(x,y,z)...],[(x,y,z)...]]  // can be multiple polys
        'dendrite': ...
        'apical': ...
    },
    'soma': (x, y, z),  // name sets options and material
    'root': (x, y, z),
    'synapses: [
        connector_id: (x, y, z)  // location on THIS neuron
        // need to compute if synapse is within volume or outside 'scope'
        // connectors list has pre/post
    },
}

materials and options are set by a different file (json)
(attributes can be computed: pre.speed -> uses presynaptic speed tuning)

options = {
    'world': {
        'scale': 1E-5,
        'center': (0., 0., 0.),
        ...
    }
    'axon': {
        'material': {},
        'options': {},
    }
    'dendrite': ...
    'soma': ...
    'synapse.pre.within': ...
    'synapse.pre.outside': ...
    'synapse.post...'
    skeleton_id: ... // skeleton_id specific settings
}

materials = {
    'default': {
        'diffuse_color': (1., 0., 0.),
        ...
    },
    'axon': ...
    'dendrite': ...
    ...
}


connectors are input from a different file (json)

connectors = {
    cid: {  // connector_id
        'pre': [],  // pre-synaptic skeleton ids
        'post': [],   // post-synaptic skeleton ids
        'location': (x, y, z)  // location of connector
        'type': "within/outside"  // computed at load time using skeleton ids
    }
}

neurons can have arbitrary attributes defined in a csv file
(maybe pass in header names as a command line option)

what neurons to render are set by command line options
"""

import logging
import os
import cPickle as pickle

from .. import algorithms
from . import curve
from . import ops
from .. import source


def neuron_to_tree(neuron, *args, **kwargs):
    tree = {}
    tree['skeleton_id'] = neuron.skeleton_id
    tree['neuron_id'] = neuron.name
    try:
        valid_soma = neuron.soma
        valid_soma = True
    except ValueError as e:  # should probably make this a custom exception
        valid_soma = False
        logging.error("Neuron %s has invalid soma: %s", neuron, e)
    if valid_soma and (neuron.soma is not None):
        tree['soma'] = ops.node_to_location(neuron.nodes[neuron.soma])
    tree['root'] = ops.node_to_location(neuron.nodes[neuron.root])
    tree['annotations'] = [i[0] for i in neuron.annotations]

    # synapses
    syns = []
    # TODO fix this for new synapse info
    si = neuron.synapse_info
    for cid in si:
        # if len(si[cid]) > 1:
        #    raise Exception("Tree conversion only supports 1 to 1 synapses")
        for n in si[cid]:
            labels = n['connector']['labels']
            syns.append((cid, ) + (ops.node_to_location(n['vertex']), labels))
    tree['synapses'] = syns

    # curves
    tree['curves'] = curve.trace_neuron(neuron, *args, **kwargs)

    # TODO tags
    return tree


def save_tree(tree, fn):
    with open(fn, 'w') as f:
        pickle.dump(tree, f)


def convert_source(src, path=None, sids=None, fn_format=None,
                   report_fails=False):
    if fn_format is None:
        fn_format = '{}.p'

    # resolve path
    if path is None:
        if isinstance(src, source.FileSource):
            path = os.path.join(src._skel_source, 'trees')
        else:
            path = 'trees'
    path = os.path.realpath(os.path.expanduser(path))
    if not os.path.exists(path):
        os.mkdir(path)

    # disable caching
    old_cache = src._cache
    src._cache = None

    if sids is None:
        sids = src.skeleton_ids()

    fails = []
    conns = {}
    for sid in sids:
        n = None
        t = None
        try:
            n = src.get_neuron(sid)
            # add to conns
            conns = algorithms.population.network.add_neuron_to_conns(n, conns)
            # convert to tree
            t = neuron_to_tree(n)
            # save tree
            fn = os.path.join(path, fn_format.format(sid))
            logging.debug("Saving tree {} to {}".format(sid, fn))
            save_tree(t, fn)
        except Exception as e:
            logging.warning("Failed to convert {} to tree: {}".format(sid, e))
            fails.append(sid)
        del n
        del t

    # save conns
    fn = os.path.join(path, 'conns.p')
    logging.debug("Saving conns to: {}".format(fn))
    with open(fn, 'w') as f:
        pickle.dump(conns, f)

    # reenable caching
    logging.debug("Reenabling cache")
    src._cache = old_cache
    if report_fails:
        return path, fn, fails
    return path, fn
