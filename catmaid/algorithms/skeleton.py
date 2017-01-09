#!/usr/bin/env python
'''
'''
import logging

import networkx


def name(sk):
    name = sk['neuron']['neuronname']
    if ' ' in name:
        tokens = name.split()
        if len(tokens) == 2 and tokens[0] == 'neuron':
            return tokens[1]
    return name


def nodes(sk):
    vertices = {}
    for v in sk['vertices']:
        if sk['vertices'][v]['type'] == 'skeleton':
            vertices[v] = sk['vertices'][v]
    return vertices


def soma(sk):
    soma = None
    for v in sk['vertices']:
        for l in sk['vertices'][v]['labels']:
            if l == 'soma':
                if soma is not None:
                    logging.critical(
                        "Found 2 somas [%s, %s] in neuron %s",
                        soma, v, name(sk))

                    raise ValueError(
                        "Found 2 somas [{}, {}] in neuron {}".format(
                            soma, v, name(sk)))
                # soma = sk['vertices'][v]
                soma = v
                break
    return soma


def connectors(sk):
    conns = {}
    for v in sk['vertices']:
        if sk['vertices'][v]['type'] == 'connector':
            conns[v] = sk['vertices'][v]
    return conns


def synapses(sk):
    """Returns all skeleton vertices that have 'synaptic' in their labels"""
    syns = {}
    for v in sk['vertices']:
        if sk['vertices'][v]['type'] == 'skeleton':
            for l in sk['vertices'][v]['labels']:
                if 'synaptic' in l:
                    syns[v] = sk['vertices'][v]
                    break
    return syns


def synapse_info(n):
    """Get information for all synapses
    """
    sinfo = {}
    connectors = n.connectors
    edges = n.skeleton['connectivity']
    verts = n.skeleton['vertices']
    for cid in edges:
        for pid in edges[cid]:
            if pid in connectors:
                # this is an edge from this neuron to a connector
                # this is either a pre or postsynaptic link
                if pid not in sinfo:
                    sinfo[pid] = []
                if cid in [s['vertex_id'] for s in sinfo[pid]]:
                    print(
                        "Duplicate link between vertex %s and conn %s"
                        % (cid, pid))
                    print("Skipping this as it is a tracing error")
                    print("\ttype: %s" % edges[cid][pid]['type'])
                    raise Exception()
                else:
                    sinfo[pid].append({
                        'connector': connectors[pid],
                        'connector_id': pid,
                        'vertex': verts[cid],
                        'vertex_id': cid,
                        #'edge': edges[cid][pid],
                        'type': edges[cid][pid]['type'],
                    })
    return sinfo


def input_synapses(n):
    inputs = []
    syns = n.synapse_info
    for si in syns:
        for syn in syns[si]:
            if syn['type'] == 'postsynaptic_to':
                inputs.append(syn)
        #if syns[si]['type'] == 'presynaptic_to':
        #    inputs[si] = syns[si].copy()
    return inputs


def output_synapses(n):
    outputs = []
    syns = n.synapse_info
    for si in syns:
        for syn in syns[si]:
            if syn['type'] == 'presynaptic_to':
                outputs.append(syn)
        #if syns[si]['type'] == 'postsynaptic_to':
        #    outputs[si] = syns[si].copy()
    return outputs


def dedges(sk):
    # don't include edges to missing vertices
    dedges = {}
    conns = sk['connectivity']
    verts = sk['vertices']
    for cid in conns:
        if cid not in verts:
            continue
        for pid in conns[cid]:
            if pid not in verts:
                continue
            if conns[cid][pid]['type'] != 'neurite':
                continue
            dedges[cid] = dedges.get(cid, []) + [pid, ]
    return dedges


def redges(neuron):
    redges = {}
    dedges = neuron.dedges
    for cid in dedges:
        for pid in dedges[cid]:
            redges[pid] = redges.get(pid, []) + [cid, ]
    return redges


def edges(neuron):
    edges = {}
    for cid in neuron.dedges:
        for pid in neuron.dedges[cid]:
            edges[cid] = edges.get(cid, []) + [pid, ]
            edges[pid] = edges.get(pid, []) + [cid, ]
    return edges


