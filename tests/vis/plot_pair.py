#!/usr/bin/env python

import sys

import numpy

import vispy
import vispy.scene
import vispy.app

import catmaid


path_length = True
distance = 1000.
resample_distance = 1000.

aa = True
w = 2

prefn = 'pre.json'
postfn = 'post.json'
if len(sys.argv) == 3:
    prefn, postfn = sys.argv[1:3]

pre = catmaid.Neuron(catmaid.neuron.load_skeleton(prefn))
post = catmaid.Neuron(catmaid.neuron.load_skeleton(postfn))

if path_length:
    print "Computing near path length"
    l, segs = catmaid.algorithms.population.distance.near_path_length(
        post, pre, g1=post.dendrites, g2=pre.axons.values()[0]['tree'],
        distance=distance, resample_distance=resample_distance,
        segments=True)
    print("Near path length: %s [%i segments]" % (l, len(segs)))
else:
    l = -1.

t = 'pre=%s post=%s, %.4f nm [%i segments]' % (
    pre.skeleton_id, post.skeleton_id, l, len(segs))

canvas = vispy.scene.SceneCanvas(
    keys='interactive', show=True,
    title=t,
    px_scale=1)
view = canvas.central_widget.add_view()
view.camera = 'fly'
view.camera.aspect = 1

if path_length and len(segs):
    seg_nodes = segs.reshape((segs.shape[0] * 2, 3))
    seg_conns = numpy.arange(seg_nodes.shape[0]).reshape(
        (segs.shape[0], 2))
    seg_lines = vispy.scene.Line(
        pos=seg_nodes, connect=seg_conns,
        antialias=aa, width=w*2.,
        method='gl', color='red', parent=view.scene)

pre_edges = catmaid.algorithms.morphology.resampled_edge_array(
    pre, distance=distance, graph=pre.axons.values()[0]['tree'])
pre_nodes = pre_edges.reshape((pre_edges.shape[0] * 2, 3))
pre_conns = numpy.arange(pre_nodes.shape[0]).reshape(
    (pre_edges.shape[0], 2))
pre_lines = vispy.scene.Line(
    pos=pre_nodes, connect=pre_conns,
    antialias=aa, width=w,
    method='gl', color='green', parent=view.scene)

post_edges = catmaid.algorithms.morphology.resampled_edge_array(
    post, distance=distance, graph=post.dendrites)
post_nodes = post_edges.reshape((post_edges.shape[0] * 2, 3))
post_conns = numpy.arange(post_nodes.shape[0]).reshape(
    (post_edges.shape[0], 2))
post_lines = vispy.scene.Line(
    pos=post_nodes, connect=post_conns,
    antialias=aa, width=w,
    method='gl', color='blue', parent=view.scene)

view.camera.set_range()
vispy.app.run()
