#!/usr/bin/env python


def get_unlabeled_leaves(source, good_tags=None):
    if good_tags is None:
        good_tags = ['postsynaptic',
                     'presynaptic',
                     'uncertain continuation',
                     'uncertain end',
                     'layer 1', ]
    nodes = []

    def labeled(tags):
        for t in tags:
            if t in good_tags:
                return True
            if 'termination' in t:
                return True
        return False

    for n in source.all_neurons_iter():
        for l in n.leaves:
            if labeled(n.nodes[l]):
                continue
            nodes.append({
                'nid': n.name, 'sid': n.skeleton_id,
                'node': l, 'labels': n.nodes[l]})

    return nodes
