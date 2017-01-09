'''
This is a section of the database transform project which extracts useful
    skeleton data from a catmaid database.  This data can then be repositioned
    and transferred to a new database using "transformfromcsv.py" and
    "push_skeletons.py", respectively.

    TODO:
        Backward-compatibility for catmaid w/o annotations
        lookup projectid value from project name -exists in broken slc script


Original by David G.C. Hildebrand, Ph.D.
Modified by Russel Torres
'''

import psycopg2
import re
import json
from time import strftime
import os
import sys

db_settings_file = '../catmaiddb_old.json'
d = strftime('%Y%m%d')
allout = './{}_export_FromDB.json'.format(d)


def testdbcursor():
    with open(db_settings_file, 'r') as fil:
        conn_catmaid_settings = json.load(fil)

    conn_catmaid = psycopg2.connect(**conn_catmaid_settings)
    curs_catmaid = conn_catmaid.cursor()
    return curs_catmaid, conn_catmaid


def getskeletons(cursor, projectid, individual_skels=False, indout=None):
    md = projectmetadata(cursor, projectid)

    # get dictionaries based on pgSQL relationships
    namedict = getnamedict(md['neuronnames'], cursor, projectid)
    tn_labeldict = gettnlabeldict(md['labels'], cursor, projectid)
    annodict = getannodict(md['annotations'], cursor, projectid)
    conn_labeldict = getconnlabeldict(md['labels'], cursor, projectid)

    connectors = getConnectors(conn_labeldict, md['resXYZ'], cursor, projectid)
    skeldict = getskeldict(cursor, projectid)
    skeletons = {}
    for skeleton in skeldict.keys():
        skeltrace, rootnode = gettracing(skeleton, tn_labeldict,
                                         md['resXYZ'], cursor, projectid)
        skelname = namedict.get(skeleton, {})
        skelanno = annodict.get(skeleton, {})

        skeld = {'trace': skeltrace,
                 'annotations': skelanno,
                 'name': skelname,
                 'root': rootnode,
                 'user_id': skeldict[skeleton]['user_id'],
                 'creation_time': skeldict[skeleton]['creation_time'],
                 'edition_time': skeldict[skeleton]['edition_time']}
        skeletons.update({skeleton: skeld})

        if individual_skels:
            if indout is None:
                indout = './migratefiles/fromolddb_{}/'.format(d)
            if not os.path.exists(dest):
                os.makedirs(dest)
            with open((dest + str(skeleton) + '.json'), 'w') as fp:
                json.dump(skeld, fp)
        del skeld
    return {'reconstructions': {'skeletons': skeletons,
                                'connectors': connectors},
            'metadata': md}


def getskeldict(cursor, projectid):
    sqlstring = ("SELECT id FROM class WHERE project_id = %s "
                 "AND class_name = 'skeleton';")
    cursor.execute(sqlstring, (projectid, ))
    classid = str(cursor.fetchone()[0])
    sqlstring = ('SELECT id, user_id, creation_time, edition_time '
                 'from class_instance '
                 'WHERE project_id = %s and class_id = %s;')
    cursor.execute(sqlstring, (projectid, classid, ))
    return {i[0]: {'user_id': i[1],
                   'creation_time': str(i[2]),
                   'edition_time': str(i[3])}
            for i in cursor.fetchall()}


def getConnectors(connlabels, resXYZ, cursor, projectid):
    sqlstring = ('SELECT DISTINCT connector_id, skeleton_id '
                 'FROM treenode_connector WHERE project_id = %s;')
    cursor.execute(sqlstring, (projectid, ))
    connskels = {}
    for cs in cursor.fetchall():
        if cs[0] in connskels.keys():
            connskels[cs[0]].append(cs[1])
        else:
            connskels[cs[0]] = [cs[1]]

    sqlstring = ('SELECT id, location_x, location_y, location_z, '
                 'confidence, user_id, editor_id, '
                 'creation_time, edition_time FROM connector '
                 'WHERE project_id = %s;')
    cursor.execute(sqlstring, (projectid, ))
    return {i[0]: {'xnm': float(i[1]),
                   'xpix': float(i[1]) / resXYZ[0],
                   'ynm': float(i[2]),
                   'ypix': float(i[2]) / resXYZ[1],
                   'znm': float(i[3]),
                   'zpix': float(i[3]) / resXYZ[2],
                   'confidence': i[4],
                   'user_id': i[5],
                   'editor_id': i[6],
                   'creation_time': str(i[7]),
                   'edition_time': str(i[8]),
                   'labels': connlabels.get(i[0], {}),
                   'connections': connskels[i[0]]}
            for i in cursor.fetchall()}


