import argparse
import catmaid
import catmaid.algorithms.morphology as morphology
import numpy
from time import strftime
import os
import sys
import requests
from requests.auth import AuthBase
import urllib


def directory(path):
    if not os.path.isdir(path):
        err_msg = "path is not a directory (%s)"
        raise argparse.ArgumentTypeError(err_msg)
    return path


c = catmaid.connect()
pid = c.find_pid(title=None)

# parse command line options
parser = argparse.ArgumentParser()
parser.add_argument(
   '-a', '--annotation', type=str, nargs="+", required=False,
   help="Annotation(s) to be used to export nodes. [optional]")
parser.add_argument(
    '-u', '--union', action="store_true", required=False,
    help="Flag to export union of two or more annotations specified in -a "
         "option rather than default intersection. [optional]")
parser.add_argument(
   '-d', '--dest', type=str, required=False,
   help="Path to a destination directory. [optional]")
parser.add_argument(
    '-i', '--ignore', type=str, nargs="+", required=False,
    help="Ignore skeletons annotated with supplied argument(s). [optional]")
parser.add_argument(
    '-s', '--scale', type=str, nargs="+", required=False,
    help="Scaling factor to apply to outputs of each coordinate "
         "(format 'Sx Sy Sz'). Default is '1 1 1'. [optional]")
parser.add_argument(
    '-t', '--threshold', type=int, required=False,
    help="Minimum path length (integer in nm) required for skeleton "
         "to be exported. [optional]")
parser.add_argument(
    '-l', '--longest_length', required=False, action="store_true",
    help="Option flag to specify the export of the longest pathlength."
         "[Optional]")
parser.add_argument(
    '-r', '--radius', required=False, action='store_true',
    help="Option flag to specify the addition of node radius in exports."
         "[Optional]")
parser.add_argument(
    '-p', '--projection', required=False, action='store_true',
    help="Option flag to specify the export of the longest soma through "
         "projection tag. If no projection is found, "
         "the script will then find the longest length. [Optional]")
parser.add_argument(
    '-f', '--filesource', type=directory, required=False,
    help="Option flag to specify a filesource instead of a server source."
         "[Optional]")
opts = parser.parse_args()

annos = opts.annotation
annos_union = opts.union
dest_path = opts.dest
except_anno = opts.ignore
scale = opts.scale
threshold = opts.threshold
longest_length = opts.longest_length
node_radius = opts.radius
longest_projection = opts.projection
filesource = opts.filesource

if filesource is not None:
    src = catmaid.get_source(filesource)
    print "Setting source as {}".format(filesource)
else:
    src = catmaid.get_source(c)
if annos_union:
    print ("Starting Export of all skeletons with any of the "
           "following annotations: {}".format(annos))
else:
    print ("Starting Export of all skeletons with exactly "
           "these annotations: {}".format(annos))
if except_anno:
    print "Ignoring skeletons with annotation(s): {}".format(except_anno)
if threshold:
    print "Minimum length of longest skeleton path for export: {}".format(
        threshold)
if longest_length:
    print "Only exporting the longest pathlength"
if node_radius:
    print "Exporting nodes with node radius included"
if longest_projection:
    print "Exporting nodes along longest soma through projection tag"
# Set scale to default if None
if scale is None:
    scale = [1., 1., 1.]
# Ensure that 3 numbers have been passed in
if len(scale) != 3:
    raise Exception("Must pass through 3 numbers 'Sx Sy Sz' to scale exports")
else:
    # Set scale to float values of passed through values
    scale = numpy.array([float(scale[0]), float(scale[1]), float(scale[2])])
print "Scale: {}".format(scale)
# Find all annotation IDs for a project
print "Fetching all annotation IDs"
if c.server[-1] != '/':
    c.server += '/'
annos_link = '{}{}/annotations/'.format(c.server, pid)
all_annos = c.fetchJSON(annos_link) 

if annos is None:
    if os.environ["CATMAID_EXPORT_ANNOTATION"]:
        annotation = os.environ["CATMAID_EXPORT_ANNOTATION"]
        annos = [annotation][0].split(" ")
    else:
        raise Exception("Annotation must be set as the first argument or as "
                        "environment variable!")
