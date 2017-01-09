#!/usr/bin/env python


def add_neuron_to_conns(n, conns=None):
    if conns is None:
        conns = {}
    si = n.synapse_info
    for synid in si:
        for conn in si[synid]:
            cid = conn['connector_id']
            if cid not in conns:
                conns[cid] = {
                    'pre': [], 'post': [],
                    'location': (
                        float(conn['connector']['x']),
                        float(conn['connector']['y']),
                        float(conn['connector']['z']),
                    ),
                }
            # postsynaptic_to: neuron is postsynaptic_to the connector
            #   so, add the neuron to post
            if conn['type'] == 'postsynaptic_to':
                conns[cid]['post'].append(n.skeleton_id)
            elif conn['type'] == 'presynaptic_to':
                conns[cid]['pre'].append(n.skeleton_id)
            else:
                raise ValueError(
                    "Unknown connector type {} for {} in {}".format(
                        conns[cid]['type'], cid, n.skeleton_id))
    return conns


def find_conns(neuron_iter):
    # used by rendering script
    conns = {}
    for n in neuron_iter:
        conns = add_neuron_to_conns(n, conns)
    return conns


def find_synapses(*neurons):
    syns = {}
    for (i, n) in enumerate(neurons):
        for c in n.synapse_info:
            if c in syns:  # already found this one
                continue
            nc = n.synapse_info[c]
            syns[c] = {
                'connector': nc['connector'].copy(),
                'connector_id': nc['connector_id'],
                'skeletons': {
                    n.skeleton_id: {
                        'type': nc['type'],
                        'vertex': nc['vertex'].copy(),
                        'vertex_id': nc['vertex_id'],
                    }
                }
            }
            for n2 in neurons[i+1:]:
                if c in n2.synapse_info:
                    # n2 is connected to c (and therefore n)
                    n2c = n2.synapse_info[c]
                    syns[c]['skeletons'][n2.skeleton_id] = {
                        'type': n2c['type'],
                        'vertex': n2c['vertex'].copy(),
                        'vertex_id': n2c['vertex_id'],
                    }
    return syns
