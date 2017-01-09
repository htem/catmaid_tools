#!/usr/bin/env python

import json
import unittest
import os

import catmaid


def load_skeleton(fn):
    f = open(fn, 'r')
    skel = json.load(f)
    f.close()
    return skel


fake_skeletons_loc = os.path.realpath('fake_skeletons')
fake_skel_noaxon_fn = '{}/fake_skel_noaxon.json'.format(fake_skeletons_loc)
fake_skel_pd_close_fn = '{}/fake_skel_pd_close.json'.format(fake_skeletons_loc)
fake_skel_pd_far_fn = '{}/fake_skel_pd_far.json'.format(fake_skeletons_loc)
fake_skel_pp_fn = '{}/fake_skel_pp.json'.format(fake_skeletons_loc)
fake_skel_noaxon = load_skeleton(fake_skel_noaxon_fn)
fake_skel_pd_close = load_skeleton(fake_skel_pd_close_fn)
fake_skel_pd_far = load_skeleton(fake_skel_pd_far_fn)
fake_skel_pp = load_skeleton(fake_skel_pp_fn)
fake_nron_noaxon = catmaid.neuron.Neuron(fake_skel_noaxon)
fake_nron_pd_close = catmaid.neuron.Neuron(fake_skel_pd_close)
fake_nron_pd_far = catmaid.neuron.Neuron(fake_skel_pd_far)
fake_nron_pp = catmaid.neuron.Neuron(fake_skel_pp)


class SynapsesTest(unittest.TestCase):
    def setUp(self):
        pass

    # TODO: add test for checking exception of comparing
    # nron has no axon with nron has axon.
    def test_skeleton_overlap(self):
        self.assertEqual(catmaid.algorithms.population.synapses.skeleton_overlap(fake_nron_pd_close, fake_nron_noaxon), 8.9793504941625167e-09)
        self.assertEqual(catmaid.algorithms.population.synapses.skeleton_overlap(fake_nron_pd_far, fake_nron_noaxon), 8.9792607011065419e-09)
        self.assertEqual(catmaid.algorithms.population.synapses.skeleton_overlap(fake_nron_pp, fake_nron_noaxon), 3.5917339121251888e-08)


if __name__ == '__main__':
    unittest.main()

