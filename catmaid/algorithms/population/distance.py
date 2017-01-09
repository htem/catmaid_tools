#!/usr/bin/env python

try:
    import numpy
    has_numpy = True
except ImportError:
    has_numpy = False

from .. import morphology


def near_path_length_md(
        n1, n2, g1=None, g2=None, distances=None, resample_distance=None,
        segments=False):
    """
    Returns the total pathlength of g1 that is < distance from the closest
    node in g2

    The distance is only calculated between nodes (not edges) so long edges
    can introduce errors. In this case, use a reasonable resample_distance.

    if g1 and g2 (the graphs of n1 and n2) are not supplied, they will
    default to the dendrites of g1 and the first axon for g2
    """
    if not has_numpy:
        raise ImportError("path_length requires numpy")
    if g1 is None:
        g1 = n1.dendrites
    if g2 is None:
        g2 = n2.axons.values()[0]['tree']
    if distances is None:
        distances = [1000., 5000.]
    if resample_distance is None:
        resample_distance = numpy.inf
    e1 = morphology.resampled_edge_array(n1, g1, resample_distance)
    #e2 = morphology.resampled_edge_array(n2, g2, resample_distance)
    nodes2 = numpy.array(
        morphology.resampled_node_array(n2, g2, resample_distance))
    # for each edge in e1
    pdi = {}
    mds = {}
    for d in distances:
        pdi[d] = {
            'l': 0.,
            'segs': [],
            'dt': d * d,
            'skip': False,
        }
    for edge in e1:
        s, e = edge[:3], edge[3:]
        st = tuple(s)
        if st not in mds:
            mds[st] = numpy.sum(numpy.square(s - nodes2), axis=1).min()
        et = tuple(e)
        if et not in mds:
            mds[et] = numpy.sum(numpy.square(e - nodes2), axis=1).min()
        for d in pdi:
            if mds[st] < pdi[d]['dt'] and mds[et] < pdi[d]['dt']:
                pdi[d]['l'] += numpy.linalg.norm(e - s)
                pdi[d]['segs'].append(edge)
    return pdi


def near_path_length(
        n1, n2, g1=None, g2=None, distance=1000., resample_distance=None,
        segments=False):
    """
    Returns the total pathlength of g1 that is < distance from the closest
    node in g2

    The distance is only calculated between nodes (not edges) so long edges
    can introduce errors. In this case, use a reasonable resample_distance.

    if g1 and g2 (the graphs of n1 and n2) are not supplied, they will
    default to the dendrites of g1 and the first axon for g2
    """
    if not has_numpy:
        raise ImportError("path_length requires numpy")
    if g1 is None:
        g1 = n1.dendrites
    if g2 is None:
        g2 = n2.axons.values()[0]['tree']
    if resample_distance is None:
        resample_distance = numpy.inf
    e1 = morphology.resampled_edge_array(n1, g1, resample_distance)
    #e2 = morphology.resampled_edge_array(n2, g2, resample_distance)
    nodes2 = numpy.array(
        morphology.resampled_node_array(n2, g2, resample_distance))
    # for each edge in e1
    l = 0.
    segs = []
    pns = {}
    sd = distance * distance
    for edge in e1:
        s, e = edge[:3], edge[3:]
        st = tuple(s)
        if st not in pns:
            pns[st] = numpy.sum(numpy.square(s - nodes2), axis=1).min() < sd
        if not pns[st]:
            continue
        et = tuple(e)
        if et not in pns:
            pns[et] = numpy.sum(numpy.square(e - nodes2), axis=1).min() < sd
        if not pns[et]:
            continue
        l += numpy.linalg.norm(e - s)
        segs.append(edge)
    if segments:
        return l, numpy.array(segs)
    return l


def hausdorff(n1, n2, g1=None, g2=None, resample_distance=None):
    """
    The maximum of the minimum distances between a node
    in n1 and any node in n2

    max[across a](min[across b](d(a, b))
    """
    if not has_numpy:
        raise ImportError("hasdorff distance requires numpy")
    if g1 is None:
        g1 = n1.axons.values()[0]['tree']
    if g2 is None:
        g2 = n2.dendrites

    if resample_distance is not None:
        n1s = numpy.array(
            morphology.resampled_node_array(
                n1, g1, resample_distance))
        n2s = numpy.array(
            morphology.resampled_node_array(
                n2, g2, resample_distance))
    else:
        n1s = morphology.node_array(n1, g1.nodes())
        n2s = morphology.node_array(n2, g2.nodes())
    #n1s = []
    #for nid in g1.nodes():
    #    n = n1.nodes[nid]
    #    n1s.append((n['x'], n['y'], n['z']))
    #n1s = numpy.array(n1s)
    #n2s = []
    #for nid in g2.nodes():
    #    n = n2.nodes[nid]
    #    n2s.append((n['x'], n['y'], n['z']))
    #n2s = numpy.array(n2s)
    v = -numpy.inf
    for n in n1s:
        v = max(
            v,
            numpy.min(numpy.sum((n2s - n) ** 2., 1)) ** 0.5)
    return v
