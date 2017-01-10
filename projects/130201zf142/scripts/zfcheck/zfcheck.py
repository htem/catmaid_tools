#!/usr/bin/env python
'''
This script parses a source using the catmaid library to validate tracing.
Assumes json key to google spreadsheet is in the working directory.
'''

import numpy
import catmaid
import os
import gspread
import json
import logging
import time
from operator import concat
from oauth2client.client import GoogleCredentials
from scipy.spatial import distance


def gen_url_and_message(err_string, err_list, url_list, neuron=None,
                        node_id=None, xyz=None):
    """
    Generates an link to a specified neuron or node and appends the link and
    error message to their respective lists.
    ----------
    Input:
    neuron = neruon id to be used in generating the url link
    err_string = and error message passed through
    err_list = a list to contain errors generated by the function
    url_list = a list to contain the urls generated by this function
    node_id = an optional node id to direct the link to a specific node
    ----------
    Output:
    Appends the link to the urls list
    Appends the error message to the errors list
    """
    stack_index = 0
    lowest_resolution = (0, 0)
    for i, stack_id in enumerate(c.find_stackids(c._pid)):
        x_res = c.stack_info()[stack_id]['resolution']['x']
        y_res = c.stack_info()[stack_id]['resolution']['y']
        res = (x_res, y_res)
        if res > lowest_resolution:
            lowest_resolution = res
            stack_index = i
    if xyz is not None:
        link = src._skel_source.openURL(x=xyz[0], y=xyz[1], z=xyz[2],
                                        zoom=3, stack_index=stack_index)
    elif node_id:
        link = src._skel_source.openURL(neuron=neuron, zoom=-2, nodeID=node_id,
                                        stack_index=stack_index)
    else:
        link = src._skel_source.openURL(neuron=neuron, zoom=-2,
                                        stack_index=stack_index)
    err_list.append(err_string)
    url_list.append(link)


def check_root_labels(neuron):
    """
    Takes a neuron id and iterates through all possible root labels to
    ensure correct labeling.
    ----------
    Input:
    neuron = a neuron id, usually generated from list of all skeleton_ids
    ----------
    Output:
    Creates a list of errors and urls with the appropriate error messages and
    url links to neurons that do not have correct root labels.
    """
    local_errors = []
    local_urls = []
    root_labels = neuron.nodes[neuron.root]['labels']
    if len(root_labels) < 1:
        errstr = ("ROOT ERROR: {} {} has "
                  "untagged root node".format(neuron.name,
                                              str(neuron.skeleton_id)))
        gen_url_and_message(errstr, local_errors, local_urls, neuron=neuron)
    elif (('soma' not in root_labels) and
          ('root_myelinated' not in root_labels) and
          ('myelinated' not in root_labels) and
          ('unmyelinated' not in root_labels) and
          ('root_unmyelinated' not in root_labels)):
        if 'soma' in neuron.tags:
            errstr = ("ROOT ERROR: {} {} soma is "
                      "not root!".format(neuron.name, neuron.skeleton_id))
            gen_url_and_message(errstr, local_errors, local_urls,
                                neuron=neuron)
        else:
            errstr = ("ROOT ERROR: {} {} does not have "
                      "expected root node tags".format(neuron.name,
                                                       neuron.skeleton_id))
            gen_url_and_message(errstr, local_errors, local_urls,
                                neuron=neuron)
    elif (('soma' in root_labels) and
          (neuron.nodes[neuron.root]['radius'] <= 0)):
        errstr = ("ROOT ERROR: {} {} soma "
                  "has no radius!".format(neuron.name, neuron.skeleton_id))
        gen_url_and_message(errstr, local_errors, local_urls, neuron=neuron)
    elif ('soma' in root_labels) and ('projection' not in neuron.tags):
        errstr = ("ROOT ERROR: {} {} neuron has soma, but no "
                  "projection tag!".format(neuron.name, neuron.skeleton_id))
        gen_url_and_message(errstr, local_errors, local_urls, neuron=neuron)
    elif (('root_unmyleinated' in neuron.tags) and
            ('root_myelinated' in neuron.tags)):
        errstr = ("ROOT ERROR: {} {} has a root_unmyelinated tag and a "
                  "root_myelinated tag!").format(neuron.name,
                                                 neuron.skeleton_id)
        gen_url_and_message(errstr, local_errors, local_urls, neuron=neuron)
    elif (('root_unmyelinated' in neuron.tags) and
            ('root_unmyelinated' not in root_labels)):
        node = neuron.tags['root_unmyelinated'][0]
        errstr = ("ROOT ERROR: {} {} has root_unmyelinated tag that is not "
                  "the root!".format(neuron.name, neuron.skeleton_id))
        gen_url_and_message(errstr, local_errors, local_urls,
                            neuron=neuron, node_id=node)
    elif (('root_myelinated' in neuron.tags) and
            ('root_myelinated' not in root_labels)):
        node = neuron.tags['root_myelinated'][0]
        errstr = ("ROOT ERROR: {} {} has root_unmyelinated tag that is not "
                  "the root!".format(neuron.name, neuron.skeleton_id))
        gen_url_and_message(errstr, local_errors, local_urls,
                            neuron=neuron, node_id=node)
    return local_errors, local_urls


