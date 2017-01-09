# Script initially by Tom Kazimiers 2013-01-12
# Adapted by Albert Cardona 2013-01-25
# Further adapted by Brett Graham 2013-10-03
#
# The purpose of this script is to connect to a django session
# in a remote computer, and to retrieve information from the database
# such as the skeleton of a neuronal arbor and its synapses

import base64
import cookielib
import json
import math
import os
import sys
import urllib
import urllib2
import webbrowser

has_numpy = False
try:
    import numpy
    import scipy.io
    has_numpy = True
except ImportError as E:
    print "Failed to import numpy and scipy: %s" % E


try:
    import networkx
except ImportError as E:
    print "networkx failed to import: %s" % E
    print "various morphological measures will fail"
    networkx = None

node_dist = lambda vs, v0, v1: sum(
    [(vs[v0][k] - vs[v1][k]) ** 2. for k in ('x', 'y', 'z')]) ** 0.5


class Neuron(object):
    def __init__(self, skeleton):
        self.name = skeleton['neuron']['neuronname'].split()[1]
        self.vertices = skeleton['vertices']
        self.dedges = skeleton['connectivity']
        self.dgraph = networkx.DiGraph()
        self.edges = {}
        for cid in self.dedges:
            for pid in self.dedges[cid]:
                if cid not in self.vertices:
                    #print(
                    #    "Invalid edge: {} (missing) and {}".format(
                    #        cid, pid))
                    continue
                if pid not in self.vertices:
                    #print(
                    #    "Invalid edge: {} and {} (missing)".format(
                    #        cid, pid))
                    continue
                if self.dedges[cid][pid]['type'] == 'neurite':
                    self.edges[cid] = self.edges.get(cid, []) + [pid, ]
                    self.edges[pid] = self.edges.get(pid, []) + [cid, ]
                    # these edges are stored in REVERSE [child][parent]
                    self.dgraph.add_edge(pid, cid)
                elif self.dedges[cid][pid]['type'] in (
                        'presynaptic_to', 'postsynaptic_to'):
                    pass  # store these?
                else:
                    print(
                        "Found edge in {} {}{} with unknown type {}".format(
                            self.name, cid, pid, self.dedges[cid][pid]['type']))
        self.graph = self.dgraph.to_undirected()
        self.soma = None
        self.connectors = {}
        self.synapses = {}
        self.axons = {}
        self.tags = {}
        for vk in self.vertices:
            v = self.vertices[vk]
            for l in v['labels']:
                self.tags[l] = self.tags.get(l, []) + [vk, ]
            if 'soma' in v['labels']:
                if self.soma is not None:
                    raise ValueError("Neuron {} has two somas: {} {}".format(self.name, vk, self.soma))
                self.soma = vk
            if v['type'] == 'connector':
                self.connectors[vk] = v
            if v['type'] == 'skeleton':
                for l in v['labels']:
                    if 'syn' in l:
                        self.synapses[vk] = v
                        break
            if 'axon' in v['labels']:
                self.axons[vk] = v

        for ax in self.axons:
            # for each axon find all it's terminations and it's 'trunk'
            tree = networkx.algorithms.traversal.bfs_tree(self.dgraph, ax)
            leaves = [n for n in tree if tree.out_degree(n) == 0]
            self.axons[ax]['tree'] = tree
            self.axons[ax]['terminals'] = leaves
            for t in leaves:
                if 'termination (axon trunk)' in \
                        self.vertices[t]['labels']:
                    if ('trunk' in self.axons[ax]) and \
                            (self.axons[ax]['trunk'] != t):
                        print("Found 2 axon trunks in {}: {} and {}".format(
                            self.name, self.axons[ax]['trunk'], t))
                    self.axons[ax]['trunk'] = t
        # cull axons
        for axa in self.axons.keys():
            for axb in self.axons.keys():
                if axa == axb or axb not in self.axons or axa not in self.axons:
                    continue
                if axa in self.axons[axb]['tree']:
                    del self.axons[axa]

        sg = networkx.topological_sort(self.dgraph)
        if not len(sg):
            raise ValueError(
                "unable to find root in {}, graph contains no nodes [{} vertices]".format(
                    self.name, len(self.vertices)))
        self.root = sg[0]
        if self.soma is not None:
            if self.soma != self.root:
                print("Found root in {}, {} that doesn't match soma {}".format(
                    self.name, self.root, self.soma))
    def openURL(self, skID, nodeID=-1, openBrowser=True):
        # opens a webbrowser with the given nodeID(goes to
        # root if nodeID omitted must pass skeletonID
        if(nodeID == -1):
            nodeID = self.root
        [x, y, z] = [self.vertices[str(nodeID)]['x'],
                     self.vertices[str(nodeID)]['y'],
                     self.vertices[str(nodeID)]['z']]
        url = 'http://catmaid.hms.harvard.edu/?active_skeleton_id={}&'\
              'active_node_id={}&pid=9&sid0=6&s0=4&xp={}&yp={}&zp={}&'\
              'tool=tracingtool'.format(skID, nodeID, x, y, z)
        if(openBrowser):
            webbrowser.open_new(url)
        return url

    def axon_trunk(self):
        # get main axon (one with trunk, if multiple, return all
        axon_trunks = []
        for ax in self.axons:
            if 'trunk' in self.axons[ax]:
                axon_trunks.append(self.axons[ax])
        return axon_trunks
    
    def dendrites(self):
        # this assumes all that is not axon is dendrite
        if len(self.axons) == 0:
            return self.dgraph
        dends = self.dgraph.copy()
        for ax in self.axons:
            axon = self.axons[ax]
            for n in axon['tree']:
                if n in dends:
                    dends.remove_node(n)
        return dends

    def leaves(self):
        return [n for n in self.dgraph if self.dgraph.out_degree(n) == 0]

    def midpoint(self, v0, v1):
        return dict([
            (d, (self.vertices[v0][d] + self.vertices[v1][d]) / 2.)
            for d in ('x', 'y', 'z')])

    def distance(self, v0, v1):
        """euclidian distance"""
        return sum([
            (self.vertices[v0][k] - self.vertices[v1][k]) ** 2.
            for k in ('x', 'y', 'z')]) ** 0.5

    def path(self, v0, v1):
        return networkx.shortest_path(self.graph, v0, v1)

    def path_length(self, v0, v1):
        """path along skeleton"""
        path = self.path(v0, v1)
        return sum([
            self.distance(path[i], path[i+1]) for i in xrange(len(path) - 1)])

    def branch_order(self, v, base=None):
        """if base is None, default to soma"""
        if base is None:
            base = self.soma
            if self.soma is None:
                return None
        path = networkx.shortest_path(self.graph, base, v)
        order = 0
        for v in path:
            if len(self.edges[v]) > 2:
                order += 1
        return order

    def myelination(self, axid=None):
        """
        For each excitatory neuron with an axon:
        1) calculate axonal path length
            (all calculations on axonal trunk only; skip collaterals)
        2) calculate path length between node tagged "axon" to first node
            tagged "myelinated" this would be considered the
            premyelin axonal segment (PMAS)
        3) calculate path length between any pair of
            "myelinated" and "unmyelinated" tags
        4) calculate [myelination coverage]/[axonal path length]
        5) categorize cells as having "unmyelinated",
            "intermittently myelinated", or "long PMAS" axons
        6) test if (5) is related to function.
        """
        if axid is None:
            return dict([
                (axid, self.myelination(axid)) for axid in self.axons])
        if axid not in self.axons:
            raise ValueError(
                "Invalid axon id {} not in {}".format(axid, self.axons.keys()))
        axon = self.axons[axid]
        if 'trunk' not in axon:
            print("Axon {} missing trunk".format(axid))
            return {}  # axon does not have a trunk
        path = self.path(axid, axon['trunk'])
        dist = 0.
        myelinated = 0.
        #state = 0  # 0: un-myelinated, 1: myelinated
        state = int(bool('myelinated' in self.vertices[path[0]]['labels']))
        pmas = float('nan')
        p = path[0]
        for n in path[1:]:
            d = self.distance(p, n)
            if state == 1:
                myelinated += d
            if 'myelinated' in self.vertices[n]['labels']:
                if state == 1:
                    print("myelinated tag at {} "
                          "when already myelinated".format(n))
                state = 1
                if math.isnan(pmas):
                    #print("found pmas {}".format(n))
                    pmas = dist
                #print("found myelinated {}".format(n))
            elif 'unmyelinated' in self.vertices[n]['labels']:
                if state == 0:
                    print("unmyelinated tag at {} "
                          "when already unmyelinated".format(n))
                state = 0
                #print("found unmyelinated {}".format(n))
            dist += d
            p = n
        return dict(pmas=pmas, dist=dist, myelinated=myelinated)

    def center_of_mass(self):
        # it's a series of tubes!
        com = {'x': 0., 'y': 0., 'z': 0.}
        mass = 0.
        for e0 in self.dedges:
            if e0 not in self.vertices:
                print("Warning: missing node {}".format(e0))
                continue
            for e1 in self.dedges[e0]:
                if e1 not in self.vertices:
                    print("Warning: missing node {}".format(e1))
                    continue
                if not self.dedges[e0][e1]['type'] == 'neurite':
                    continue
                # distance between nodes
                m = self.midpoint(e0, e1)
                d = self.distance(e0, e1)
                com['x'] += m['x'] * d
                com['y'] += m['y'] * d
                com['z'] += m['z'] * d
                mass += d
        com['x'] /= mass
        com['y'] /= mass
        com['z'] /= mass
        return com


