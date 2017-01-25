#!/usr/bin/env python
'''
This portion of the database transform project pushes skeleton data
    to an existing tracing-ready project in a specified catmaid database.
    TODO:
        lookup projectid from project name -- exists in brkn slc script
IMPORTANT: REQUIRES TRACING TO BE SET UP FOR PROJECT IN TARGET DB!
    Accomplished by activating the tracing tool
Original by David G.C. Hildebrand, Ph.D.
Modified by Russel Torres
'''

import json
import logging
from datetime import datetime
import argparse
import psycopg2
from psycopg2.extensions import AsIs

DEFAULT_projectfile = './20161224_export_FromDB.json'
DEFAULT_db_settings = '../catmaiddb.json'

defaultuserid = 1
oldnodesdone = []   # FIXME ugly hack for recursion issues
recursion_error_threshold = 5

global o_n_skel
o_n_skel = {}

skeltoskip = []  # skeleton id strings to skip


def exportdatabase(project, cursor, connection, projectid, commit_each=True):
    '''
     This portion exports constructed dictionaries to an existing tracing-ready
         project.  Ideally, this is a safe way to combine or transform
         skeletons from different databases
    '''
    md = project['metadata']
    # determine new userids and create if necessary
    old_to_newuser = transfer_users(md['users'], cursor)
    newdbref = {'classes': getrelational('class', projectid, cursor),
                'relations': getrelational('relation', projectid, cursor),
                'class_instances': classinstances(getrelational('class',
                                                                projectid,
                                                                cursor),
                                                  md['annotations'].values(),
                                                  md['neuronnames'].values(),
                                                  md['labels'].values(),
                                                  defaultuserid, projectid,
                                                  cursor, connection)}

    skelclass = newdbref['classes']['skeleton']
    annorel = newdbref['relations']['annotated_with']
    namerel = newdbref['relations']['model_of']
    skeletons = project['reconstructions']['skeletons']
    connectors = project['reconstructions']['connectors']

    totalconns = len(connectors.keys())
    oldnew_conn = {}
    for i, oldconn in enumerate(connectors):
        logging.debug('exporting connector {} of {}'.format(i, totalconns))
        oldnew_conn.update({oldconn: newConnector(
            connectors[oldconn], old_to_newuser, newdbref['relations'],
            newdbref['class_instances'], cursor, connection, projectid)})

    totalskels = len(skeletons.keys())
    for i, oldskel in enumerate(skeletons):
        if oldskel in skeltoskip:
            continue
        logging.debug('exporting skeleton {} of {}'.format(i, totalskels))
        tracing = skeletons[oldskel]['trace']
        annos = skeletons[oldskel]['annotations']
        nm = skeletons[oldskel]['name'].keys()[0]
        nameci = newdbref['class_instances']['names'][nm]
        root = skeletons[oldskel]['root']

        newsid = newskel(skelclass,
                         old_to_newuser[str(skeletons[oldskel]['user_id'])],
                         cursor, connection, projectid)
        o_n_skel.update({oldskel: newsid})
        for anno in annos:
            annoci = newdbref['class_instances']['annotations'][anno]
            addcicirelations(nameci, annoci, annorel, annos[anno],
                             old_to_newuser, cursor, connection, projectid)
        addcicirelations(newsid, nameci, namerel,
                         skeletons[oldskel]['name'][nm],
                         old_to_newuser, cursor, connection, projectid)
        constructtree(newsid, tracing, root,
                      newdbref['class_instances'],
                      newdbref['relations'],
                      old_to_newuser, oldnew_conn,
                      cursor, connection, projectid)
        if commit_each:
            connection.commit()
    connection.commit()