def gettracing(skeletonid, nodelabels, resXYZ, cursor, projectid):
    sqlstring = ('SELECT id, location_x, location_y, location_z, '
                 'parent_id, confidence, user_id, editor_id, '
                 'creation_time, edition_time, radius '
                 'FROM treenode '
                 'WHERE project_id = %s AND skeleton_id = %s '
                 'ORDER BY parent_id NULLS FIRST;')
    cursor.execute(sqlstring, (projectid, skeletonid))
    fetched = cursor.fetchall()
    skeldict = {}
    for i in fetched:
        labels = nodelabels.get(i[0], [])

        if i[4] is None:
            rootnode = i[0]
        skeldict.update({i[0]: {'xnm': float(i[1]),
                                'xpix': (float(i[1]) / resXYZ[0]),
                                'ynm': float(i[2]),
                                'ypix': (float(i[2]) / resXYZ[1]),
                                'znm': float(i[3]),
                                'zpix': (float(i[3]) / resXYZ[2]),
                                'parent': i[4],
                                'confidence': i[5],
                                'user_id': i[6],
                                'editor_id': i[7],
                                'creation_time': str(i[8]),
                                'edition_time': str(i[9]),
                                'radius': i[10],
                                'labels': labels,
                                'connectors': treenode_conns(i[0], cursor,
                                                             projectid)}})
    return skeldict, rootnode


def treenode_conns(tn, cursor, projectid):
    sqlstring = ('SELECT id, relation_name FROM relation '
                 'WHERE project_id = %s '
                 'AND relation_name = %s '
                 'OR relation_name = %s;')
    cursor.execute(sqlstring, (projectid, 'postsynaptic_to', 'presynaptic_to'))
    connrel = {i[0]: i[1] for i in cursor.fetchall()}

    sqlstring = ('SELECT connector_id, relation_id, confidence, '
                 'creation_time, edition_time, user_id '
                 'FROM treenode_connector WHERE project_id = %s '
                 'AND treenode_id = %s;')
    cursor.execute(sqlstring, (projectid, tn))

    return {i[0]: {'relation': connrel[i[1]],
                   'confidence': int(i[2]),
                   'creation_time': str(i[3]),
                   'edition_time': str(i[4]),
                   'user_id': i[5]}
            for i in cursor.fetchall()}


def getrelation(relstring, cursor, projectid):
    sqlstring = ("SELECT id FROM relation "
                 "WHERE project_id = %s AND relation_name = %s")
    cursor.execute(sqlstring, (projectid, relstring, ))
    return cursor.fetchone()[0]


def getnamedict(namemeta, cursor, projectid):
    relationid = str(getrelation('model_of', cursor, projectid))
    sqlstring = ('SELECT class_instance_a, class_instance_b, user_id, '
                 'creation_time, edition_time '
                 'FROM class_instance_class_instance '
                 'WHERE relation_id = %s;')
    cursor.execute(sqlstring, (relationid, ))
    # returns a dictionary in "skeleton named NAME" format -- assumes one name
    return {name[0]: {namemeta[name[1]]: {'user_id': name[2],
                                          'creation_time': str(name[3]),
                                          'edition_time': str(name[4])}}
            for name in cursor.fetchall()}


def getneuronskels(cursor, projectid):
    relationid = getrelation('model_of', cursor, projectid)
    sqlstring = ('SELECT class_instance_a, class_instance_b '
                 'FROM class_instance_class_instance '
                 'WHERE relation_id = %s;')
    cursor.execute(sqlstring, (relationid, ))
    neuronskel = cursor.fetchall()

    nsdict = {}
    for i in neuronskel:
        if i[1] not in nsdict:
            nsdict[i[1]] = []
        nsdict[i[1]].append(i[0])
    return nsdict


def getannodict(annometa, cursor, projectid):
    relationid = str(getrelation('annotated_with', cursor, projectid))
    neuronskels = getneuronskels(cursor, projectid)
    sqlstring = ('SELECT class_instance_a, class_instance_b, user_id, '
                 'creation_time, edition_time '
                 'FROM class_instance_class_instance '
                 'WHERE relation_id = %s;')
    cursor.execute(sqlstring, (relationid, ))
    annodict = {}
    for i in cursor.fetchall():
        d = {annometa[i[1]]: {'user_id': i[2],
                              'creation_time': str(i[3]),
                              'edition_time': str(i[4])}}
        if i[0] in neuronskels.keys():
            for skel in neuronskels[i[0]]:
                if skel in annodict.keys():
                    annodict[skel].update(d)
                else:
                    annodict.update({skel: d})
    return annodict


