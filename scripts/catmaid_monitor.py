#!/usr/bin/env python

import argparse
import datetime
import sys
import time
import json
import os

import catmaid


parser = argparse.ArgumentParser()
parser.add_argument("-l", "--location",
                    help="place you want to store the skeleton source folder and problem viewer page. need to add / at the end. default is setting to your current directory",
                    default='')
parser.add_argument("-c", "--cache", help="cache or not when getting skeleton source",
                    default=False)
parser.add_argument("-s", "--server", help="server for connecting catmaid",
                    default=None)
parser.add_argument("-u", "--username", help="username for connectiing catmaid",
                    default=None)
parser.add_argument("-a", "--authname", help="authname for connecting catmaid",
                    default=None)
parser.add_argument("-p", "--password", help="password for connecting catmaid",
                    default=None)
parser.add_argument("-ct", "--correct_tags",
                    help="text file that stores all the correct tags, each line of the file should only contains one tag", default=None)
parser.add_argument("-tt", "--termination_tags",
                    help="text file that stores all the termination tags, each line of the file should only contains one tag", default=None)
opts = parser.parse_args()


skeleton_repo = '{}skeletons'.format(opts.location)

if opts.correct_tags is None:
    correct_tags = [
        'soma', 'inhibitory', 'inhibitory?', 'excitatory', 'excitatory?',
        'termination(axon trunk)', 'root', 'soma',
        'axon', 'l5_apical', 'asymmetric', 'symmetric',
        'presynaptic', 'postsynaptic', 'myelinated', 'todo',
        'todo_postsynaptic', 'todo_presynaptic', 'unmyelinated',
        'uncertain end', 'uncertain continuation', 'axon',
        'termination (lost in biology)',
        'termination (lost due to missing data)',
        'termination (biological)',
        'termination (axon trunk)',
        'basal dendrite',
        'termination (edge of series)',
        'continued by reviewer',
        'continued by second reviewer',
        'continued by third reviewer',
        'continued by fourth reviewer',
        'basal dendrite', 'apical dendrite',
        'termination (lateral edge of series)',
        'todo_postsynaptic(on synapse nodes)',
        'layer1', 'stopped tracing', 'uncertain',
        'split-spine axon frag', 'dendrite'
    ]
else:
    f = open(opts.correct_tags, 'r')
    correct_tags = f.read().splitlines()
    f.close()
    if len(correct_tags) == 0:
        raise ValueError("correct_tags file cant be empty")


if opts.termination_tags is None:
    termination_tags = [
        'termination (biological)', 'termination (edge of series)',
        'termination (lost in biology)',
        'termination (lost due to missing data)',
        'termination (lateral edge of series)',
        'presynaptic', 'postsynaptic', 'todo',
        'termination (axon trunk)', 'layer1', 'stopped tracing'
    ]
else:
    f = open(opts.termination_tags, 'r')
    termination_tags = f.read().splitlines()
    if len(termination_tags) == 0:
        raise ValueError("termination_tags file cant be empty")


def connect_to_catmaid():
    return catmaid.connect(server=opts.server, user=opts.username,
                           password=opts.password, project=opts.authname)


def try_to_fetch_skeleton_by_id(source, sid, max_retries=2):
    tries = 0
    errors = []
    while tries < max_retries:
        try:
            skel = source.get_skeleton(sid)
            return skel
        except Exception as e:
            errors.append(e)
        tries += 1
    return errors


def get_filename_for_skeleton_id(sid):
    if not os.path.exists(skeleton_repo):
        os.makedirs(skeleton_repo)
    return os.path.join(skeleton_repo, 'skel{}.json'.format(sid))


def fetch_skeletons_pc(source):
    skel_ids = source.skeleton_ids()
    fetched = []
    for sid in skel_ids:
        with open(get_filename_for_skeleton_id(sid), 'w') as f:
            skel = try_to_fetch_skeleton_by_id(source, sid)
            if isinstance(skel, dict):
                json.dump(skel, f)
                fetched.append(sid)
                f.close()
            else:
                print("Failed to fetch {} with {}".format(sid, skel))
    return fetched


def printTimeDetails(si, n, st):
    si = si + 1
    dt = time.time() - st
    sys.stdout.write(
        str(round(float(si) / n * 100, 3)) +
        '% complete | Elapsed: ' +
        str(datetime.timedelta(seconds=round(dt))) +
        ' | ETA: ' +
        str(datetime.timedelta(seconds=(round(dt * n/float(si))
            - round(dt)))) +
        '          \r')
    sys.stdout.flush()


