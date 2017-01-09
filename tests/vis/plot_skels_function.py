#!/usr/bin/env python

import sys
import numpy
import catmaid

import vispy
import vispy.scene
import vispy.app


def renderNeurons(neurons, colors='random', w=2, aa=False):
    print("Rendering...")
    canvas = vispy.scene.SceneCanvas(
        keys='interactive', show=True,
        title='skeletons',
        px_scale=1)
    view = canvas.central_widget.add_view()
    view.camera = 'fly'
    view.camera.aspect = 1

    for n in neurons:
        if colors == 'random':
            RGB = numpy.random.rand(3)
            c = RGB[0], RGB[1], RGB[2], 1.
        else:
            c = 'green'
        ns, es = catmaid.algorithms.morphology.node_edge_array(n)
        if len(ns) == 0 or len(es) == 0:
            print("Skipping %s either 0 nodes or edges" % (n.skeleton_id, ))
            continue
        print("Adding: %s [%i, %i]" % (n.skeleton_id, len(ns), len(es)))
        pre_lines = vispy.scene.Line(
            pos=ns, connect=es,
            antialias=aa, width=w,
            method='gl', color=c, parent=view.scene)

    print("Showing...")
    view.camera.set_range()
    vispy.app.run()

if __name__ == "__main__":
    skel_fns = sys.argv[1:]
    if len(skel_fns) == 0:
        raise Exception("Must provide skeleton filenames")
    print("Loading skeletons: %s" % (skel_fns, ))
    neurons = [catmaid.Neuron(catmaid.neuron.load_skeleton(fn))
               for fn in skel_fns]
    renderNeurons(neurons)
