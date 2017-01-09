import catmaid
import numpy
import pickle
from time import strftime
import sys

filesource = '../../data/skeletons/'
# TODO transformfile should be set as environmental variable
#      and an error thrown if not set
transformfile = './physical_section_affine_4x4.p'
resXYZ = numpy.array([18.85, 18.85, 60.])
src = catmaid.get_source(filesource)

try:
    outfile = str(sys.argv[1])
except:
    outfile = '../../results/exports/{}_130201zf142_' \
              'ALLNODE_dump_RAW.txt'.format(strftime('%y%m%dT%H%M'))

with open(transformfile, 'r') as f:
    transforms = pickle.load(f)

with open(outfile, 'w') as f:
    for sid in src.skeleton_ids():
        n = src.get_neuron(sid)
        #if any([('blacklist' in anno) for anno in n.annotations]):
        #    continue
        for nid in n.nodes:
            if nid == n.root:
                parent = 'root'
            else:
                parent = n.dedges[nid][0]
            xpxaff, ypxaff, zpxaff = numpy.array([n.nodes[nid]['x'],
                                                  n.nodes[nid]['y'],
                                                  n.nodes[nid]['z']]) / resXYZ

            transformed_coords = (transforms[int(zpxaff)].I *
                                  numpy.matrix(numpy.array([xpxaff,
                                                            ypxaff,
                                                            zpxaff,
                                                            1.])).T)
            xraw, yraw, zraw = (float(i) for i in (transformed_coords[0],
                                                   transformed_coords[1],
                                                   transformed_coords[2]))
            f.write('{} {} {} {} {} {}\n'.format(sid, nid, str(parent),
                                                 xraw, yraw, int(zraw)))
