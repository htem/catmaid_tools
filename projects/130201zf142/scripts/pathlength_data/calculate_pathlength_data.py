#!/usr/bin/env python
'''
Determining pathlength data for all neurons in a source.
    Currently expects soma input from skelhassoma.json (generated dict using
        list comprehension of all neurons)
    Ideally expects a kalman smoothed filesource, such as
        produced by running smoothing as a script (preserving soma itentity)


'''
import argparse
import catmaid
import csv
import numpy
import json
import glob
import os
from itertools import combinations
from catmaid.algorithms.morphology import total_pathlength, path_length

conn = catmaid.connect()

filesource = '../../data/skeletons'

outd = '../../results/stats/'

filename = "PROJSTATS.txt"

nnodethres = 15  # only skels with more than nnodethres nodes are complete


def write_dictionary_txt(d, outdir, name):
    if not os.path.exists(outd):
        os.makedirs(outd)
    fn = os.path.join(outdir, name)
    with open(fn, 'w') as f:
        for k, v in d.items():
            f.write('{} {}\n'.format(k, v))


def directory(path):
    if not os.path.isdir(path):
        err_msg = "path is not a directory (%s)"
        raise argparse.ArgumentTypeError(err_msg)
    return path


def get_skels_with_anno(conn, source, annos):
    print "Fetching all annotation IDs"
    # pid = conn._pid
    pid = conn.find_pid(title=None)
    if conn.server[-1] != '/':
        conn.server += '/'
    annos_link = '{}{}/annotations/'.format(conn.server, pid)
    all_annos = conn.fetchJSON(annos_link)

    if annos is None:
        raise Exception("Annotation must be set as the first argument or as "
                        "environment variable!")
    if len(annos) == 1:
        annotation = annos[0]
        anno_id = ([i[u'id'] for i in all_annos[u'annotations'] if
                    i[u'name'] == unicode(annotation)])
    if len(annos) > 1:
        anno_id = []
        for annotation in annos:
            a_id = ([i[u'id'] for i in all_annos[u'annotations'] if
                     i[u'name'] == unicode(annotation)])
            if len(a_id) == 0:
                raise Exception("Annotation '{}' does not have correspoding"
                                " ID".format(annotation))
            anno_id.append(a_id[0])

    print "Querying project for skeletons with anotation(s)"
    post = {('annotated_with[%s]' % i): anno for i, anno in enumerate(anno_id)}

    # Query the project for skeletons that are annotated with the annotation ID
    query_link = '{}{}/annotations/query-targets'.format(conn.server, pid)
    query = conn.fetchJSON(query_link, post=post)
    # Pull out the JSON from the query

    query_json = query
    if len(query_json[u'entities']) == 0:
        raise Exception("No Skeletons found with "
                        "annotations: {}".format(annos))
    # Create a list of all the skeleton_ids from the query
    skel_ids = [i[u'skeleton_ids'] for i in query_json[u'entities']]
    return skel_ids