def getconnlabeldict(labelmeta, cursor, projectid):
    relationid = str(getrelation('labeled_as', cursor, projectid))
    sqlstring = ('SELECT connector_id, class_instance_id, '
                 'user_id, creation_time, edition_time '
                 'FROM connector_class_instance WHERE relation_id = %s;')
    cursor.execute(sqlstring, (relationid, ))
    label = cursor.fetchall()
    labeldict = {}
    for i in label:
        d = {labelmeta[i[1]]: {'user_id': i[2],
                               'creation_time': str(i[3]),
                               'edition_time': str(i[4])}}
        lblstring = labelmeta[i[1]]
        if i[0] in labeldict:
            labeldict[i[0]].update(d)
        else:
            labeldict[i[0]] = d
    return labeldict


def gettnlabeldict(labelmeta, cursor, projectid):
    relationid = str(getrelation('labeled_as', cursor, projectid))
    sqlstring = ('SELECT treenode_id, class_instance_id, '
                 'user_id, creation_time, edition_time '
                 'FROM treenode_class_instance WHERE relation_id = %s;')
    cursor.execute(sqlstring, (relationid, ))
    label = cursor.fetchall()
    labeldict = {}
    for i in label:
        d = {labelmeta[i[1]]: {'user_id': i[2],
                               'creation_time': str(i[3]),
                               'edition_time': str(i[4])}}
        lblstring = labelmeta[i[1]]
        if i[0] in labeldict:
            labeldict[i[0]].update(d)
        else:
            labeldict[i[0]] = d
    return labeldict


# The following functions get a dict of metadata for a project
def projectmetadata(cursor, projectid):
    title, stackid, stackname, resXYZ = getprojleveldata(cursor, projectid)
    return {'labels': getclasses(cursor, projectid, 'label'),
            'annotations': getclasses(cursor, projectid, 'annotation'),
            'neuronnames': getclasses(cursor, projectid, 'neuron'),
            'title': title,
            'stack_id': stackid,
            'stack_title': stackname,
            'resXYZ': resXYZ,
            'resX': resXYZ[0],
            'resY': resXYZ[1],
            'resZ': resXYZ[2],
            'users': getuserdata(cursor)}


def getuserdata(cursor):
    sqlstring = ('SELECT id, password, last_login, is_superuser, username, '
                 'first_name, last_name, email, '
                 'is_staff, is_active, date_joined '
                 'FROM auth_user;')
    cursor.execute(sqlstring)
    return{r[0]: {'password': r[1],
                  'last_login': str(r[2]),
                  'is_super': r[3],
                  'username': r[4],
                  'first_name': r[5],
                  'last_name': r[6],
                  'email': r[7],
                  'is_staff': r[8],
                  'is_active': r[9],
                  'date_joined': str(r[10])} for r in cursor.fetchall()}


def getclasses(cursor, projectid, classname):
    sqlstring = ("SELECT id FROM class WHERE project_id = %s "
                 "AND class_name = %s;")
    cursor.execute(sqlstring, (projectid, classname, ))
    classid = str(cursor.fetchone()[0])

    sqlstring = ('SELECT id, "name" FROM class_instance WHERE class_id = %s;')
    cursor.execute(sqlstring, (classid, ))
    return {i[0]: i[1] for i in cursor.fetchall()}


def getprojleveldata(cursor, projectid):
    sql_str = ("SELECT project.title,stack.id,stack.title,stack.resolution "
               "FROM project,project_stack,stack "
               "WHERE project.id=%s "
               "AND project.id=project_stack.project_id "
               "AND stack.id=project_stack.stack_id;")
    cursor.execute(sql_str, str(projectid))
    r = cursor.fetchall()[0]
    projecttitle = str(r[0])
    stackid = int(r[1])
    stackname = r[2]
    stackres = r[3]

    resstring = stackres.replace('(', '').replace(')', '')
    resXYZ = [float(i) for i in re.split(',', resstring)]

    return projecttitle, stackid, stackname, resXYZ

if __name__ == "__main__":
    '''when run as script, works for arbitrary project'''
    projectid = sys.argv[1]
    curs, conn = testdbcursor()
    al = getskeletons(curs, projectid)

    with open(allout, 'w') as alf:
        json.dump(al, alf)

    conn.close()