def projections(neuron):
    """ This function parses a neuron for a projection tag (similar to an axon
    tag), and returns an networkx directed graph of the nodes that follow
    the projection tag."""
    projection = {}
    # find backbone nodes
    for nid in neuron.nodes:
        if 'projection' in neuron.nodes[nid]['labels']:
            projection[nid] = neuron.nodes[nid]
    # find trunks, trees, and terminals
    for p in projection:
        tree = networkx.algorithms.traversal.bfs_tree(neuron.dgraph, p)
        leaves = [node for node in tree if tree.out_degree(node) == 0]
        projection[p]['tree'] = tree
        projection[p]['terminals'] = leaves
        for t in leaves:
            if 'termination (projection trunk)' in \
                    neuron.nodes[t]['labels']:
                if ('trunk' in projection[p]) and \
                        (projection[p]['trunk'] != t):
                    logging.critical(
                        "projection has two trunks %s, %s",
                        projection[p]['trunk'], t)
                    raise ValueError("projection has two trunks {}, {}".format(
                        projection[p]['trunk'], t))
                projection[p]['trunk'] = t
    # cull projection
    # use keys() avoid RuntimeError: dictionary changed size during iteration
    for pa in projection.keys():
        for pb in projection.keys():
            if pa == pb or pb not in projection or pa not in projection:
                continue
            if pa in projection[pb]['tree']:
                del projection[pa]
    return projection


def axons(neuron):
    axs = {}
    # find axon nodes
    for nid in neuron.nodes:
        if 'axon' in neuron.nodes[nid]['labels']:
            axs[nid] = neuron.nodes[nid]
    # find trunks, trees, and terminals
    for ax in axs:
        tree = networkx.algorithms.traversal.bfs_tree(neuron.dgraph, ax)
        leaves = [node for node in tree if tree.out_degree(node) == 0]
        axs[ax]['tree'] = tree
        axs[ax]['terminals'] = leaves
        for t in leaves:
            if 'termination (axon trunk)' in \
                    neuron.nodes[t]['labels']:
                if ('trunk' in axs[ax]) and \
                        (axs[ax]['trunk'] != t):
                    logging.critical(
                        "axon has two trunks %s, %s",
                        axs[ax]['trunk'], t)
                    raise ValueError("axon has two trunks {}, {}".format(
                        axs[ax]['trunk'], t))
                axs[ax]['trunk'] = t
    # cull axons
    # use keys() avoid RuntimeError: dictionary changed size during iteration
    for axa in axs.keys():
        for axb in axs.keys():
            if axa == axb or axb not in axs or axa not in axs:
                continue
            if axa in axs[axb]['tree']:
                del axs[axa]
    return axs


def tags(sk):
    all_tags = {}
    for v in sk['vertices']:
        for l in sk['vertices'][v]['labels']:
            all_tags[l] = all_tags.get(l, []) + [v, ]
    return all_tags


def root(neuron):
    sg = networkx.topological_sort(neuron.dgraph)
    if not len(sg):
        if len(neuron.nodes) == 1:
            return neuron.nodes.keys()[0]
        else:
            # TODO print warning
            logging.warning(
                "Attempt to get root for neuron[%s] with %s nodes",
                neuron.name, len(neuron.nodes))
            return None
    return sg[0]


def dendrites(neuron):
    if len(neuron.axons) == 0:
        return neuron.dgraph
    dends = neuron.dgraph.copy()
    for ax in neuron.axons:
        for nid in neuron.axons[ax]['tree']:
            if nid in dends:
                dends.remove_node(nid)
    return dends


def leaves(neuron):
    return [n for n in neuron.dgraph if neuron.dgraph.out_degree(n) == 0]


def axon_trunk(neuron):
    # get main axon (one with trunk, if multiple, return all)
    axon_trunks = []
    for ax in neuron.axons:
        if 'trunk' in neuron.axons[ax]:
            axon_trunks.append(neuron.axons[ax])
    return axon_trunks


def get_id(skeleton):
    return skeleton.get('id', None)


def annotation(skeleton):
    return skeleton['neuron'].get('annotations', [])


def bifurcations(neuron):
    return [n for n in neuron.dgraph if neuron.dgraph.out_degree(n) > 1]
