#!/usr/bin/env python
"""
Modification of likely-synapse calculation to measure cofasciculation
(sin switched to cos)

Will take as input two graphs (dendrites or axons) and some distance threshold.
The distance threshold is used to skip comparing edges that are too far apart.

For each pair of edges (1 from each graph), the minimum distance is computed,
compared against the threshold, and if the distance is <= threshold then
the cofasciculation metric is calculated. The result should be a list of
(
    node 1 of edge i of neuron a,
    node 2 of edge i of neuron b,
    n2einb, n2einc,
    distance, metric
)

A better metric for this might just be having distance and angle thresholds,
using those to find segments that cofasiculate, and measure the length over
which the segments cofasciculate.

Alternative metric:
    - get all edges from both neurons
    - calculate minimum distance between edge pairs, find < threshold pairs
    - repeat for angles [perhaps abs(cos(angle)) instead]
    - return remaining pairs and path length (each chain? sub-edge?)
"""
import logging
import itertools
import numpy


class EdgeError(Exception):
    pass


def vertex_to_point(v):
    return numpy.array([v[i] for i in ('x', 'y', 'z')])


def edge_to_cylinder(uv, vv):
    # find midpoints (r_a, r_d)
    # calculate unit vectors (n_a, n_d)
    # get lengths (l_a, l_d)
    #uv = numpy.array([uv[i] for i in ('x', 'y', 'z')])
    #vv = numpy.array([vv[i] for i in ('x', 'y', 'z')])
    v = vv - uv
    r = v / 2. + uv  # midpoint
    l = numpy.sum(v ** 2.) ** 0.5  # length
    if l == 0.:
        raise EdgeError(
            "invalid edge between two overlapping nodes: {}, {}".format(
                uv, vv))
    n = v / l  # unit vector
    assert numpy.abs(numpy.linalg.norm(n) - 1) < 0.001
    return r, n, l


def angle(a, d):
    dp = numpy.dot(a, d)  # sometimes, this is slightly outside [-1, 1]
    if dp > 1.0:
        dp = 1.0
    elif dp < -1.0:
        dp = -1.0
    v = numpy.arccos(dp)
    return v


def cylinder_cofasciculation(a, d, sig=10000.):
    ra, na, la = [a[k] for k in ('r', 'n', 'l')]
    rd, nd, ld = [d[k] for k in ('r', 'n', 'l')]
    rdiff = (ra - rd)
    v = la * ld * abs(numpy.cos(angle(na, nd))) * numpy.exp(
        -(numpy.dot(rdiff, rdiff)) / (4 * sig ** 2.)) / (
            (4 * numpy.pi * sig ** 2) ** 1.5)
    if numpy.isnan(v):
        logging.critical("cylinder_cofasciculation = nan, {}, {}".format(a, d))
        raise Exception("cylinder_cofasciculation = nan, {}, {}".format(a, d))
    return v


def cylinder_minimum_distance(a, b):
    return min(
        numpy.linalg.norm(a['u'] - b['u']),
        numpy.linalg.norm(a['u'] - b['v']),
        numpy.linalg.norm(a['v'] - b['u']),
        numpy.linalg.norm(a['v'] - b['v']))


def edges_to_array(n, g):
    # [nid_1, nid_2, x_1, y_1, z_1, x_2, y_2, z_2]
    a = numpy.empty((len(g.edges()), 8), dtype='f8')
    i = 0
    for u, v in g.edges_iter():
        un = n.nodes[u]
        vn = n.nodes[v]
        a[i] = map(
            float, (
                u, v, un['x'], un['y'], un['z'], vn['x'], vn['y'], vn['z']))
        i += 1
    return a


def dists(a):
    return numpy.sum(a ** 2., axis=1) ** 0.5