def check_leaf_tags(neuron):
    local_errors = []
    local_urls = []
    correct_leaf_labels = ['TODO', 'ends']
    for leaf in neuron.leaves:
        l = leaf
        leaf_labels = neuron.nodes[l]['labels']
        if len(leaf_labels) < 1:
            errstr = ("LEAF NODE ERROR: {} {} has leaf node {} "
                      "that is untagged!".format(neuron.name,
                                                 neuron.skeleton_id, l))
            gen_url_and_message(errstr,
                                local_errors,
                                local_urls,
                                neuron=neuron,
                                node_id=l)
        else:
            for label in leaf_labels:
                if label not in correct_leaf_labels:
                    errstr = ("LEAF NODE ERROR: {} {} has leaf node {} "
                              "that has an incorrect tag {}".format(
                                neuron.name, neuron.skeleton_id, l, label))
    return local_errors, local_urls


def check_for_loop(neuron):
    """
    Takes a neuron id and iterates through all nodes to check for instances of
    looping nodes.
    ----------
    Input:
    neuron = a neuron id, usually generated from list of all skeleton_ids
    ----------
    Output:
    Creates a list of errors and urls with the appropriate error messages and
    url links to neurons that have cyclical nodes.
    """
    local_errors = []
    local_urls = []
    for node, ned in enumerate(neuron.dgraph.edge):
        if ned != neuron.root:
            if len(ned) < (int(neuron.dgraph.degree(ned)) - 1):
                errstr = ("LOOP ERROR: {} {} has node {} which is "
                          "cyclic!".format(neuron.name,
                                           neuron.skeleton_id, ned))
                gen_url_and_message(errstr,
                                    local_errors,
                                    local_urls,
                                    neuron=neuron,
                                    node_id=ned)
    return local_errors, local_urls


def incorrect_tags(neuron, correct_tags):
    """
    Takes a neuron id and iterates through all node tags and checks them
    against a known list of proper tags, flagging any that are not in the list
    of known tags.
    ----------
    Input:
    neuron = a neuron id, usually generated from list of all skeleton_ids
    correct_tags = a list of tags that are approved for use in tracing
    ----------
    Output:
    Creates a list of errors and urls with the appropriate error messages and
    url links to nodes that do not have approved tags.
    """
    local_errors = []
    local_urls = []
    for tag in neuron.tags:
        if tag not in correct_tags:
            for nid in neuron.tags[tag]:
                errstr = ("TAG ERROR: {} {} has unknown tag {} at "
                          "node {}".format(neuron.name, neuron.skeleton_id,
                                           tag, nid))
                gen_url_and_message(errstr,
                                    local_errors,
                                    local_urls,
                                    neuron=neuron,
                                    node_id=nid)
        if tag == 'soma':
            if len(neuron.tags['soma']) > 1:
                errstr = "TAG ERROR: {} {} has two somata!".format(
                    neuron.name, neuron.skeleton_id)
                gen_url_and_message(errstr, local_errors, local_urls,
                                    neuron=neuron)
        if tag == 'root_unmyelinated':
            if len(neuron.tags['root_unmyelinated']) > 1:
                errstr = ("TAG ERROR: {} {} has more than one "
                          "root_unmyelinated tag!".format(neuron.name,
                                                          neuron.skeleton_id))
                gen_url_and_message(errstr, local_errors, local_urls,
                                    neuron=neuron)
        if tag == 'root_myelinated':
            if len(neuron.tags['root_myelinated']) > 1:
                errstr = ("TAG ERROR: {} {} has more than one root_myelinated "
                          "tag!".format(neuron.name, neuron.skeleton_id))
                gen_url_and_message(errstr, local_errors, local_urls,
                                    neuron=neuron)
        if tag == 'projection':
            if len(neuron.tags['projection']) > 1:
                errstr = ("TAG ERROR: {} {} has more than one projection "
                          "tag!".format(neuron.name, neuron.skeleton_id))
                gen_url_and_message(errstr, local_errors, local_urls,
                                    neuron=neuron)
        if tag == 'axon':
            if len(neuron.tags['axon']) > 1:
                errstr = ("TAG ERROR: {} {} has more than one axon "
                          "tag!".format(neuron.name, neuron.skeleton_id))
                gen_url_and_message(errstr, local_errors, local_urls,
                                    neuron=neuron)
        if tag == 'TODO':
            for nid in neuron.tags[tag]:
                if nid not in neuron.leaves:
                    errstr = ("TAG ERROR: {} {} has TODO tag at {} node "
                              "that is not a leaf node!".format(
                                neuron.name, neuron.skeleton_id, nid))
                    gen_url_and_message(errstr,
                                        local_errors,
                                        local_urls,
                                        neuron=neuron,
                                        node_id=nid)
    return local_errors, local_urls


