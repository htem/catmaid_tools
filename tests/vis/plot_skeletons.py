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

aa = False
w = 2

skel_fns = sys.argv[1:]
if len(skel_fns) == 0:
    raise Exception("Must provide skeleton filenames")

print("Loading skeletons: %s" % (skel_fns, ))
neurons = [catmaid.Neuron(catmaid.neuron.load_skeleton(fn)) for fn in skel_fns]

print("Rendering...")
canvas = vispy.scene.SceneCanvas(
    keys='interactive', show=True,
    title='skeletons',
    px_scale=1)
view = canvas.central_widget.add_view()
view.camera = 'fly'
view.camera.aspect = 1

for n in neurons:
    ns, es = catmaid.algorithms.morphology.node_edge_array(n)
    if len(ns) == 0 or len(es) == 0:
        print("Skipping %s either 0 nodes or edges" % (n.skeleton_id, ))
        continue
    print("Adding: %s [%i, %i]" % (n.skeleton_id, len(ns), len(es)))
    pre_lines = vispy.scene.Line(
        pos=ns, connect=es,
        antialias=aa, width=w,
        method='gl', color='green', parent=view.scene)

print("Showing...")
view.camera.set_range()
vispy.app.run()