def transfer_users(oldusers, cursor):
    newrowstring = ('INSERT INTO auth_user (password, last_login, '
                    'is_superuser, username, first_name, last_name, email, '
                    'is_staff, is_active, date_joined)'
                    'SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s '
                    'WHERE NOT EXISTS (SELECT id FROM auth_user '
                    'WHERE username = %s) RETURNING id;')
    existingrowstring = ('SELECT id FROM auth_user WHERE username = %s')

    old_to_new = {}
    for olduid in oldusers.keys():
        cursor.execute(newrowstring, (oldusers[olduid]['password'],
                                      (oldusers[olduid]['last_login']
                                       if oldusers[olduid]['last_login'] !=
                                       'None' else None),
                                      oldusers[olduid]['is_super'],
                                      oldusers[olduid]['username'],
                                      oldusers[olduid]['first_name'],
                                      oldusers[olduid]['last_name'],
                                      oldusers[olduid]['email'],
                                      oldusers[olduid]['is_staff'],
                                      oldusers[olduid]['is_active'],
                                      oldusers[olduid]['date_joined'],
                                      oldusers[olduid]['username'],))
        newid = cursor.fetchone()
        if newid is not None:
            sqlstring = ('INSERT INTO catmaid_userprofile (user_id, '
                         'show_text_label_tool, show_tagging_tool, '
                         'show_cropping_tool, show_segmentation_tool, '
                         'show_tracing_tool, show_ontology_tool, '
                         'independent_ontology_workspace_is_default, color, '
                         'show_roi_tool) VALUES (%s, %s, %s,  %s, %s, %s, %s, '
                         '%s, %s, %s);')
            cursor.execute(sqlstring, (newid[0], False, False, False, False,
                                       True, False, False, '(1,0,0,1)',
                                       False,))
        if newid is None:
            cursor.execute(existingrowstring, (oldusers[olduid]['username'],))
            newid = cursor.fetchone()
        old_to_new[olduid] = newid[0]
    return old_to_new


def addcicirelations(ci1, ci2, rel, cicidict, old_to_new,
                     cursor, connection, projectid):
    '''
    This function adds class_instance class_instance relations such as
        neuron names and annotations corresponding to skeletons
    '''
    sqlstring = ('INSERT INTO class_instance_class_instance '
                 '(user_id, project_id, relation_id, '
                 'class_instance_a, class_instance_b, creation_time, '
                 'edition_time) '
                 'VALUES (%s, %s, %s, %s, %s, %s, %s);')
    cursor.execute(sqlstring, (old_to_new[str(cicidict['user_id'])], projectid,
                               rel, ci1, ci2, cicidict['creation_time'],
                               cicidict['edition_time']))


def classinstances(dbclasses, annotations, neuronnames, labels, userid,
                   projectid, cursor, connection):
    '''
    This function updates the class table to include all annotations, labels,
        and names for the neurons
    '''
    newrowstring = ('INSERT INTO class_instance '
                    '(user_id, project_id, class_id, "name") '
                    'SELECT %s, %s, %s, %s '
                    'WHERE '
                    'NOT EXISTS (SELECT id FROM class_instance '
                    'WHERE project_id = %s AND class_id = %s AND "name" = %s) '
                    'RETURNING id;')
    existingrowstring = ('SELECT id FROM class_instance '
                         'WHERE project_id = %s '
                         'AND class_id = %s AND "name" = %s;')

    annodict, namedict, labeldict = {}, {}, {}
    for i in annotations:
        cursor.execute(newrowstring, (userid, projectid,
                       dbclasses['annotation'],
                       i, projectid, dbclasses['annotation'], i, ))
        newid = cursor.fetchone()
        if newid is not None:
            newid = newid[0]

        if newid is None:
            cursor.execute(existingrowstring, (
                projectid, dbclasses['annotation'], i, ))
            newid = cursor.fetchone()[0]
        annodict.update({i: newid})

    for i in labels:
        cursor.execute(newrowstring, (userid, projectid,
                       dbclasses['label'],
                       i, projectid, dbclasses['label'], i, ))
        newid = cursor.fetchone()
        if newid is not None:
            newid = newid[0]

        if newid is None:
            cursor.execute(existingrowstring, (
                projectid, dbclasses['label'], i, ))
            newid = cursor.fetchone()[0]
        labeldict.update({i: newid})
    for i in neuronnames:
        cursor.execute(newrowstring, (userid, projectid,
                       dbclasses['neuron'],
                       i, projectid, dbclasses['neuron'], i, ))
        newid = cursor.fetchone()
        if newid is not None:
            newid = newid[0]

        if newid is None:
            cursor.execute(existingrowstring, (
                projectid, dbclasses['neuron'], i, ))
            newid = cursor.fetchone()[0]
        namedict.update({i: newid})

    return {'annotations': annodict,
            'names': namedict,
            'labels': labeldict}