def check_max_node_distance(neuron, section_counter, error_counter):
    """
    Takes a neuron id and iterates through all nodes, creating an error
    message if a node is greater than 2 um from its parent node.
    ----------
    Input:
    neuron = a neuron id, usually generated from list of all skeleton_ids
    ----------
    Output:
    Creates a list of errors and urls with the appropriate error messages and
    url links to nodes that are greater than 2 um from its parent node.
    """
    local_errors = []
    local_urls = []
    for node in neuron.nodes:
        try:
            parent = neuron.dedges[node][0]
        except:
            continue
        a = (numpy.array([neuron.nodes[node]['x'], neuron.nodes[node]['y'],
             neuron.nodes[node]['z']]))
        b = (numpy.array([neuron.nodes[parent]['x'],
             neuron.nodes[parent]['y'], neuron.nodes[parent]['z']]))
        dist = ((numpy.linalg.norm(a-b)) / 1000)
        z_index = (neuron.nodes[node]['z'] / 60)
        try:
            section_counter[z_index] += 1
        except KeyError:
            section_counter[z_index] = 1
        if 'soma' in neuron.tags:
            if int(neuron.tags['soma'][0]) == int(node):
                continue
            if int(neuron.tags['soma'][0]) == int(parent) and dist <= 6.5:
                continue
        if 'damage' in neuron.tags:
            if int(neuron.tags['damage'][0]) == int(node):
                continue
            if int(neuron.tags['damage'][0]) == int(parent):
                continue
        if dist >= 1.5:
            # Check Distance of Parent
            try:
                parents_parent = neuron.dedges[parent][0]
                c = (numpy.array([neuron.nodes[parents_parent]['x'],
                     neuron.nodes[parents_parent]['y'],
                     neuron.nodes[parents_parent]['z']]))
                parent_dist = ((numpy.linalg.norm(b-c)) / 1000)
            except:
                parent_dist = 0
            if parent_dist >= 1.5:
                if 'soma' in neuron.tags:
                    if int(neuron.tags['soma'][0]) == int(parents_parent):
                        pass
                    else:
                        continue
                else:
                    continue
            errstr = ("DISTANCE ERROR: {0} ({1}) node {2} is "
                      "{3:.1f}um from parent [z {4}]".format(
                       neuron.name, int(neuron.skeleton_id),
                       int(node), float(dist), int(z_index)))
            gen_url_and_message(errstr,
                                local_errors,
                                local_urls,
                                neuron=neuron,
                                node_id=node)
            try:
                error_counter[z_index] += 1
            except KeyError:
                error_counter[z_index] = 1
            section_locator[z_index] = a
    return local_errors, local_urls


def nodepos(node):
    """ Takes a node object as input and outputs an array of the (X, Y, Z)
        position"""
    return numpy.array([node['x'], node['y'], node['z']])


def all_nid_and_xyz(neuron):
    """ Takes a neuron as input and returns an array of all node ids along with
        an array of all XYZ positions of those nodes"""
    all_nid, xyz = [], []
    for nid in neuron.nodes.keys():
        nidxyz = nodepos(neuron.nodes[nid])
        all_nid.append(nid)
        xyz.append(nidxyz)
    return numpy.array(all_nid), numpy.array(xyz)