def cofasciculation2(
        neuron_a, graph_a, neuron_b, graph_b,
        distance_threshold=1000., angle_threshold=90.,
        return_pairs=True):
    """
    Alternative metric:
        - get all edges from both neurons
        - calculate minimum distance between edge pairs, find < threshold pairs
        - repeat for angles
        - return remaining pairs and path length (each chain? sub-edge?)
    """
    if distance_threshold is None:
        distance_threshold = float('inf')
    if angle_threshold is None:
        angle_threshold = 361.
    angle_threshold = numpy.radians(angle_threshold)
    # [nid_1, nid_2, x_1, y_1, z_1, x_2, y_2, z_2]
    a = edges_to_array(neuron_a, graph_a)
    b = edges_to_array(neuron_b, graph_b)
    r = []
    # find pairs for each a
    for ai in a:
        ua = ai[2:5]
        va = ai[5:]
        ubs = b[:, 2:5]
        vbs = b[:, 5:]
        na = ua - va
        na /= numpy.linalg.norm(na)  # normalized vector
        # minimum distance for all ds
        min_dist = numpy.min(numpy.vstack((
            dists(ua - ubs),
            dists(va - ubs),
            dists(ua - vbs),
            dists(va - vbs),
        )), axis=0)
        # angles
        bns = ubs - vbs
        bns /= dists(bns)[:, numpy.newaxis]
        for i in numpy.where(min_dist <= distance_threshold)[0]:
            relative_angle = angle(na, bns[i])
            # clamp angles to +- 90
            #while relative_angle > (numpy.pi / 2.):
            #    relative_angle -= numpy.pi
            #while relative_angle < -(numpy.pi / 2.):
            #    relative_angle += numpy.pi
            if numpy.abs(relative_angle) < angle_threshold:
                r.append((
                    ai[0], ai[1], b[i][0], b[i][1],
                    min_dist[i], relative_angle))
    if return_pairs:
        return r


def cofasciculation(
        neuron_a, graph_a, neuron_b, graph_b,
        distance=1000., s=1000., sig=10000.):
    if distance is None:
        distance = float('inf')
    # build cylinders
    for (nron, g) in ((neuron_a, graph_a), (neuron_b, graph_b)):
        for u, v, d in g.edges_iter(data=True):
            try:
                uv = vertex_to_point(nron.skeleton['vertices'][u])
                vv = vertex_to_point(nron.skeleton['vertices'][v])
                d['u'] = uv
                d['v'] = vv
                d['r'], d['n'], d['l'] = edge_to_cylinder(uv, vv)
                d['valid'] = True
            except EdgeError as e:
                logging.error("Bad edge: {} -> {} on {}, Error: {}".format(
                    u, v, nron, e))
                d['valid'] = False

    # iterate over sk.dgraph.edges_iter
    edges = []
    #n = len(axon.edges()) * 0.01
    #i = 0
    for u1, v1, a in graph_a.edges_iter(data=True):
        #i += 1
        if not a['valid']:
            continue
        for u2, v2, b in graph_b.edges_iter(data=True):
            if not d['valid']:
                continue
            dist = cylinder_minimum_distance(a, b)
            if dist > distance:
                continue
            metric = cylinder_cofasciculation(a, b, sig=sig) * 2. * s
            edges.append((u1, v1, u2, v2, dist, metric))

    return edges


