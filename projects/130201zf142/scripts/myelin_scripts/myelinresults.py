#!/usr/bin/env python
'''
This script analyzes myelin profiles output by "fishmyelin.py" and outputs
    visualizations as well as error messages for suspect physiology.

    TODO:
        include visualizations -- myelin histogram, dendrogram, etc.
        error message PEP8 -- no '+=' to concatenate
        error messages:
            branching myelin
            terminating myelin
'''
import json
import seaborn

myelin_file = '../../data/myelin_profiles/all.json'
err_file = '../../results/lists/myelinerr.txt'
outputdir = '../../results/myelin_data/'


def plotHistogram(pathlengths, euclids, types):
    # TODO function to plot relevant histogram of data
    print "plotting histogram!"


def plotDendrogram(skelmy):
    # TODO function to plot skeleton dendrogram w/ myelin data
    print "plotting dendrogram!"

with open(myelin_file, 'r') as f:
    myelination = json.load(f)

all_pathlengths = []
all_euclid = []

for sid in myelination:
    skel_pathlengths = []
    skel_euclid = []
    skel_types = []

    my = myelination[sid]
    for segment in my:
        seg = myl[segment]

        # check for myelin tagging irregularities
        # TODO citation to support lack of myelin at branch points?
        if (seg['myelinated'] and (seg['type'] == 'branching')):
            err += "branching myelination at node {} in skeleton {}.".format(
                    seg['path'][-1], sid)
        elif (seg['myelinated'] and (seg['type'] == 'terminating')):
            err += "myelinated tracing ends at node {} in skeleton {}".format(
                    seg['path'][-1], sid)

        skel_pathlengths.append(seg['pathlength'])
        skel_euclid.append(seg['euclid'])
        skel_types.append(seg['type'])

    all_pathlengths.extend(skel_pathlengths)
    all_euclid.extend(skel_pathlengths)
    all_types.extend(skel_types)

    plotHistogram(skel_pathlengths, skel_euclid, skel_types)
    plotDendrogram(my)

plotHistogram(all_pathlengths, all_euclid, all_types)

with open(err_file, 'w') as f:
    for lin in err:
        f.write("{}\n".format(lin))
