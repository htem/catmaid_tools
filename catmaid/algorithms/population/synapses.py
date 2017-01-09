#!/usr/bin/env python
"""
TODO:
1. add discription
2. find two small neurons and test it?

overlap
N(a, d) = 2s sum_i_j(l_a_i * l_d_j * abs(sin(n_a_i, n_d_j)) *
    exp[ -((r_a_i - r_d_j) ** 2) / (4 * sig ** 2)] / (4 * pi * sig ** 2) ** 1.5

l_x_y = length of segment y on skeleton x
n_x_y = unit vector along segment y of skeleton x
r_x_y = location of segment y of skeleton x
s = "the distance entering the definition of the potential synapse" huh?
abs(sin(...)) = abs of sin of angle between unit vectors
sig = gaussian sigma
"""
import logging
import itertools
import numpy

# import catmaid
# TODO only axon/dendrite overlap, for now just calculate all


class EdgeError(Exception):
    pass


def edge_to_cylinder(uv, vv):
    # find midpoints (r_a, r_d)
    # calculate unit vectors (n_a, n_d)
    # get lengths (l_a, l_d)
    uv = numpy.array([uv[i] for i in ('x', 'y', 'z')])
    vv = numpy.array([vv[i] for i in ('x', 'y', 'z')])
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


def edge_to_cylinder_v(uv, vv):
    v = vv - uv
    r = v / 2. + uv
    l = numpy.sum(v ** 2., axis=1) ** 0.5
    n = v / l[:, numpy.newaxis]
    # remove 0 length cylinders
    m = l != 0
    return r[m], n[m], l[m]


def angle(a, d):
    dp = numpy.dot(a, d)  # sometimes, this is slightly outside [-1, 1]
    if dp > 1.0:
        dp = 1.0
    elif dp < -1.0:
        dp = -1.0
    v = numpy.arccos(dp)
    return v


def dot_v(a, d):
    return numpy.einsum('ij,ij->i', a, d)


def angle_v(a, d):
    dp = dot_v(a, d)
    dp[dp > 1.0] = 1.0
    dp[dp < -1.0] = -1.0
    return numpy.arccos(dp)


def cylinder_overlap(a, d, sig=10000.):
    ra, na, la = [a[k] for k in ('r', 'n', 'l')]
    rd, nd, ld = [d[k] for k in ('r', 'n', 'l')]
    rdiff = (ra - rd)
    v = la * ld * abs(numpy.sin(angle(na, nd))) * numpy.exp(
        -(numpy.dot(rdiff, rdiff)) / (4 * sig ** 2.)) / (
        (4 * numpy.pi * sig ** 2) ** 1.5)
    if numpy.isnan(v):
        logging.critical("cylinder_overlap = nan, {}, {}".format(a, d))
        raise Exception("cylinder_overlap = nan, {}, {}".format(a, d))
    return v


def cylinder_overlap_v(ra, na, la, rd, nd, ld, sig=10000.):
    rdiff = (ra - rd)
    v = la * ld * abs(
        numpy.sin(angle_v(na, nd))) * numpy.exp(
        -(dot_v(rdiff, rdiff)) / (4 * sig ** 2.)) / (
        (4 * numpy.pi * sig ** 2) ** 1.5)
    return v


def cylinder_proximity_v(ra, na, la, rd, nd, ld, sig=10000.):
    rdiff = (ra - rd)
    v = la * ld * numpy.exp(
        -(dot_v(rdiff, rdiff)) / (4 * sig ** 2.)) / (
        (4 * numpy.pi * sig ** 2) ** 1.5)
    return v


def get_edge_array(n, edges):
    uvs = []
    vvs = []
    vs = n.skeleton['vertices']
    for (ui, vi) in edges:
        u = vs[ui]
        v = vs[vi]
        uvs.append((u['x'], u['y'], u['z']))
        vvs.append((v['x'], v['y'], v['z']))
    return numpy.array(uvs), numpy.array(vvs)