def getrelational(table, projectid, cursor, columnname=None):
    if columnname is None:
        columnname = '{}_name'.format(table)

    sqlstring = ('SELECT %s, id FROM %s WHERE project_id = %s;')
    cursor.execute(sqlstring, (AsIs(columnname), AsIs(table), projectid, ))
    return {i[0]: i[1] for i in cursor.fetchall()}


def newskel(skelclass, userid, cursor, connection, projectid):
    sqlstring = ('INSERT INTO class_instance (user_id, project_id, '
                 'class_id, "name") '
                 "VALUES (%s, %s, %s, 'skeleton') RETURNING id;")
    cursor.execute(sqlstring, (userid, projectid, skelclass, ))  # FIXME users
    new_skel = cursor.fetchone()[0]
    new_skelstring = 'skeleton ' + str(new_skel)
    sqlstring = ('UPDATE class_instance SET "name" = %s WHERE id = %s;')
    cursor.execute(sqlstring, (new_skelstring, new_skel, ))
    return new_skel


def newConnector(conndict, old_to_newuser, relations, classinstances,
                 cursor, connection, projectid):
    sqlstring = ('INSERT INTO connector (project_id, location_x, '
                 'location_y, location_z, editor_id, user_id, creation_time, '
                 'edition_time, confidence) '
                 'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;')
    cursor.execute(sqlstring, (projectid, conndict['xnm'], conndict['ynm'],
                   conndict['znm'], old_to_newuser[str(conndict['editor_id'])],
                   old_to_newuser[str(conndict['user_id'])],
                   conndict['creation_time'], conndict['edition_time'],
                   conndict['confidence']))
    newconn = cursor.fetchone()[0]

    # insert connector labels
    sqlstring = ('INSERT INTO connector_class_instance (user_id, '
                 'creation_time, edition_time, project_id, relation_id, '
                 'connector_id, class_instance_id) '
                 'VALUES (%s, %s, %s, %s, %s, %s, %s);')

    labeldict = conndict['labels']
    for label in labeldict.keys():
        lbldict = labeldict[label]
        cursor.execute(sqlstring, (old_to_newuser[str(lbldict['user_id'])],
                                   lbldict['creation_time'],
                                   lbldict['edition_time'], projectid,
                                   relations['labeled_as'], newconn,
                                   classinstances['labels'][label], ))
    return newconn


def newskeloldskel(oldskels, skelclass, userid, cursor, connection, projectid):
    newandold = {}
    sqlstring = ('INSERT INTO class_instance (user_id, project_id, '
                 'class_id, "name") '
                 "VALUES (%s, %s, %s, 'skeleton') RETURNING id;")
    cursor.execute(sqlstring, (userid, projectid, skelclass))
    new_skel = cursor.fetchone()[0]
    new_skelstring = 'skeleton ' + str(new_skel)
    sqlstring = ('UPDATE class_instance SET "name" = %s WHERE id = %s;')
    cursor.execute(sqlstring, (new_skelstring, new_skel))
    return {new_skel: oldskel}