def test():
    v0 = {'x': 0., 'y': 0., 'z': 0.}
    vx1 = {'x': 1., 'y': 0., 'z': 0.}
    vy1 = {'x': 0., 'y': 1., 'z': 0.}
    vz1 = {'x': 0., 'y': 0., 'z': 1.}
    vx2 = {'x': 2., 'y': 0., 'z': 0.}
    vy2 = {'x': 0., 'y': 2., 'z': 0.}
    vz2 = {'x': 0., 'y': 0., 'z': 2.}
    cx1 = edge_to_cylinder(v0, vx1)
    assert all(cx1[0] == [0.5, 0., 0.])
    assert all(cx1[1] == [1., 0., 0.])
    assert cx1[2] == 1.0
    cy1 = edge_to_cylinder(v0, vy1)
    assert all(cy1[0] == [0., 0.5, 0.])
    assert all(cy1[1] == [0., 1., 0.])
    assert cy1[2] == 1.0
    cz1 = edge_to_cylinder(v0, vz1)
    assert all(cz1[0] == [0., 0., 0.5])
    assert all(cz1[1] == [0., 0., 1.])
    assert cz1[2] == 1.0
    cx2 = edge_to_cylinder(v0, vx2)
    assert all(cx2[0] == [1., 0., 0.])
    assert all(cx2[1] == [1., 0., 0.])
    assert cx2[2] == 2.0
    cy2 = edge_to_cylinder(v0, vy2)
    assert all(cy2[0] == [0., 1., 0.])
    assert all(cy2[1] == [0., 1., 0.])
    assert cy2[2] == 2.0
    cz2 = edge_to_cylinder(v0, vz2)
    assert all(cz2[0] == [0., 0., 1.])
    assert all(cz2[1] == [0., 0., 1.])
    assert cz2[2] == 2.0
    cx12 = edge_to_cylinder(vx1, vx2)
    assert all(cx12[0] == [1.5, 0., 0.])
    assert all(cx12[1] == [1., 0., 0.])
    assert cx12[2] == 1.0
    cy12 = edge_to_cylinder(vy1, vy2)
    assert all(cy12[0] == [0., 1.5, 0.])
    assert all(cy12[1] == [0., 1., 0.])
    assert cy12[2] == 1.0
    cz12 = edge_to_cylinder(vz1, vz2)
    assert all(cz12[0] == [0., 0., 1.5])
    assert all(cz12[1] == [0., 0., 1.])
    assert cz12[2] == 1.0

    # angle
    ars = [numpy.array([a[i] for i in ('x', 'y', 'z')])
           for a in (vx1, vy1, vz1)]
    for a in ars:
        for b in ars:
            if all(a == b):
                assert angle(a, b) == 0.
            else:
                assert angle(a, b) == (numpy.pi / 2.)

    # cylinder_overlap
    def co(a, b, **kwargs):
        return cylinder_overlap(
            dict(zip(('r', 'n', 'l'), a)),
            dict(zip(('r', 'n', 'l'), b)))
    assert co(cx1, cx1, sig=10.) == 0.
    assert co(cx1, cx2, sig=10.) == 0.
    assert co(cy1, cy1, sig=10.) == 0.
    assert co(cy1, cy2, sig=10.) == 0.
    assert co(cz1, cz1, sig=10.) == 0.
    assert co(cz1, cz2, sig=10.) == 0.
    cx = edge_to_cylinder(
        {'x': -1, 'y': 0, 'z': 0},
        {'x': 1, 'y': 0, 'z': 0})
    cy = edge_to_cylinder(
        {'x': 0, 'y': -1, 'z': 0},
        {'x': 0, 'y': 1, 'z': 0})
    cz = edge_to_cylinder(
        {'x': 0, 'y': 0, 'z': -1},
        {'x': 0, 'y': 0, 'z': 1})
    print co(cx, cy, sig=10.)
    print co(cx, cz, sig=10.)
    print co(cy, cx, sig=10.)
    print co(cy, cz, sig=10.)
    print co(cz, cx, sig=10.)
    print co(cz, cy, sig=10.)
    # skeleton_overlap


def overlap_list(source, skList):
    """Cycles through all pairs of skeletons on the list and does
    the skeleton overlap for them"""
    pairs = itertools.combinations(skList, 2)
    overlap_dict = {}
    for sk_a, sk_d in pairs:
        nr_a = source.get_neuron(sk_a)
        nr_d = source.get_neuron(sk_d)
        ov_a = skeleton_overlap(nr_a, nr_d)
        ov_b = skeleton_overlap(nr_d, nr_a)
        try:
            overlap_dict[(sk_a, sk_d)] = ov_a
        except Exception as e:
            overlap_dict[(sk_a, sk_d)] = "Error: {}".format(e)
        try:
            overlap_dict[(sk_d, sk_a)] = ov_b
        except Exception as e:
            overlap_dict[(sk_d, sk_a)] = ov_b
    return overlap_dict
