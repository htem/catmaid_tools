'''
This script saves python dictionaries describing the myelination profiles of
    catmaid skeletons to json files for further analysis.  Please see the
    included "dictionaryguide.txt" for details on the structure.

    TODO:
        Validate paths and lengths for profiles
        Remove scipy dependency
'''

import catmaid
import scipy.spatial
import json

source = '../../data/skeletons'
outputdir = '../../data/myelin_profiles/'


def segmentation(neuron, startnode, myelin):
    segments = {}
    if neuron.edges[startnode] > 1:
        children = neuron.redges[startnode]
        for child in children:
            segments.update(getsegments(neuron, startnode, myelin, segments))
    return segments


def getsegments(neu, parent, myelin, segments, prevtype='root'):
    z = {}
    sid = neu.skeleton_id
    startnode = parent
    segtype = "neurite"
    path = []
    pathlength = 0
    euclid = 0
    path.append(parent)

    if len(neu.edges[parent]) > 1:
        children = neu.redges[parent]
        for child in children:
            while len(neu.edges[child]) > 1:
                if len(neu.edges[child]) > 2:
                    print "branch at {} in neuron {}.".format(child, sid)
                    segtype = "branching"
                    euclid = nodedistancesameneuron(neu, parent, child)
                    tempdict = dict([('myelinated', myelin),
                                    ('pathlength', pathlength),
                                    ('path', path),
                                    ('prevtype', prevsegtype),
                                    ('type', segtype),
                                    ('euclidean', euclid)])
                    newdict = dict([(parent, tempdict)])
                    z.update(newdict)
                    for kid in neu.redges[child]:
                        z.update(getsegments(neu, kid, myelin, z, prevtype=segtype))
                    break

                elif (('myelinated' in neu.nodes[child]['labels']) or
                        ('unmyelinated' in neu.nodes[child]['labels'])):
                    print "myelination at {} in neuron {}.".format(child, sid)
                    segtype = "myelinating/unmyelinating"
                    euclid = nodedistancesameneuron(neu, parent, child)
                    tempdict = dict([('myelinated', myelin),
                                    ('pathlength', pathlength),
                                    ('path', path),
                                    ('type', segtype),
                                    ('prevtype', prevsegtype),
                                    ('euclidean', euclid)])
                    newdict = dict([(parent, tempdict)])
                    z.update(newdict)
                    myelin = not myelin
                    child = neu.redges[child][0]
                    z.update(getsegments(neu, child, myelin, z, prevtype=segtype))
                    break

                else:
                    pathlength += nodedistancesameneuron(neu,
                                                         neu.redges[child][0],
                                                         child)
                    if child not in neu.redges[child]:
                        child = neu.redges[child][0]
                        path.append(child)
            segtype = 'end'
            euclid = nodedistancesameneuron(neu, child, parent)
            tempdict = dict([('myelinated', myelin),
                            ('pathlength', pathlength),
                            ('path', path),
                            ('type', segtype),
                            ('euclidean', euclid)])
            newdict = dict([(parent, tempdict)])
            z.update(newdict)
    return z


def myelin_profile(neuron):
    myelin = {}
    if (('myelinated' in neuron.tags) or ('unmyelinated' in neuron.tags)):
        myelinstate = 'root myelinated' in neuron.nodes[neuron.root]['labels']
        myelin = segmentation(neuron, neuron.root, myelinstate)
    return myelin


def nodedistancesameneuron(neuron, node1, node2):
    # TODO this is a lame reason to have a scipy dependency
    a = [neuron.nodes[node1]['x'],
         neuron.nodes[node1]['y'],
         neuron.nodes[node1]['z']]
    b = [neuron.nodes[node2]['x'],
         neuron.nodes[node2]['y'],
         neuron.nodes[node2]['z']]
    return abs(scipy.spatial.distance.euclidean(a, b))


src = catmaid.get_source(source)

myelination = {}
for sid in src.skeleton_ids():
    n = src.get_neuron(sid)
    if not any([('Blacklist' in anno) for anno in n.annotations]):
        myelination[sid] = myelin_profile(n)

output = outputdir + "all.json"
with open(output, 'w') as f:
    json.dump(myelination, f)

for i in myelination:
    output = outputdir + str(i)
    with open(output, 'w') as f:
        json.dump(myelination[i], f)