class Connection:
    def __init__(self, server, username, password, project=None, authname=None,
                 authpassword=None, login=True):
        self.server = server
        self.authname = username if authname is None else authname
        self.authpassword = password if authpassword is None else authpassword
        self.username = username
        self.password = password
        self.cookies = cookielib.CookieJar()
        self._projects = None
        self._pid = project
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPCookieProcessor(self.cookies))
        if login:
            self.login()
    def __reduce__(self):
	return(self.__class__,(self.server,self.authname,self.authpassword,
		               self.username,self.password,self._pid))
    def djangourl(self, path):
        """ Expects the path to lead with a slash '/'. """
        assert path[0] == '/'
        return self.server + path

    def auth(self, request):
        if self.authname:
            base64string = base64.encodestring(
                '%s:%s' % (self.authname, self.authpassword)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)

    def login(self):
        url = self.djangourl("/accounts/login")
        opts = {
            'name': self.username,
            'pwd': self.password
        }
        data = urllib.urlencode(opts)
        request = urllib2.Request(url, data)
        self.auth(request)
        response = urllib2.urlopen(request)
        self.cookies.extract_cookies(response, request)
        return response.read()

    def fetch(self, url, post=None):
        """ Fetch a url with optional post data (dict) """
        if url[:4] != 'http':
            url = self.djangourl(url)
        if post:
            request = urllib2.Request(url, post)
        else:
            request = urllib2.Request(url)

        self.auth(request)
        return self.opener.open(request).read()

    def fetchJSON(self, url, post=None):
        response = self.fetch(url, post=post)
        if not response:
            return
        r = json.loads(response)
        if type(r) == dict and 'error' in r:
            print "ERROR:", r['error']
        else:
            return r


    def fetch_projects(self):
        if self._projects is None:
            self._projects = self.fetchJSON('/projects')
        return self._projects

    projects = property(fetch_projects)

    def find_pid(self, title):
        if title is None:
            if self._pid is None:
                raise ValueError("A project name or id must be provided")
            elif isinstance(self._pid, int):
                return self._pid
            else:
                return self.find_pid(self._pid)
        if isinstance(title, int):
            return title
        for p in self.projects:
            if p['title'] == title:
                return p['pid']
        raise LookupError("Project with title %s not found" % title)

    def set_project(self, project):
        self._pid = self.find_pid(project)

    def skeleton(self, sid, project=None):
        pid = self.find_pid(project)
        return self.fetchJSON('/{}/skeleton/{}/json'.format(pid, sid))

    def skeleton_ids(self, project=None):
        pid = self.find_pid(project)
        wd = self.wiring_diagram(pid)
        return [int(n['id']) for n in wd['data']['nodes']]

    def neuron_id(self, sid, project=None):
        pid = self.find_pid(project)
        return int(self.fetchJSON(
            '/{}/skeleton/{}/neuronname'.format(pid, sid))['neuronid'])

    def neuron_ids(self, project=None):
        pid = self.find_pid(project)
        return [self.neuron_id(sid, pid) for sid in self.skeleton_ids(pid)]

    def wiring_diagram(self, project=None):
        pid = self.find_pid(project)
        return self.fetchJSON('/{}/wiringdiagram/json'.format(pid))

    def adjacency_matrix(self, project=None, save=False):
        return wiring_diagram_to_adjacency_matrix(
            self.wiring_diagram(project), save)

    def user_stats(self, project=None):
        pid = self.find_pid(project)
        return self.fetchJSON('/{}/stats-user-history'.format(pid))