def collect_project_data(source, conn=None, skels_list=None, except_anno=None):
    if except_anno is not None:
        print "Excluding all skeletons with annotation(s): {}".format(
            except_anno)
    print "Collecting Project Data..."
    all_data = {}
    numskels = 0
    somareconstructed = 0
    max_somapathlengths = {}
    min_somapathlengths = {}
    mean_somapathlengths = {}
    median_somapathlengths = {}
    max_leafpathlengths = {}
    min_leafpathlengths = {}
    mean_leafpathlengths = {}
    median_leafpathlengths = {}
    hassoma = {}
    totalpaths = {}
    allsomapathlengths, allleafpathlengths = [], []
    s = catmaid.get_source(source)
    if skels_list is not None:
        skels = skels_list
    else:
        skels = s.skeleton_ids()
    for sid in skels:
        # Create empty variable for skipping a skel with x annotation
        skip_skel = 0
        if type(sid) == list:
            sid = sid[0]
        n = s.get_neuron(sid)
        if except_anno is not None:
            if len(except_anno) > 1:
                for e in except_anno:
                    if any(a[0] == e for a in n.annotations):
                        skip_skel += 1
            else:
                if any(a[0] == except_anno[0] for a in n.annotations):
                    continue
        # Skip this skeleton if it has any excluded annotations
        if skip_skel != 0:
            continue
        totalpaths[sid] = total_pathlength(n)
        if len(n.nodes.keys()) > nnodethres:
            numskels += 1
        if 'soma' in n.tags:
            hassoma[sid] = 1
        else:
            hassoma[sid] = 0
        if len(n.nodes) > 1:
            rootpathlengths = [path_length(n, n.root, leaf)
                               for leaf in n.leaves]
            if len(n.leaves) > 1:
                leafpathlengths = [path_length(n, leaf1, leaf2)
                                   for leaf1, leaf2 in combinations(
                                    n.leaves, 2)]
            else:
                leafpathlengths = rootpathlengths

            if hassoma[sid]:
                somareconstructed += 1
                max_somapathlengths[sid] = max(rootpathlengths)
                min_somapathlengths[sid] = min(rootpathlengths)
                mean_somapathlengths[sid] = numpy.mean(rootpathlengths)
                median_somapathlengths[sid] = numpy.median(rootpathlengths)
                allsomapathlengths.extend(rootpathlengths)
            allleafpathlengths.extend(leafpathlengths)
            max_leafpathlengths[sid] = max(leafpathlengths)
            min_leafpathlengths[sid] = min(leafpathlengths)
            mean_leafpathlengths[sid] = numpy.mean(leafpathlengths)
            median_leafpathlengths[sid] = numpy.median(leafpathlengths)
    project_pathlength = sum(totalpaths.values())
    max_pathlength = max(totalpaths.values())
    mean_pathlength = numpy.mean(totalpaths.values())
    min_pathlength = min(totalpaths.values())
    median_pathlength = numpy.median(totalpaths.values())
    project_somata = somareconstructed
    somapercent = float(project_somata)/float(numskels)
    projdata = {'length traced': project_pathlength,
                'number of somata': project_somata,
                'number of reconstructions': numskels,
                'percent with soma': somapercent,
                'max length traced': max_pathlength,
                'min length traced': min_pathlength,
                'mean length traced': mean_pathlength,
                'median length traced': median_pathlength,
                'soma to leaf max': max(allsomapathlengths),
                'soma to leaf min': min(allsomapathlengths),
                'soma to leaf median': numpy.median(allsomapathlengths),
                'soma to leaf mean': numpy.mean(allsomapathlengths),
                'total pathlength of neurons with a soma': sum(allsomapathlengths),
                'leaf to leaf max': max(allleafpathlengths),
                'leaf to leaf min': min(allleafpathlengths),
                'leaf to leaf median': numpy.median(allleafpathlengths),
                'leaf to leaf mean': numpy.mean(allleafpathlengths)}
    all_data['max_somapathlengths'] = max_somapathlengths
    all_data['min_somapathlengths'] = min_somapathlengths
    all_data['mean_somapathlengths'] = mean_somapathlengths
    all_data['median_somapathlengths'] = median_somapathlengths
    all_data['max_leafpathlengths'] = max_leafpathlengths
    all_data['min_leafpathlengths'] = min_leafpathlengths
    all_data['mean_leafpathlengths'] = mean_leafpathlengths
    all_data['median_leafpathlengths'] = median_leafpathlengths
    all_data['hassoma'] = hassoma
    all_data['totalpaths'] = totalpaths
    all_data['allsomapathlengths'] = allsomapathlengths
    all_data['allleafpathlengths'] = allleafpathlengths
    all_data['project_pathlength'] = project_pathlength
    all_data['somapercent'] = somapercent
    all_data['projdata'] = projdata
    print "Project Data Collected"
    return all_data


def write_output(skel_type, main_dir, data_dir, data,
                 annotation, except_anno):
    fn = '{}/{}_PROJSTATS.txt'.format(main_dir, skel_type)
    with open(fn, 'w') as f:
        f.write("Project Data for {}\n".format(skel_type))
        if annotation is not None:
            f.write("Annotation(s): {}\n".format(annotation))
        if except_anno is not None:
            f.write(
                "Exclude Skels with annotation(s): {}\n".format(except_anno))
        for k, v in sorted(data['projdata'].iteritems(),
                           key=lambda (k, v): (v, k)):
            f.write('{} {}\n'.format(k, v))
        # f.write("\n")
    fn = '{}/total_pathlengths.csv'.format(data_dir)
    with open(fn, 'w') as f:
        # Write out to separate csvs
        writer = csv.writer(f, delimiter=',')
        # writer.write("Objects with their Total Path Lengths\n")
        for k, v in sorted(data['totalpaths'].iteritems(),
                           key=lambda (k, v): (v, k)):
            writer.writerow((k, v))
    # f.write("\n")
    # f.write("Objects with their Max Leaf to Leaf Path Lengths\n")
    fn = '{}/max_leaf_to_leaf_pathlength.cvs'.format(data_dir)
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for k, v in sorted(data['max_leafpathlengths'].iteritems(),
                           key=lambda (k, v): (v, k)):
            writer.writerow((k, v))
    # f.write("\n")
    # f.write("Objects with their Min Leaf to Leaf Path Lengths\n")
    fn = '{}/min_leaf_to_leaf_pathlength.csv'.format(data_dir)
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for k, v in sorted(data['min_leafpathlengths'].iteritems(),
                           key=lambda (k, v): (v, k)):
            writer.writerow((k, v))
    # f.write("\n")
    # f.write("Objects with their Mean Leaf to Leaf Path Lengths\n")
    fn = '{}/mean_leaf_to_leaf_pathlength.csv'.format(data_dir)
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for k, v in sorted(data['mean_leafpathlengths'].iteritems(),
                           key=lambda (k, v): (v, )):
            writer.writerow((k, v))
    # f.write("\n")
    # f.write("Objects with their Median Leaf to Leaf Path Lengths\n")
    fn = '{}/median_leaf_to_leaf_pathlength.csv'.format(data_dir)
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for k, v in sorted(data['median_leafpathlengths'].iteritems(),
                           key=lambda (k, v): (v, k)):
            writer.writerow((k, v))
    # f.write("\n")
    # f.write("Objects with their Max Soma to Leaf Path Lengths\n")
    fn = '{}/max_soma_to_leaf_pathlength.csv'.format(data_dir)
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for k, v in sorted(data['max_somapathlengths'].iteritems(),
                           key=lambda (k, v): (v, k)):
            writer.writerow((k, v))
    # f.write("\n")
    # f.write("Objects with their Min Soma to Leaf Path Lengths\n")
    fn = '{}/min_soma_to_leaf_pathlength.csv'.format(data_dir)
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for k, v in sorted(data['min_somapathlengths'].iteritems(),
                           key=lambda (k, v): (v, k)):
            writer.writerow((k, v))
    # f.write("\n")
    # f.write("Objects with their Mean Soma to Leaf Path Lengths\n")
    fn = '{}/mean_soma_to_leaf_pathlength.csv'.format(data_dir)
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for k, v in sorted(data['mean_somapathlengths'].iteritems(),
                           key=lambda (k, v): (v, k)):
            writer.writerow((k, v))
    # f.write("\n")
    # f.write("Objects with their Median Soma to Leaf Path Lengths\n")
    fn = '{}/median_soma_to_leaf_pathlength.csv'.format(data_dir)
    with open(fn, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for k, v in sorted(data['median_somapathlengths'].iteritems(),
                           key=lambda (k, v): (v, k)):
            writer.writerow((k, v))


def collect_data(connection, source, skel_type, main_dir, data_dir,
                 only_anno, except_anno):
    if only_anno is not None:
        print ("Collecting pathlength data for skeletons wtih"
               " annotation(s): {}".format(only_anno))
        skels_list = get_skels_with_anno(connection, source, only_anno)
        all_data = collect_project_data(source, conn=connection,
                                        skels_list=skels_list,
                                        except_anno=except_anno)
    else:
        all_data = collect_project_data(source, except_anno=except_anno)
    write_output(skel_type, main_dir, data_dir,
                 all_data, only_anno, except_anno)


def check_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)