def check_min_node_distance(neuron):
    """ Takes a neuron as input and generates arrays of all nodes and xyz
        positions, then checks for neurons with less than 300 nodes, along
        with a check for any nodes that are too close to another node in then
        neuron"""
    local_errors, local_urls = [], []
    if [u'short'] in neuron.annotations:
        return local_errors, local_urls
    all_nid, xyz = all_nid_and_xyz(neuron)
    if len(all_nid) == 1:
        errstr = ("NEURON ERROR: {} {} only has one node!".format(
                    neuron.name, neuron.skeleton_id))
        gen_url_and_message(errstr,
                            local_errors,
                            local_urls,
                            neuron=neuron)
    if len(all_nid) > 1 and len(all_nid) < 300:
        errstr = ("NEURON ERROR: {} {} has less than 300 nodes.".format(
                    neuron.name, neuron.skeleton_id))
        gen_url_and_message(errstr,
                            local_errors,
                            local_urls,
                            neuron=neuron)
    if len(all_nid) > 1:
        dists = distance.pdist(xyz, 'euclidean')
        distance_relate = distance.squareform(dists)
        for i, n in enumerate(distance_relate):
            if any(0 < a < 50 for a in n):
                node = all_nid[i]
                z_index = (xyz[i][2]) / 60
                errstr = ("PROXIMITY ERROR: {} {} has node {} that closer "
                          "than 50nm to another node on Z {}.".format(
                            neuron.name, neuron.skeleton_id,
                            node, int(z_index)))
                gen_url_and_message(errstr,
                                    local_errors,
                                    local_urls,
                                    neuron=neuron,
                                    node_id=node)
    return local_errors, local_urls


def check_section_error_percentage(section_counter, error_counter):
    local_errors = []
    local_urls = []
    for index in section_counter:
        try:
            error_counter[index]
        except KeyError:
            continue
        total_sections = section_counter[index]
        errors = error_counter[index]
        perc_error = int(float(errors) / float(total_sections) * 100)
        if perc_error >= 5:
            errstr = ("SECTION ERROR: Section {} has {} percent "
                      "errors!".format(int(index), perc_error))
            xyz = section_locator[index]
            gen_url_and_message(errstr, local_errors, local_urls,
                                xyz=xyz)
    return local_errors, local_urls


def reorder_distance_list(error_list, url_list):
    new_error_list, new_url_list = [], []
    distances = []
    # for i, e in enumerate(error_list):
    #    if "DISTANCE ERROR" in e:
    #        dist = [int(s) for s in e.split() if s.isdigit()][2]
    #        distances.append((dist, i))
    for i, e in enumerate(error_list):
        dist = [s.split('um')[0] for s in e.split() if 'um' in s][0]
        distances.append((dist, i))
    distances.sort()
    for d in reversed(distances):
        errstr = error_list[d[1]]
        url = url_list[d[1]]
        new_error_list.append(errstr)
        new_url_list.append(url)
    return new_error_list, new_url_list


def update_cell(gc, w, letter, cell_number, d):
    """
    Takes a letter and number to specifiy cell, then adds the data into that
    cell
    ----------
    Input:
    letter = a capitalized letter to indicate column
    cell_number = the row number
    d = the values to be placed in the specified cell
    ----------
    Output:
    Adds a value (d) into the cell specified by column(letter)
    and row(cell_number)
    """
    if gc.auth.access_token_expired:
        gc.login()
        # checks if access token is valid, and reestablishes conn if invalid
    w.update_acell(letter+cell_number, d)


def update_spreadsheet_with_master_errors(errors, urls):
    # Open the Google spreadsheet to push data to
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = GoogleCredentials.get_application_default()
    credentials = credentials.create_scoped(
                                            ['https://'
                                             'spreadsheets.google.com/feeds'])
    date = time.strftime("%y%m%d")
    gc = gspread.authorize(credentials)
    # Load in google spreadsheet key from env variables
    try:
        var = os.environ['GOOGLE_SPREADSHEET_KEY']
    except KeyError:
        raise Exception("Google spreadsheet key not set as an environment "
                        "variable. Cannot access spreadsheet")
    sh = gc.open_by_key(var)
    sheet_list = sh.worksheets()
    # Create a new worksheet for today

    # If zfcheck is being run more than once daily:
    # date = time.strftime("%y%m%dT%H%M")
    try:
        w = sh.add_worksheet(title=date, rows=str(len(errors) + 1), cols = "2")
    except:
        date = time.strftime("%y%m%dT%H%M")
        w = sh.add_worksheet(title=date, rows=str(len(errors) + 1), cols = "2")

    # Update Header/initiate counters
    w.update_acell('A1', 'Errors')
    w.update_acell('B1', 'Links')
    cell_counter = 2

    # Loop through Errors and push each entry to the google spreadsheet
    for idx, line in enumerate(errors):
        cell = str(cell_counter)
        error = errors[idx]
        url = urls[idx]
        try:
            update_cell(gc, w, 'A', cell, error)
        except:
            print ("Cannot access Google Drive. Retry one more time "
                   "in 10 seconds to access it.")
            time.sleep(10)
            update_cell(gc, w, 'A', cell, error)
        try:
            update_cell(gc, w, 'B', cell, url)
        except:
            print ("Cannot access Google Drive. Retry one more time "
                   "in 10 seconds to access it.")
            time.sleep(10)
            update_cell(gc, w, 'B', cell, url)
        cell_counter += 1


