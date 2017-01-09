#!/usr/bin/env python
'''
# add test for ValueError: neuron has two somas
# add test for ValueError: unable to find root in skeleton, graph contains no nodes
# add test for ValueError: invalid axon id not in axon.keys (from myelination)
# maybe test it somewhere instead of here?
'''

import json
import unittest

import networkx
import numpy

import catmaid
import oldcatmaid


def load_skeleton(fn):
    f = open(fn, 'r')
    skel = json.load(f)
    f.close()
    return skel


normal_skel_fn = 'skel72324.json'
myelinated_skel_fn = 'skel9586.json'
normal_skel = load_skeleton(normal_skel_fn)
old_nron = oldcatmaid.Neuron(normal_skel)
new_nron = catmaid.neuron.Neuron(normal_skel)
myelinated_skel = load_skeleton(myelinated_skel_fn)
old_nron_myelinated = oldcatmaid.Neuron(myelinated_skel)
new_nron_myelinated = catmaid.neuron.Neuron(myelinated_skel)


def graph_equal(g1, g2):
    n1 = g1.nodes()
    n2 = g2.nodes()
    if len(n1) != len(n2):
        print("nodes unequal lengths: %s != %s" % (len(n1), len(n2)))
        return False
    for n in n1:
        if not g2.has_node(n):
            print("%s not in g2 nodes" % n)
            return False
    for n in n2:
        if not g1.has_node(n):
            print("%s not in g1 nodes" % n)
            return False
    e1 = g1.edges()
    e2 = g2.edges()
    if len(e1) != len(e2):
        print("edges unequal lengths: %s != %s" % (len(e1), len(e2)))
        return False
    for e in e1:
        if not g2.has_edge(*e):
            print("%s not in g2 edges" % (e,))
            return False
    for e in e2:
        if not g1.has_edge(*e):
            print("%s not in g1 edges" % (e,))
            return False
    return True


class LazyMethodTest(unittest.TestCase):
    def setUp(self):
        # moved to above to speed things up
        pass

    def test_name(self):
        self.assertEqual(old_nron.name, new_nron.name)

    def test_edges(self):
        self.assertEqual(
            sorted(old_nron.edges),
            sorted(new_nron.edges))

    def test_soma(self):
        self.assertEqual(old_nron.soma, new_nron.soma)

    def test_connectors(self):
        self.assertEqual(
            sorted(old_nron.connectors),
            sorted(new_nron.connectors))

    def test_synapses(self):
        self.assertEqual(
            sorted(old_nron.synapses),
            sorted(new_nron.synapses))

    def test_axons(self):
        for axon_id in new_nron.axons.keys():
            for key in new_nron.axons[axon_id]:
                if key != 'tree':
                    self.assertEqual(old_nron.axons[axon_id][key],
                                     new_nron.axons[axon_id][key])
                else:
                    self.assertTrue(
                        graph_equal(
                            old_nron.axons[axon_id]['tree'],
                            new_nron.axons[axon_id]['tree']))

    def test_tags(self):
        self.assertEqual(
            sorted(old_nron.tags),
            sorted(new_nron.tags))

    def test_root(self):
        self.assertEqual(old_nron.root, new_nron.root)

    def test_leaves(self):
        self.assertEqual(
            sorted(old_nron.leaves()), sorted(new_nron.leaves))

    def test_myelination(self):
        for axon_id in old_nron.myelination():
            for key in old_nron.myelination()[axon_id]:
                if key != 'pmas':
                    self.assertEqual(old_nron.myelination()[axon_id][key],
                                     new_nron.myelination[axon_id][key])
                else:
                    if not (numpy.isnan(
                        old_nron.myelination()[axon_id]['pmas']) and
                            numpy.isnan(
                                new_nron.myelination[axon_id]['pmas'])):
                        self.assertEqual(
                            old_nron.myelination()[axon_id]['pmas'],
                            new_nron.myelination[axon_id]['pmas'])

        self.assertEqual(old_nron_myelinated.myelination(),
                         new_nron_myelinated.myelination)

    def test_center_of_mass(self):
        ocm = old_nron.center_of_mass()
        ncm = new_nron.center_of_mass
        self.assertEqual(sorted(ocm.keys()), sorted(ncm.keys()))
        for a in ('x', 'y', 'z'):
            self.assertAlmostEqual(ocm[a], ncm[a])

    def test_graph(self):
        self.assertTrue(graph_equal(
            old_nron.graph, new_nron.graph))

    def test_dendrites(self):
        self.assertTrue(graph_equal(
            old_nron.dendrites(), new_nron.dendrites))

    def test_dgraph(self):
        self.assertTrue(graph_equal(
            old_nron.dgraph, new_nron.dgraph))

    def test_axon_trunk(self):
        for num in range(len(old_nron.axon_trunk())):
            for key in old_nron.axon_trunk()[num]:
                if key != 'tree':
                    self.assertEqual(old_nron.axon_trunk()[num][key],
                                     new_nron.axon_trunk[num][key])
                else:
                    self.assertTrue(graph_equal(
                        old_nron.axon_trunk()[num]['tree'],
                        new_nron.axon_trunk[num]['tree']))


if __name__ == '__main__':
    unittest.main()