def find_dir(skel_type, output_dir):
    if 'kalman' in skel_type:
        if 'not_fixed' in skel_type:
            f = 'not_fixed'
        elif 'fixed' in skel_type:
            f = 'fixed'
        else:
            print "'Fixed' not found in skel type!"
            return 'skip'
        if 'unmasked' in skel_type:
            m = 'unmasked'
        elif 'masked' in skel_type:
            m = 'masked'
        else:
            print "'Masked' not found in skel_type!"
            return 'skip'
        kalman_dir = os.path.join(output_dir, 'smoothKALMAN/')
        check_dir(kalman_dir)
        fixed_dir = os.path.join(kalman_dir, f)
        check_dir(fixed_dir)
        masked_dir = os.path.join(fixed_dir, m)
        check_dir(masked_dir)
        return masked_dir
    elif 'gaussian' in skel_type:
        if 'not_fixed' in skel_type:
            f = 'not_fixed'
        elif 'fixed' in skel_type:
            f = 'fixed'
        else:
            print "'Fixed' not found in skel_type!"
            return 'skip'
        gaussian_dir = os.path.join(output_dir, 'smoothGAUSSIAN/')
        check_dir(gaussian_dir)
        fixed_dir = os.path.join(gaussian_dir, f)
        check_dir(fixed_dir)
        return fixed_dir
    elif 'skeleton' in skel_type:
        skel_dir = os.path.join(output_dir, 'unsmoothedSKELS')
        check_dir(skel_dir)
        return skel_dir


parser = argparse.ArgumentParser()
parser.add_argument(
    '-s', '--source', type=directory, required=False,
    help="A path to a directory containing jsons of the skeletons to be used."
    "[optional]")
parser.add_argument(
    '-d', '--dest', type=directory, required=False,
    help="A path to the desired output directory.[optional]")
parser.add_argument(
    '-a', '--annotation', type=str, nargs="+", required=False,
    help="Annotation(s) to be used in extracting pathlength data. [optional]")
parser.add_argument(
    '-e', '--exclude_anno', type=str, nargs="+", required=False,
    help="Annotation(s) to be excluded in pathlength data. [optional]")
opts = parser.parse_args()

annotation = opts.annotation
exclude_anno = opts.exclude_anno

if opts.source:
    source = os.path.abspath(opts.source)

if opts.dest:
    outd = os.path.abspath(opts.dest)

check_dir(outd)
if source[-1] != '/':
    source += '/*'
else:
    source += '*'
dirs = glob.glob(source)
for d in dirs:
    skel_type = d.split('/')[-1]
    data_dir = find_dir(skel_type, outd)
    if data_dir == 'skip':
        continue
    if 'skeletons' in skel_type:
        print "Collecting Stats for {}".format(skel_type)
        # filename = os.path.join(outd, (skel_type + '_PROJSTATS.txt'))
        collect_data(conn, d, skel_type, outd, data_dir,
                     annotation, exclude_anno)
    else:
        continue
