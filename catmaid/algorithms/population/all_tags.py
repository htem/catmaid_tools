#!/usr/bin/env python


def get_tags(source):
    """Gets all tags from all skeletons in a skelSource"""
    tags = {}
    for n in source.all_neurons_iter():
        for t in n.tags:
            tags[t] = tags.get(t, []) + [
                {'nid': n.name, 'sid': n.skeleton_id, 'nodes': n.tags[t]}]
    return tags
