#!/usr/bin/env python
'''
todo:
figure out how to test StopIteration?
add tests for: all_neurons, all_neuron_iters, neurons_from_sk_list
               neuron_overlap, list_overlap, get_tags, find_axons, unlabeled_leaves
'''

import json
import unittest
import os

import catmaid


source_loc = os.path.realpath('skeletons')


skel_9586 = '{}/skel9586.json'.format(source_loc)


class FileSourceTests(unittest.TestCase):
    def setUp(self):
        def load_skeleton(fn):
            f = open(fn, 'r')
            skel = json.load(f)
            skel['id'] = fn.strip('{}/skel*.json'.format(source_loc))
            f.close()
            return skel

        self.maxDiff = None
        self.file_source = catmaid.source.get_source(source_loc)
        self.file_source.filename_format = "skel{}.json"
        self.skel_ids_iter = self.file_source.skeleton_ids_iter()
        self.skel9586 = load_skeleton(skel_9586)

    def test_init(self):
        self.assertIsInstance(self.file_source, catmaid.source.Source)
        self.assertEqual(self.file_source._skel_source, source_loc)

    def test_skeleton_ids_iter(self):
        self.assertEqual(self.skel_ids_iter.next(), 9586)
        self.assertEqual(self.skel_ids_iter.next(), 72324)
        try:
            self.skel_ids_iter.next()
        except StopIteration:
            self.assertEqual(list(self.skel_ids_iter), [])

    def test_skeleton_ids(self):
        self.assertEqual(self.file_source.skeleton_ids(),
                         [9586, 72324])

    def test_get_skeleton(self):
        self.assertEqual(self.file_source.get_skeleton('9586'),
                         self.skel9586)

    def test_get_neuron(self):
        self.assertIsInstance(self.file_source.get_neuron('9586'),
                              catmaid.neuron.Neuron)
        self.assertEqual(self.file_source.get_neuron('9586').skeleton,
                         self.skel9586)


if __name__ == '__main__':
    unittest.main()