def parentchild(tracing):
    parentchildren = {}
    for node in tracing:
        if tracing[node]['parent'] is not None:
            if tracing[node]['parent'] not in parentchildren.keys():
                parentchildren[tracing[node]['parent']] = []
            parentchildren[tracing[node]['parent']].append(node)
    return parentchildren


def constructtree(newsid, tracing, root, class_instance, relations,
                  old_to_newuser, oldnew_conn, cursor, connection, projectid):
    oldparentchild = parentchild(tracing)
    _ = newtrace(newsid, tracing, oldparentchild,
                 root, root, None, class_instance, relations,
                 old_to_newuser, oldnew_conn, cursor, connection, projectid)


# FIXME recursion leads to duplication
def newtrace(new_skel, oldskel, oldparentchild, oldparent, startnode,
             newparent, ci, rel, old_to_newuser, oldnew_conn,
             cursor, connection, projectid):
    '''
    Executes a depth-first tracing which generates new nodes with labels
        and connector relations
    '''

    count = 0
    elder = None
    if newparent is not None:
        elder = newparent
    if str(startnode) not in oldnodesdone:
        newparent = addnode(oldskel, str(startnode), new_skel, newparent,
                            ci, rel, old_to_newuser, oldnew_conn,
                            cursor, connection, projectid)
        oldnodesdone.append(str(startnode))
    else:
        count += 1
    stepparent = newparent
    if len(oldparentchild.keys()) > 1:
        children = oldparentchild[int(oldparent)]
        for child in children:
            newparent = stepparent
            bro = int(child[:])
            if str(bro) not in oldnodesdone:  # FIXME ugly hack
                newparent = addnode(oldskel, str(bro), new_skel, newparent, ci,
                                    rel, old_to_newuser, oldnew_conn,
                                    cursor, connection, projectid)
                oldnodesdone.append(str(bro))  # FIXME
            else:
                count += 1
                if count > recursion_error_threshold:
                    break
            while bro in oldparentchild.keys():
                if len(oldparentchild[bro]) > 1:
                    for kid in oldparentchild[bro]:
                        s = newparent
                        _ = newtrace(new_skel, oldskel, oldparentchild,
                                     bro, kid[:], newparent, ci, rel,
                                     old_to_newuser, oldnew_conn,
                                     cursor, connection, projectid)
                        newparent = s
                    break
                else:
                    bro = int(oldparentchild[bro][0])
                    if str(bro) not in oldnodesdone:  # FIXME ugly hack
                        newparent = addnode(oldskel, str(bro), new_skel,
                                            newparent, ci, rel,
                                            old_to_newuser, oldnew_conn,
                                            cursor, connection, projectid)
                        oldnodesdone.append(str(bro))  # FIXME
                    else:
                        count += 1
                        if count > recursion_error_threshold:
                            break
    return elder