def skeleton_overlap_v_verbose(
        neuron_a, neuron_d, s=1000., sig=10000., g1=None, g2=None,
        ordered_by='axon', op=numpy.sum, output=None):
    if output is None:
        output = {'midpoint': True}
    if g1 is None:
        axon = neuron_a.axons
        if len(axon) != 1:
            msg = "axon skeleton {} has != 1 [{}] axon".format(
                neuron_a.name, len(axon))
            logging.critical(msg)
            raise Exception(msg)
        axon = axon[axon.keys()[0]]['tree']
    else:
        axon = g1

    # precompute cylinders
    if g2 is None:
        dendrites = neuron_d.dendrites
    else:
        dendrites = g2
    # get edges
    ra, na, la = edge_to_cylinder_v(
        *get_edge_array(neuron_a, axon.edges_iter()))
    rd, nd, ld = edge_to_cylinder_v(
        *get_edge_array(neuron_d, dendrites.edges_iter()))

    totals = []
    if ordered_by == 'axon':
        for i in xrange(len(la)):
            r = op(2. * s * cylinder_overlap_v(
                ra[i, numpy.newaxis], na[i, numpy.newaxis],
                la[i, numpy.newaxis],
                rd, nd, ld, sig=sig))
            t = []
            if output.get('midpoint', False):
                t.extend(ra[i])
            if isinstance(r, (tuple, list)):
                t.extend(list(r))
            else:
                t.append(r)
            if output.get('normal', False):
                t.extend(na[i])
            if output.get('length', False):
                t.append(la[i])
            totals.append(t)
            #totals.append(
            #    (ra[i][0], ra[i][1], ra[i][2], r))
    elif ordered_by == 'dendrite':
        for i in xrange(len(ld)):
            r = op(2. * s * cylinder_overlap_v(
                ra, na, la,
                rd[i, numpy.newaxis], nd[i, numpy.newaxis],
                ld[i, numpy.newaxis], sig=sig))
            t = []
            if output.get('midpoint', False):
                t.extend(rd[i])
            if isinstance(r, (tuple, list)):
                t.extend(list(r))
            else:
                t.append(r)
            if output.get('normal', False):
                t.extend(nd[i])
            if output.get('length', False):
                t.append(ld[i])
            totals.append(t)
            #totals.append(
            #    (rd[i][0], rd[i][1], rd[i][2], r))
    return totals


def skeleton_proximity_v(
        neuron_a, neuron_d, s=1000., sig=10000., g1=None, g2=None):
    # 1706 seconds
    # passing instance of neurons
    # if isinstance(fn_a, catmaid.Neuron):
        # sk_a = fn_a
    # else:
        # sk_a = catmaid.Neuron(json.load(open(fn_a, 'r')))
    # if isinstance(fn_a, catmaid.Neuron):
        # sk_d = fn_d
    # else:
        # sk_d = catmaid.Neuron(json.load(open(fn_d, 'r')))
    if g1 is None:
        axon = neuron_a.axons
        if len(axon) != 1:
            msg = "axon skeleton {} has != 1 [{}] axon".format(
                neuron_a.name, len(axon))
            logging.critical(msg)
            raise Exception(msg)
        axon = axon[axon.keys()[0]]['tree']
    else:
        axon = g1

    # precompute cylinders
    if g2 is None:
        dendrites = neuron_d.dendrites
    else:
        dendrites = g2
    # get edges
    ra, na, la = edge_to_cylinder_v(
        *get_edge_array(neuron_a, axon.edges_iter()))
    rd, nd, ld = edge_to_cylinder_v(
        *get_edge_array(neuron_d, dendrites.edges_iter()))

    total = 0.
    for i in xrange(len(la)):
        total += numpy.sum(cylinder_proximity_v(
            ra[i, numpy.newaxis], na[i, numpy.newaxis], la[i, numpy.newaxis],
            rd, nd, ld, sig=sig))
    return total * 2. * s