def check_tags(sid, neuron, problems, connection):
    '''helper, check if this neuron is tagged correctly'''
    neuron_tags = neuron.tags.keys()
    problem_tags = {}
    for tag in neuron_tags:
        if tag not in correct_tags:
            problem_tags[tag] = neuron.tags.get(tag)
    # BJG: moved this outside to loop so that it is not set every iterration
    if len(problem_tags):
        problem_strings = []
        for tag in problem_tags.keys():
            problem_strings.append(
                'incorrect tag [%s] on nodes [%s]' % (tag, problem_tags[tag]))
        problems['Check_tags'] = {}
        problems['Check_tags']['string'] = '; '.join(problem_strings)
        problems['Check_tags']['ids'] = {}
        for tag in problem_tags.keys():
            node_id_list = problem_tags[tag]
            for node_id in node_id_list:
                problems['Check_tags']['ids'][node_id] = [tag, connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]
    qmark_tags = {}
    for tag in neuron.tags.keys():
        if '?' in tag:
            qmark_tags[tag] = neuron.tags.get(tag)
    if len(qmark_tags):
        problem_strings_qmark = []
        for tag in qmark_tags.keys():
            problem_strings_qmark.append(
                'question mark tag [%s] on nodes [%s]' % (tag, qmark_tags[tag]))
        problems['Check_question_mark_tags'] = {}
        problems['Check_question_mark_tags']['string'] = '; '.join(problem_strings_qmark)
        problems['Check_question_mark_tags']['ids'] = {}
        for tag in qmark_tags.keys():
            node_id_list = qmark_tags[tag]
            for node_id in node_id_list:
                problems['Check_question_mark_tags']['ids'][node_id] = [tag, connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_soma(sid, neuron, problems, connection):
    '''helper, check if this neuron has more than one soma'''
    if neuron.tags.get('soma') is not None:
        soma_length = len(neuron.tags.get('soma'))
        if soma_length > 1:
            # include both soma ids
            problems['check_soma'] = {}
            problems['check_soma']['string'] = 'more than one node [%s] labeled soma' % (neuron.tags['soma'], )
            problems['check_soma']['ids'] = {}
            for node_id in neuron.tags.get('soma'):
                problems['check_soma']['ids'][node_id] = ['multiple soma', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_axon(sid, neuron, problems, connection):
    '''helper, check if this neuron has more than one axon'''
    axon_length = len(neuron.axons)
    if axon_length > 1:
        # include axon starting node ids
        problems['Check_axon'] = {}
        problems['Check_axon']['string'] = 'more than one node [%s] labeled axon' % (neuron.tags['axon'], )
        problems['Check_axon']['ids'] = {}
        for node_id in neuron.tags['axon']:
            problems['Check_axon']['ids'][node_id] = ['multiple axon', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_root_soma(sid, neuron, problems, connection):
    '''helper, check if the root node is at the soma
    if there is a soma tag in the neuron'''
    root_id = neuron.root
    if 'soma' in neuron.tags:
        if len(neuron.tags.get('soma')) == 1:
            soma_id = neuron.soma
            if root_id != soma_id:
                # include root and soma ids
                problems['Check_root_soma'] = {}
                problems['Check_root_soma']['string'] = 'root node [%s] and soma node [%s] differ' % (root_id, soma_id)
                problems['Check_root_soma']['ids'] = {}
                for node_id in [root_id, soma_id]:
                    problems['Check_root_soma']['ids'][node_id] = ['soma not on root', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_root_status(sid, neuron, problems, connection):
    '''helper, check if there is only one 'excitatory' or'inhibitory'
    tag at the root node'''
    root_id = neuron.root
    root_labels = neuron.skeleton['vertices'][root_id]['labels']
    if 'excitatory' in root_labels:
        if 'inhibitory' in root_labels:
            problems['Check_root_status'] = {}
            problems['Check_root_status']['string'] = \
                'root cant have both excitatory and inhibitory tags'
            problems['Check_root_status']['ids'] = {}
            problems['Check_root_status']['ids'][root_id] = ['root', connection.openURL(neuron=neuron, skID=sid, nodeID=int(root_id))]
    elif 'inhibitory' in root_labels:
        if 'excitatory' in root_labels:
            problems['Check_root_status'] = {}
            problems['Check_root_status']['string'] = \
                'root cant have both excitatory and inhibitory tags'
            problems['Check_root_status']['ids'] = {}
            problems['Check_root_status']['ids'][root_id] = ['root', connection.openURL(neuron=neuron, skID=sid, nodeID=int(root_id))]
    else:
        if 'soma' in root_labels:
            problems['Check_root_status'] = {}
            problems['Check_root_status']['string'] = \
                'need to tag root node as excitatory or inhibitory'
            problems['Check_root_status']['ids'] = {}
            problems['Check_root_status']['ids'][root_id] = ['root', connection.openURL(neuron=neuron, skID=sid, nodeID=int(root_id))]


def check_leaf(sid, neuron, problems, connection):
    '''helper, check if there are unlabled terminations/leaf-nodes'''
    leaves = neuron.leaves
    problem_leaves = []
    root_id = neuron.root
    root_labels = neuron.skeleton['vertices'][root_id]['labels']
    if 'inhibitory' not in root_labels:
        for leaf in leaves:
            if not any([l in termination_tags for l in neuron.skeleton['vertices'][leaf]['labels']]):
                problem_leaves.append(leaf)
        if len(problem_leaves):
            str_problem = 'unlabeled leaf nodes : ' + str(problem_leaves)
            problems['Check_leaf'] = {}
            problems['Check_leaf']['string'] = str_problem
            problems['Check_leaf']['ids'] = {}
            for node_id in problem_leaves:
                problems['Check_leaf']['ids'][node_id] = ['unlabeled leaf', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_synaptic_tags(sid, neuron, problems, connection):
    '''helper, check if every presynaptic tag and postsynaptic tag has only
    symmetric or asymmertic tag, but not both'''
    synaptic_nodes = neuron.tags.get('presynaptic', []) + \
        neuron.tags.get('postsynaptic', [])
    problem_synaptic_tags = {}
    for node in synaptic_nodes:
        node_labels = neuron.skeleton['vertices'][node]['labels']
        if 'symmetric' in node_labels:
            if 'asymmetric' in node_labels:
                problem_synaptic_tags[node] = \
                    'cant have both symmetric and asymmetric tags'
        elif 'asymmetric' in node_labels:
            if 'symmetric' in node_labels:
                problem_synaptic_tags[node] = \
                    'cant have both symmetric and asymmetric tags'
        else:
            problem_synaptic_tags[node] = 'missing symmetric or asymmetric tag'
    if len(problem_synaptic_tags):
        problem_strings = []
        for key in problem_synaptic_tags:
            problem_strings.append('node %s %s' % (key, problem_synaptic_tags[key]))
        problems['Check_synaptic_tags'] = {}
        problems['Check_synaptic_tags']['string'] = '; '.join(problem_strings)
        problems['Check_synaptic_tags']['ids'] = {}
        for node_id in problem_synaptic_tags.keys():
            problems['Check_synaptic_tags']['ids'][node_id] = ['synaptic_tag', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_is_finished(sid, neuron, problems, connection):
    '''helper, check if a neuron is finished '''
    tags = neuron.tags.keys()
    root_id = neuron.root
    root_labels = neuron.skeleton['vertices'][root_id]['labels']
    if 'excitatory' in root_labels:
        if 'todo' in tags:
            problems['Check_is_finished'] = {}
            problems['Check_is_finished']['string'] = 'this neuron isnt finished (has todo tag)'
            problems['Check_is_finished']['ids'] = {}
            for node_id in neuron.tags.get('todo'):
                problems['Check_is_finished']['ids'][node_id] = ['not_finished', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_gaps(sid, neuron, problems, connection):
    ''' helper, check if there is gap in the neuron'''
    edges = neuron.dgraph.edges()
    # dedges are ordered by [child][parent]
    # dedges = neuron.dedges
    dedges = neuron.skeleton['connectivity']
    root_id = neuron.root
    problem_gaps = []
    for edge in edges:
        pid = edge[0]
        # if this isn't the root, and it has no parent
        if pid != root_id and pid not in dedges:
            print(pid)
            # than we have a gap
            problem_gaps.append(pid)
    if len(problem_gaps):
        problems['Check_gaps'] = {}
        problems['Check_gaps']['string'] = 'gaps at %s' % str(problem_gaps)
        problems['Check_gaps']['ids'] = {}
        for node_id in problem_gaps:
            problems['Check_gaps']['ids'][node_id] = ['gap', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_deep_layer_Apical(sid, neuron, problems, connection):
    '''helper, check if a deep layer apical dendrite is tagged
    with 'L5_Apical' at the root'''
    # BJG: should this be L5_Apical instead of Apical?
    if 'L5_Apical' in neuron.tags:
        if 'soma' not in neuron.tags:
            root_id = neuron.root
            root_labels = neuron.vertices[root_id]['labels']
            if 'L5_Apical' not in root_labels:
                problems['Check_deep_layer_Apical'] = {}
                problems['Check_deep_layer_Apical']['string'] = \
                    'need to tag L5_Apical at the root node [%s]' % root_id
                problems['Check_deep_layer_Apical']['ids'] = {}
                problems['Check_deep_layer_Apical']['ids'][root_id] = ['L5_Apical', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]
        else:
            problems['Check_deep_layer_Apical'] = {}
            problems['Check_deep_layer_Apical']['string'] =  \
                'cant have Apical and soma at the same time'
            problems['Check_deep_layer_Apical']['ids'] = {}
            problems['Check_deep_layer_Apical']['ids'][root_id] = ['L5_Apical', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def find_nron_skels(sid, neuron, nron_skels_dict):
    '''helper, return a dict, key is the nron id, value is a list of skels_id
    that initials this neuron'''
    nron_id = neuron.name
    nron_skels_dict[nron_id] = nron_skels_dict.get(nron_id, []) + [sid, ]


def check_loops(sid, skeleton, problems, connection):
    '''helper, check if a skeleton contains loop'''
    loops = []
    for cid in skeleton['connectivity'].keys():
        pid_list = skeleton['connectivity'][cid].keys()
        if len(pid_list) > 1:
            counter = 0
            for pid in pid_list:
                type = skeleton['connectivity'][cid][pid]['type']
                if type == 'neurite':
                    counter = counter + 1
            if counter > 1:
                loops.append(cid)
    if len(loops):
        problems['Check_loops'] = 'loops at: %s' % str(loops)
        str_problems = 'loops at : ' + str(loops)
        problems['Check_loops'] = {}
        problems['Check_loops']['string'] = str_problems
        problems['Check_loops']['ids'] = {}
        for node_id in loops:
            problems['Check_loops']['ids'][node_id] = ['loop', connection.openURL(neuron=neuron, skID=sid, nodeID=int(node_id))]


def check_skeleton(sid, skeleton, nron_skels_dict, source):
    '''find all the problems for this skeleton'''
    problems = {}
    if isinstance(source, catmaid.source.ServerSource):
        connection = source._skel_source
    else:
        connection = connect_to_catmaid()
    if skeleton is not None:
        check_loops(sid, skeleton, problems, connection)
        if len(skeleton['connectivity']) >= 1:
            if len(skeleton['vertices']) > 2:
                try:
                    neuron = source.get_neuron(skeleton)
                except Exception as e:
                    # e can be more than two soma or can be loops
                    problems['Failed_to_initialize_a_neuron'] = {'string': str(e)}
                    problems['Failed_to_initialize_a_neuron']['ids'] = {}

                    return problems
                check_tags(sid, neuron, problems, connection)
                check_axon(sid, neuron, problems, connection)
                check_soma(sid, neuron, problems, connection)
                check_leaf(sid, neuron, problems, connection)
                check_gaps(sid, neuron, problems, connection)
                check_root_soma(sid, neuron, problems, connection)
                check_root_status(sid, neuron, problems, connection)
                check_synaptic_tags(sid, neuron, problems, connection)
                check_is_finished(sid, neuron, problems, connection)
                check_deep_layer_Apical(sid, neuron, problems, connection)
                find_nron_skels(sid, neuron, nron_skels_dict)
            else:
                problems['Too_few_nodes'] = {'string': 'this skeleton has too few nodes, size of connectivity is %s, size of vertices is %s' % (len(skeleton['connectivity']), len(skeleton['vertices']))}
                problems['Too_few_nodes']['ids'] = {}
        else:
            problems['Too_few_nodes'] = {'string': 'this skeleton has too few nodes, size of connectivity is %s, size of vertices is %s' % (len(skeleton['connectivity']), len(skeleton['vertices']))}
            problems['Too_few_nodes']['ids'] = {}
    else:
        problems['Failed_to_initialize_a_neuron'] = {'string': 'this is an empty skeleton'}
        problems['Failed_to_initialize_a_neuron']['ids'] = {}
    return problems


def check_skeleton_list(sids, source):
    '''go over the sids, find all the problem skeletons
    and stores their problems'''
    problem_skeletons = {}
    nron_skels_dict = {}
    n = len(sids)
    st = time.time()
    for (si, sid) in enumerate(sids):
        printTimeDetails(si, n, st)
        try:
            f = open(get_filename_for_skeleton_id(sid), 'r')
            skeleton = json.load(f)
            f.close()
            problems = check_skeleton(sid, skeleton, nron_skels_dict,
                                      source)
            if len(problems):
                problem_skeletons[sid] = problems
        except IOError:
            pass
    for id in nron_skels_dict:
        skel_list = nron_skels_dict[id]
        if len(skel_list) != 1:
            for skel in skel_list:
                if skel in problem_skeletons.keys():
                    # include neuron id in this error
                    str_problem = 'shares neuron id %s with skeletons : '\
                        % (id) + str(skel_list)
                    problem_skeletons[skel][
                        'Skeletons_share_neuron_id'] = {'string': str_problem}
                    problem_skeletons[skel][
                        'Skeletons_share_neuron_id']['ids'] = {}
                else:
                    problems = {}
                    # include neuron id in this error
                    str_problem = 'shares neuron id %s with skeletons : '\
                        % (id) + str(skel_list)
                    problems[
                        'Skeletons_share_neuron_id'] = {'string': str_problem}
                    problems[
                        'Skeletons_share_neuron_id']['ids'] = {}
                    # BJG: careful! you were assigning problems instead of
                    # problem which would be the set of problems from
                    # the last problematic skeleton, not the
                    # >1 skeleton neuron
                    problem_skeletons[skel] = problems
    return problem_skeletons


def problem_viewer(source, problemSkels=None):
    '''main, check all skeletons and create a report as a html file'''
    if problemSkels is None:
        problemSkels = fetch_and_check(source)
    problemSkels_ids = problemSkels.keys()
    problem_to_skels_dict = problem_to_skels(problemSkels)
    problems_in_skels = problem_to_skels_dict.keys()
    with open('{}/problem_viewer.html'.format(opts.location), 'w') as myFile:
        myFile.write('<html>')

        myFile.write('<head>')
        myFile.write('<title>%s</title>' % time.ctime())
        myFile.write('<script type = "text/javascript">')
        myFile.write(
            'function toggle(div_id) {e = document.getElementById(div_id); ' +
            'e.hidden = !e.hidden;};')
        myFile.write('</script>')
        myFile.write('</head>')

        myFile.write('<body>')
        myFile.write('<p><font size="5" color="black">Below is a list of problems with a list of skeleton ids. ')
        myFile.write('Click on a problem to show (or hide) the list of skeleton ids.</p>')
        for problem in problems_in_skels:
            myFile.write('<p>')
            ind = problems_in_skels.index(problem)
            myFile.write('<a onclick = "toggle(%s)"><font size="4" color="navy"><b>%s</b></a>' % (ind, problem))
            myFile.write('<div id = "%s" hidden>' % (ind))
            myFile.write('<ul>')
            # myFile.write('%s' % (problem_to_skels_dict[problem]))
            for id in problem_to_skels_dict[problem]:
                strId = str(id)
                myFile.write('<a href="#%s_heading" onclick="toggle(%s)"> %s </a>' % (id, id, strId))
                myFile.write(' | ')
            myFile.write('</ul>')
            myFile.write('</div>')
            myFile.write('</p>')
        myFile.write('<p><font size="5" color="black">Below is a list of skeleton ids with known problems. ')
        myFile.write('Click on a skeleton id to show (or hide) the problems.</p>')
        for id in problemSkels_ids:
            strId = str(id)
            myFile.write('<h2>')
            myFile.write('<a id="%s_heading" onclick="toggle(%s)"><font size="4" color="black"> Skeleton %s </a>' % (id, id, strId))
            myFile.write('</h2>')
            myFile.write('<div id = "%s" hidden>' % (strId))
            problems = problemSkels[id]
            myFile.write('<ul>')
            for key in problems:
                probString = problems[key]['string']
                myFile.write('(%s) %s' % (key, probString))
                for node_id in problems[key]['ids'].keys():
                    myFile.write('<input type=\"button\" value=\"{}\" onclick=\"window.open(\'{}\')\">'.format(node_id, problems[key]['ids'][node_id][1]))
                myFile.write('<br>')
            myFile.write('</ul>')
            myFile.write('</div>')
        myFile.write('</body>')

        myFile.write('<html>')
        myFile.close()


def fetch_and_check(source):
    '''fetch the skeletons to the computer, and check each skeleton'''
    sids = fetch_skeletons_pc(source)
    problemSkels = check_skeleton_list(sids, source)
    return problemSkels


def problem_to_skels(problemSkels):
    '''return a dict, key is a problem type, value is a list of skel_ids'''
    problem_to_skels_dict = {}
    for skel in problemSkels.keys():
        problems = problemSkels[skel]
        for key in problems.keys():
            if key in problem_to_skels_dict.keys():
                problem_to_skels_dict[key].append(skel)
            else:
                problem_to_skels_dict[key] = []
                problem_to_skels_dict[key].append(skel)
    return problem_to_skels_dict


if __name__ == '__main__':
    c = connect_to_catmaid()
    src = catmaid.get_source(c, opts.cache)
    problem_viewer(src)