def addnode(tracing, nid, skeleton, parent, classinstances, relations,
            old_to_newuser, oldnew_conn, cursor, connection, projectid,
            supp_virt=True, zres=60.):
    nodeproperties = tracing[nid]

    # insert treenode into treenode table
    sqlstring = ('INSERT INTO treenode (project_id, location_x, location_y, '
                 'location_z, editor_id, user_id, skeleton_id, confidence, '
                 'radius, creation_time, edition_time, parent_id) '
                 'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) '
                 'RETURNING id;')
    cursor.execute(sqlstring,
                   (projectid, nodeproperties['xnm'],
                    nodeproperties['ynm'], nodeproperties['znm'],
                    old_to_newuser[str(nodeproperties['editor_id'])],
                    old_to_newuser[str(nodeproperties['user_id'])], skeleton,
                    nodeproperties['confidence'],
                    nodeproperties['radius'], nodeproperties['creation_time'],
                    nodeproperties['edition_time'], parent, ))
    newnode = cursor.fetchone()[0]

    # attach labels to treenode
    sqlstring = ('INSERT INTO treenode_class_instance '
                 '(user_id, project_id, relation_id, '
                 'treenode_id, class_instance_id) '
                 'VALUES (%s, %s, %s, %s, %s);')
    for i in nodeproperties['labels']:
        cursor.execute(sqlstring,
                       (old_to_newuser[str(nodeproperties['user_id'])],
                        projectid, relations['labeled_as'],
                        newnode, classinstances['labels'][i]))

    # add connectors
    for oldconnid in nodeproperties['connectors'].keys():
        connprops = nodeproperties['connectors'][oldconnid]
        newconnid = oldnew_conn[oldconnid]

        relid = relations[connprops['relation']]
        sqlstring = ('INSERT INTO treenode_connector (user_id, creation_time, '
                     'edition_time, project_id, relation_id, treenode_id, '
                     'connector_id, skeleton_id, confidence) '
                     'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);')
        cursor.execute(sqlstring, (connprops['user_id'],
                                   connprops['creation_time'],
                                   connprops['edition_time'], projectid, relid,
                                   newnode, newconnid, skeleton,
                                   connprops['confidence'], ))

    # optionally suppress virtual nodes in z
    if supp_virt and (nodeproperties['parent'] is not None):
        nz = nodeproperties['zpix']
        pz = tracing[str(nodeproperties['parent'])]['zpix']
        vnodezs = range((int(min(nz, pz)) + 1), int(max(nz, pz)))
        # TODO this only suppresses nodes in z.  general purpose needs work
        for vnodez in vnodezs:
            zloc = zres * vnodez
            sqlstring = ('INSERT INTO suppressed_virtual_treenode (user_id, '
                         'project_id, creation_time, edition_time, '
                         'child_id, location_coordinate, '
                         'orientation) VALUES(%s, %s, %s, %s, %s, %s, %s);')
            cursor.execute(sqlstring,
                           (old_to_newuser[str(nodeproperties['user_id'])],
                            projectid, str(datetime.now()),
                            str(datetime.now()), newnode, zloc, 0,))
    return newnode


def toggle_triggers(table, cursor, state=True):
    sqlstring = (('ALTER TABLE %s ENABLE TRIGGER USER;')
                 if state else
                 ('ALTER TABLE %s DISABLE TRIGGER USER;'))
    cursor.execute(sqlstring, (AsIs(table), ))

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--db_settings_file', required=True,
                    help='json file containing access credentials for '
                    'target CATMAID database.')
parser.add_argument('-t', '--target_project_id', required=True,
                    help='CATMAID project id to which reconstructions '
                    'will be added.')
parser.add_argument('-i', '--input_project_json', required=True,
                    help='json file formatted from custom export '
                    'of CATMAID database.')
parser.add_argument('-m', '--map_old_new_output', required=False,
                    help='json file to which skeleton id (pkey) old>new '
                    'will be written.')

if __name__ == "__main__":
    opts = parser.parse_args()
    db_settings = (opts.db_settings_file if opts.db_settings_file
                   else DEFAULT_db_settings)
    project_id = opts.target_project_id
    projectfile = (opts.input_project_json if opts.input_project_json
                   else DEFAULT_projectfile)
    map_on_file = (opts.map_old_new_output if opts.map_old_new_output
                   else None)

    # load project dump file
    with open(projectfile, 'r') as f:
        pdata = json.load(f)

    # load db settings and connect to database
    with open(db_settings, 'r') as f:
        conn_catmaid_settings = json.load(f)
    conn = psycopg2.connect(**conn_catmaid_settings)
    curs = conn_catmaid.cursor()

    # optionally skip triggers in selected tables THIS IS NOT RECOMMENDED
    triggers_to_skip = []
    for t in triggers_to_skip:
        toggle_trigger(t, curs, False)

    exportdatabase(pdata, curs, conn, str(projectid), False)

    for t in triggers_to_skip:
        toggle_triggers(t, curs, True)

    if map_on_file is not None:
        with open(map_on_file, 'w') as f:
            json.dump(o_n_skel, f)

    conn.close()