print "Setting up Annotations for export"
if len(annos) == 1:
    annotation = annos[0]
    annotation_for_file = annotation.replace("_", "")
    anno_id = ([i[u'id'] for i in all_annos[u'annotations'] if
                i[u'name'] == unicode(annotation)])
if len(annos) > 1:
    anno_id = []
    for annotation in annos:
        a_id = ([i[u'id'] for i in all_annos[u'annotations'] if
                 i[u'name'] == unicode(annotation)])
        if len(a_id) == 0:
            raise Exception("Annotation '{}' does not have correspoding ID".format(annotation))
        anno_id.append(a_id[0])
    annotation_for_file = "".join(annos)

if dest_path:
    outfile = dest_path
else:
    outfile = ('../../results/exports/{}_130201zf142_ANNOT{}_dump_'
               'PHYScoord.txt'.format(strftime('%y%m%dT%H%M'),
                                      annotation_for_file))

print "Querying project for skeletons with anotation(s)"
if annos_union:
    anno_id = (", ".join(["%d"] * len(anno_id)) % tuple(anno_id))
    post = {'annotated_with[0]': '{}'.format(anno_id)}
else:
    post = {('annotated_with[%s]' % i): anno for i, anno in enumerate(anno_id)}

# Query the project for all skeletons that are annotated with the annotation ID
query_link = '{}{}/annotations/query-targets'.format(c.server, pid)
query = c.fetchJSON(query_link, post=post)
# Pull out the JSON from the query


query_json = query
if len(query_json[u'entities']) == 0:
    raise Exception("No Skeletons found with annotations: {}".format(annos))
# Create a list of all the skeleton_ids from the query
skel_ids = [i[u'skeleton_ids'] for i in query_json[u'entities']]
print ("Beginning export of skeletons")
with open(outfile, 'w') as f:
    for sid in skel_ids:
        # Create an exception checking variable and empty anno list
        skip_skel = 0
        skip_annos = []
        sid = sid[0]
        neuron = src.get_neuron(sid)
        # Check if neuron has enough nodes
        if threshold is not None:
            if morphology.longest_pathlength(neuron) < threshold:
                print ("EXPORT ERROR: Skipped skeleton {} because it is "
                       "shorter than {} nm".format(neuron.skeleton_id,
                                                   threshold))
                continue
        # Check neuron for one annotation to be excluded
        if except_anno is not None:
            if len(except_anno) > 1:
                for e in except_anno:
                    if any(n[0] == e for n in neuron.annotations):
                        skip_skel += 1
                        skip_annos.append(e)
            else:
                if any(n[0] == except_anno[0] for n in neuron.annotations):
                    print ("EXPORT ERROR: Excluding skeleton {} with "
                           "anno '{}'".format(
                            neuron.skeleton_id, except_anno[0]))
                    continue
        # Check if neuron had any annotations that are in excluded list
        if skip_skel > 0:
            print "EXPORT ERROR: Excluding skeleton {} with anno(s) {}".format(
                neuron.skeleton_id, skip_annos)
            continue
        if longest_projection:
            path = morphology.soma_through_projection_to_leaf(src,
                                                              neuron=neuron)
            if path is None:
                longest_length = True
            else:
                longest_length = False
        if longest_length:
            path = morphology.longest_node_pathlength(neuron)
        if not longest_projection and not longest_length:
            path = neuron.nodes
        if path == 0:
            continue
        for nid in path:
            if nid == neuron.root:
                parent = 'root'
            else:
                parent = neuron.dedges[nid][0]
            xpx, ypx, zpx = numpy.array([neuron.nodes[nid]['x'],
                                        neuron.nodes[nid]['y'],
                                        neuron.nodes[nid]['z']]) / scale
            if node_radius:
                nr = neuron.nodes[nid]['radius']
                f.write('{} {} {} {} {} {} {}\n'.format(sid, nid, str(parent),
                                                        xpx, ypx, int(zpx),
                                                        int(nr)))
            else:
                f.write('{} {} {} {} {} {}\n'.format(sid, nid, str(parent),
                                                     xpx, ypx, int(zpx)))
        print "Successfully exported skeleton: {}".format(neuron.skeleton_id)