def skeleton_overlap_v(
        neuron_a, neuron_d, s=1000., sig=10000., g1=None, g2=None):
    # 1706 seconds
    # passing instance of neurons
    # if isinstance(fn_a, catmaid.Neuron):
        # sk_a = fn_a
    # else:
        # sk_a = catmaid.Neuron(json.load(open(fn_a, 'r')))
    # if isinstance(fn_a, catmaid.Neuron):
        # sk_d = fn_d
    # else:
        # sk_d = catmaid.Neuron(json.load(open(fn_d, 'r')))
    if g1 is None:
        axon = neuron_a.axons
        if len(axon) != 1:
            msg = "axon skeleton {} has != 1 [{}] axon".format(
                neuron_a.name, len(axon))
            logging.critical(msg)
            raise Exception(msg)
        axon = axon[axon.keys()[0]]['tree']
    else:
        axon = g1

    # precompute cylinders
    if g2 is None:
        dendrites = neuron_d.dendrites
    else:
        dendrites = g2
    # get edges
    ra, na, la = edge_to_cylinder_v(
        *get_edge_array(neuron_a, axon.edges_iter()))
    rd, nd, ld = edge_to_cylinder_v(
        *get_edge_array(neuron_d, dendrites.edges_iter()))

    total = 0.
    for i in xrange(len(la)):
        total += numpy.sum(cylinder_overlap_v(
            ra[i, numpy.newaxis], na[i, numpy.newaxis], la[i, numpy.newaxis],
            rd, nd, ld, sig=sig))
    return total * 2. * s
    # iterate over sk.dgraph.edges_iter
    total = 0.
    #n = len(axon.edges()) * 0.01
    #i = 0
    for _, _, a in axon.edges_iter(data=True):
        #i += 1
        if not a['valid']:
            continue
        for _, _, d in dendrites.edges_iter(data=True):  # 13.9%
            if not d['valid']:
                continue
            total += cylinder_overlap(a, d, sig=sig)  # 82.7%

    return total * 2. * s


def skeleton_overlap(neuron_a, neuron_d, s=1000., sig=10000.):
    # 1706 seconds
    # passing instance of neurons
    # if isinstance(fn_a, catmaid.Neuron):
        # sk_a = fn_a
    # else:
        # sk_a = catmaid.Neuron(json.load(open(fn_a, 'r')))
    # if isinstance(fn_a, catmaid.Neuron):
        # sk_d = fn_d
    # else:
        # sk_d = catmaid.Neuron(json.load(open(fn_d, 'r')))
    axon = neuron_a.axons
    if len(axon) != 1:
        msg = "axon skeleton {} has != 1 [{}] axon".format(
            neuron_a.name, len(axon))
        logging.critical(msg)
        raise Exception(msg)
    axon = axon[axon.keys()[0]]['tree']

    # precompute cylinders
    dendrites = neuron_d.dendrites
    for (nron, g) in ((neuron_a, axon), (neuron_d, dendrites)):
        for u, v, d in g.edges_iter(data=True):
            try:
                d['r'], d['n'], d['l'] = edge_to_cylinder(
                    nron.skeleton['vertices'][u], nron.skeleton['vertices'][v])
                d['valid'] = True
            except EdgeError as e:
                logging.error("Bad edge: {} -> {} on {}, Error: {}".format(
                    u, v, nron, e))
                d['valid'] = False

    # iterate over sk.dgraph.edges_iter
    total = 0.
    #n = len(axon.edges()) * 0.01
    #i = 0
    for _, _, a in axon.edges_iter(data=True):
        #i += 1
        if not a['valid']:
            continue
        for _, _, d in dendrites.edges_iter(data=True):  # 13.9%
            if not d['valid']:
                continue
            total += cylinder_overlap(a, d, sig=sig)  # 82.7%

    return total * 2. * s


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
