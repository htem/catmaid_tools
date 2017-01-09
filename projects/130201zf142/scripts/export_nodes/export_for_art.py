import catmaid
import numpy
import pickle
from time import strftime
import sys

filesource = '../../data/skeletons1/'
resXYZ = numpy.array([18.85, 18.85, 60.])
src = catmaid.get_source(filesource)

try:
    outfile = str(sys.argv[1])
except:
    outfile = '../../results/exports/{}_130201zf142_ALLNODE_dump_AFFINE.txt'.format(strftime('%y%m%dT%H%M'))


with open(outfile, 'w') as f:
    connectors = {}
    for sid in src.skeleton_ids():
        n = src.get_neuron(sid)
        if len(n.connectors) > 0:
            connectors.update(n.connectors)
        if any([('blacklist' in anno) for anno in n.annotations]):
            if not any([('export' in anno) for anno in n.annotations]):
                continue
        for nid in n.nodes:
            if nid == n.root:
                parent = 'root'
            else:
                parent = n.dedges[nid][0]
            xpxaff, ypxaff, zpxaff = numpy.array([n.nodes[nid]['x'],
                                                  n.nodes[nid]['y'],
                                                  n.nodes[nid]['z']]) / resXYZ
            f.write('{} {} {} {} {} {}\n'.format(sid, nid, str(parent),
                                                 xpxaff, ypxaff, int(zpxaff)))
    for item in connectors.items():
        parent = 'root'
        sid = 'connector'
        xpxaff, ypxaff, zpxaff = numpy.array([item[1]['x'],
                                              item[1]['y'],
                                              item[1]['z']]) / resXYZ
        f.write('{} {} {} {} {} {}\n'.format(str(sid), item[0], str(parent),
                                             xpxaff, ypxaff, int(zpxaff)))