def connect():
    """ connect using environment variables """
    server = os.environ['CATMAID_SERVER']
    user = os.environ['CATMAID_USER']
    password = os.environ['CATMAID_PASSWORD']
    project = os.environ.get('CATMAID_PROJECT', None)
    if project is not None:
        project = int(project)
    return Connection(server, user, password, project)


def wiring_diagram_to_adjacency_matrix(wd, save=False):
    if not has_numpy:
        raise Exception("Numpy and scipy.io required for adjacency_matrix")
    # get all skeletons
    sids = sorted([n['id'] for n in wd['data']['nodes']])
    nsids = len(sids)
    lookup = dict([(sids[i], i) for i in xrange(nsids)])
    # matrix: row & columns = skeletons, values = N connections
    m = numpy.zeros((nsids, nsids))
    for e in wd['data']['edges']:
        # [source, target]
        m[lookup[e['source']], lookup[e['target']]] = e['number_of_connector']
    # save matrix & skeleton list
    sids = numpy.array([int(sid) for sid in sids])
    if save:
        scipy.io.savemat('adjacency.mat', mdict={'adjacency': m})
        scipy.io.savemat('skeletons.mat', mdict={'skeletons': sids})
    return m, sids


def guess_type(s):
    try:
        return int(s)
    except:
        pass
    try:
        return float(s)
    except:
        pass
    if s == 'None':
        return None
    elif s == 'True':
        return True
    elif s == 'False':
        return False
    return s


def main():
    server, username, password, project, command = sys.argv[1:6]
    args = [guess_type(s) for s in sys.argv[6:]]
    print server, username, password, project, command, args

    c = Connection(server, username, password, project=project)
    f = getattr(c, command)

    print f(*args)


if __name__ == "__main__":
    main()