# a list of all known tags used in tracing
correct_tags = [
                'TODO', 'TODO branch',
                'soma',
                'myelinated', 'unmyelinated',
                'root_myelinated', 'root_unmyelinated',
                'ends', 'damage', 'axon', 'projection',
                'backbone',
		]

# connect to catmaid and get the source from the connection
# default to using environmental variables
c = catmaid.connect()
src = catmaid.get_source(c, ignore_none_skeletons=True)


# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# creates two lists, one for error messages and one for url links
master_errors = []
master_urls = []

root_errors, root_urls = [], []
leaf_tag_errors, leaf_tag_urls = [], []
loop_errors, loop_urls = [], []
incorrect_tag_errors, incorrect_tag_urls = [], []
max_distance_errors, max_distance_urls = [], []
min_distance_errors, min_distance_urls = [], []
section_errors, section_urls = [], []
neuron_errors, neuron_urls = [], []

total = len(src.skeleton_ids())
section_counter = {}
section_error_counter = {}
section_locator = {}
# iterates through all skeletons in the catmaid database
# takes the neuron id from the skeletons and calls the error checking functions
# adds the error messages and url links into the proper list


for i, neu in enumerate(src.all_neurons()):
        names = []
        if not any([('blacklist' in anno) for anno in neu.annotations]):
            if len(neu.annotations) < 1:
                errstr = "NEURON ERROR: {} {} is not annotated".format(
                            neu.name, neu.skeleton_id)
                gen_url_and_message(errstr, neuron_errors, neuron_urls,
                                    neuron=neu)
            if neu.name in names:
                errstr = ("NEURON ERROR: {} {} has the same name '{}' as "
                          "another neuron!".format(neu.name, neu.skeleton_id,
                                                   neu.name))
                gen_url_and_message(errstr, neuron_errors, neuron_urls,
                                    neuron=neu)
            else:
                names.append(neu.name)
            # Check neuron for root label errors
            root_errors, root_urls = map(
                concat, [root_errors, root_urls], list(check_root_labels(neu)))
            # Check neuron for looping errors
            loop_errors, loop_urls = map(
                concat, [loop_errors, loop_urls], list(check_for_loop(neu)))
            # Check neuron for distance errors
            max_distance_errors, max_distance_urls = map(
                concat, [max_distance_errors, max_distance_urls],
                list(check_max_node_distance(
                    neu, section_counter, section_error_counter)))
            # Check neuron for incorrect tags
            incorrect_tag_errors, incorrect_tag_urls = map(
                concat, [incorrect_tag_errors, incorrect_tag_urls], list(
                    incorrect_tags(neu, correct_tags)))
            # Check neuron for leaf tag errors
            leaf_tag_errors, leaf_tag_urls = map(
                concat, [leaf_tag_errors, leaf_tag_urls], list(
                    check_leaf_tags(neu)))
            # Check neuron for proximity errors
            min_distance_errors, min_distance_urls = map(
                concat, [min_distance_errors, min_distance_urls], list(
                    check_min_node_distance(neu)))

        if not (i % 1000):
            percent = int((float(i) / float(total)) * 100)
            logging.info("Error Checking {} percent finished".format(percent))

logging.info("Checking Section Errors")

section_errors, section_urls = map(
    concat, [section_errors, section_urls],
    list(check_section_error_percentage(section_counter,
                                        section_error_counter)))
logging.info("Rearranging Distance Errors")

new_dist_errors, new_dist_urls = reorder_distance_list(max_distance_errors,
                                                       max_distance_urls)

logging.info("Creating Master Lists")


master_errors.extend(section_errors)
master_urls.extend(section_urls)
master_errors.extend(new_dist_errors)
master_urls.extend(new_dist_urls)
master_errors.extend(min_distance_errors)
master_urls.extend(min_distance_urls)
master_errors.extend(root_errors)
master_urls.extend(root_urls)
master_errors.extend(incorrect_tag_errors)
master_urls.extend(incorrect_tag_urls)
master_errors.extend(neuron_errors)
master_urls.extend(neuron_urls)
master_errors.extend(leaf_tag_errors)
master_urls.extend(leaf_tag_urls)
master_errors.extend(loop_errors)
master_urls.extend(loop_urls)


update_spreadsheet_with_master_errors(master_errors, master_urls)
