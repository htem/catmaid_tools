# Script initially by Tom Kazimiers 2013-01-12
# Adapted by Albert Cardona 2013-01-25
# Further adapted by Brett Graham 2013-10-03
#
# The purpose of this script is to connect to a django session
# in a remote computer, and to retrieve information from the database
# such as the skeleton of a neuronal arbor and its synapses

import base64
import cookielib
import getpass
import json
import os
import logging
import urllib
import warnings
import webbrowser
from StringIO import StringIO
import numpy
from PIL import Image

try:
    import urllib2
except ImportError as E:
    logging.error("No urllib2 found, Error: {}".format(E))
    import urllib.request
    urllib2 = urllib.request

from . import algorithms
from . import errors


class Connection:
    def __init__(self, server, username, password, project=None,
                 api_token=None, login=True):
        self.server = server
        self.api_token = api_token
        self.username = username
        self.password = password
        self._projects = None
        self._pid = project
        self._cache = {}
        self.cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPCookieProcessor(self.cookies))
        if login:
            self.login()

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['cookies']
        del d['opener']
        return d

    def __setstate__(self, d):
        self.__dict__ = d
        self.cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPCookieProcessor(self.cookies))
        self.login()

    def djangourl(self, path):
        """ Expects the path to lead with a slash '/'. """
        assert path[0] == '/'
        return self.server + path

    def _process_csrf(self, request):
        cookie = None
        for c in self.cookies:
            if c.name > 8 and c.name[:9] == 'csrftoken':
                cookie = c
        if cookie is None:
            return False
        index = None
        for (i, (k, v)) in enumerate(self.opener.addheaders):
            if k == 'X-CSRFToken':
                index = i
        if index is not None:
            self.opener.addheaders.pop(index)
        self.opener.addheaders.append(
            ('X-CSRFToken', cookie.value))
        return True

    def login(self):
        # add basic authentication for older catmaid installs
        bs = base64.encodestring(
            '%s:%s' % (self.username, self.password)).replace('\n', '')
        self.opener.addheaders.append(('Authorization', 'Basic %s' % bs))
        has_csrf = False
        if self.api_token is None:
            warnings.warn(
                'No api_token provided, fetching this takes a few seconds')
            r = self.fetch('/', read=False)
            # check for csrf
            has_csrf = self._process_csrf(r)
        if has_csrf:
            self._process_csrf(r)
            if self.api_token is None:
                api_data = urllib.urlencode(
                    {'username': self.username, 'password': self.password})
                r = self.fetch('/api-token-auth/', api_data, read=False)
                self._process_csrf(r)
                self.api_token = json.loads(r.read())['token']
        try:
            login_data = urllib.urlencode(
                {'name': self.username, 'pwd': self.password})
            r = self.fetch('/accounts/login', login_data, read=False)
        except urllib2.HTTPError as e:
            if self.api_token is None or e.getcode() != 403:
                raise e
        if self.api_token is not None:
            self.opener.addheaders.append(
                ('X-Authorization', 'Token %s' % self.api_token))
        return

    def fetch(self, url, post=None, read=True):
        """ Fetch a url with optional post data (dict) """
        if url[:4] != 'http':
            url = self.djangourl(url)
        if post:
            if not isinstance(post, (str, unicode)):
                post = urllib.urlencode(post)
            request = self.opener.open(url, post)
        else:
            request = self.opener.open(url)
        if read:
            return request.read()
        return request

    def fetchJSON(self, url, post=None):
        """
        Provides a JSON with information from provided url.

        Parameters
        ----------
        self: Connection object
        url: The url of desired information
        post:

        Returns
        -------
        JSON with associated data from url
        """
        response = self.fetch(url, post=post)
        if not response:
            return
        r = json.loads(response)
        if isinstance(r, dict) and 'error' in r:
            logging.error("ERROR : %s" % r['error'])
        else:
            return r

    def fetch_projects(self):
        if self._projects is None:
            projects = self.fetchJSON('/projects')
            for project in projects:
                if 'pid' not in project:
                    project['pid'] = project['id']
            self._projects = projects
        return self._projects

    projects = property(fetch_projects)

    def find_pid(self, title):
        if title is None:
            if self._pid is None:
                raise ValueError("A project name or id must be provided")
            elif isinstance(self._pid, int):
                return self._pid
            else:
                self._pid = self.find_pid(self._pid)
                return self._pid
        if isinstance(title, int):
            return title
        for p in self.projects:
            if p['title'] == title:
                return p['pid']
        logging.critical("Project with title %s not found" % title)
        raise LookupError("Project with title %s not found" % title)

    def set_project(self, project):
        self._pid = self.find_pid(project)

    def find_stackids(self, project=None):
        """
        Returns a list of all stack ids associated with a given project.

        Parameters
        ----------
        self: Connection object
        project: Project id

        Returns
        -------
        List of stack ids
        """
        pid = self.find_pid(project)
        stacks_JSON = self.fetchJSON('/{}/stacks'.format(pid))
        return [s[u'id'] for s in stacks_JSON]

    def skeleton(self, sid, project=None):
        pid = self.find_pid(project)
        skel = self.fetchJSON('/{}/skeleton/{}/json'.format(pid, sid))
        if isinstance(skel, dict):
            # catmaid1 skeleton
            skel['id'] = sid
            skel['neuron']['id'] = self.neuron_id(sid, project)
            try:
                skel['neuron']['annotations'] = self.annotation_table(
                    skel['neuron']['id'], project)
            except urllib2.HTTPError:
                # annotations probably don't exist for this server
                pass
        elif isinstance(skel, list):
            # catmaid2 skeleton
            skel.append(sid)
            skel.append(self.neuron_id(sid, project))
            skel.append(self.annotation_table(skel[-1], project))
        return skel

    def skeleton_ids(self, project=None, from_wiring_diagram=False):
        pid = self.find_pid(project)
        if from_wiring_diagram:
            d = self.wiring_diagram(pid)
            return [int(n['id']) for n in d['data']['nodes']]
        else:
            d = self.annotation_diagram(pid)
            return [
                int(n['id']) for n in d['nodes'] if n['class'] == 'skeleton']

    def neuron_id(self, sid, project=None):
        pid = self.find_pid(project)
        return int(self.fetchJSON(
            '/{}/skeleton/{}/neuronname'.format(pid, sid))['neuronid'])

    def neuron_ids(self, project=None, from_wiring_diagram=False):
        pid = self.find_pid(project)
        if from_wiring_diagram:
            # TODO find a better way to do this
            # perhaps grab all neuron ids, wiring diagram (sids)
            # and map of nid -> sid, then filter nids
            return [
                self.neuron_id(sid, pid) for sid
                in self.skeleton_ids(pid, from_wiring_diagram)]
        else:
            d = self.annotation_diagram(pid)
            return [int(n['id']) for n in d['nodes'] if n['class'] == 'neuron']

    def wiring_diagram(self, project=None, save=False, sids=None):
        pid = self.find_pid(project)
        diagram = self.fetchJSON('/{}/wiringdiagram/json'.format(pid))
        return algorithms.wiring.diagram_filter(diagram,
            sids, save)

    def annotation_diagram(self, project=None):
        pid = self.find_pid(project)
        return self.fetchJSON('/{}/annotationdiagram/nx_json'.format(pid))

    def nid_to_sid_map(self, project=None):
        pid = self.find_pid(project)
        d = self.annotation_diagram(pid)
        nid_to_sid = {}
        for l in d['links']:
            sn = d['nodes'][l['source']]
            tn = d['nodes'][l['target']]
            if sn['class'] != 'neuron' or tn['class'] != 'skeleton':
                # this link is not between a neuron and skeleton
                continue
            nid_to_sid[sn['id']] = nid_to_sid.get(sn['id'], []) + [tn['id'], ]
        return nid_to_sid

    def sid_to_nid_map(self, project=None):
        nid_to_sid = self.nid_to_sid_map(project)
        sid_to_nid = {}
        for nid in nid_to_sid:
            for sid in nid_to_sid[nid]:
                if sid not in sid_to_nid or sid_to_nid[sid] == nid:
                    sid_to_nid[sid] = nid
                else:
                    raise ValueError(
                        "Skeleton[%s] has two neurons %s, %s" % (
                            sid, nid, sid_to_nid[sid]))
        return sid_to_nid
    
    def search_string( self, search_query, class_name=None ):
        """ Returns the results from performing a search on the 
        current catmaid server
        
        Results come in a list of search results.
        each result will have a member 'class_name' which can be 
        passed to the function to pare down all other results.
        Some possible class names are:
        'neuron','annotation','label'

        Arguments:
            search_query: susbtring to search for
            class_name: type of class to search for, can be a list
                        leave blank to return all class types
        Returns:
            list of search results
        """
        pid = self.find_pid(None)
        js_result = self.fetchJSON('{}{}/search?pid={}&substring={}'.format(
                                        self.server,pid,
                                        pid,search_query))
        if class_name is not None:
            if isinstance(class_name, str):
                # one class name, turn it into a list of 
                # class_names
                class_name = [class_name]
            
            # parse down results based on class_names given
            return [res for res in js_result if res['class_name'] in
                    class_name]
        else:
            # if no class_name specified return all results
            return js_result
    
    def get_connector_info( self, con_id ):
        """
        Returns information about a given connector id (or list of connector
        ids)
        """
        if isinstance(con_id,int):
            con_id = str(con_id)
        if isinstance(con_id,str):
            con_id = [con_id]

        pid = self.find_pid(None)
        url = '{}{}/connector/skeletons'.format(self.server,pid)
        pst = 'connector_ids[0]=%s' % con_id[0]
        
        for i in range(1, len(con_id)):
            pst += '&connector_ids[%d]=%s' % (i, con_id[i])

        js_result = self.fetchJSON(url,pst)
        return js_result

    def annotations(self, project=None, limit=None):
        """Return a list of neuron annotations of the format
        ['neuron name', [list of annotations], [skeleton ids], neuron id]
        """
        pid = self.find_pid(project)
        if limit is not None:
            data = urllib.urlencode({'iDisplayLength': limit})
        else:
            data = None
        js = self.fetchJSON(
            '/{}/neuron/table/query-by-annotations'.format(pid), post=data)
        if limit is None and len(js['aaData']) != js['iTotalRecords']:
            return self.annotations(project, js['iTotalRecords'])
        return js['aaData']

    def annotation_table(self, neuron_id=None, project=None, limit=None):
        """Return a list of neuron annotations of the format
        ['annotation', 'last-used', use_count, id_of_last_user, annotation_id]
        """
        pid = self.find_pid(project)
        post_data = {}
        if neuron_id is not None:
            post_data['neuron_id'] = neuron_id
        if limit is not None:
            post_data['iDisplayLength'] = limit
        if len(post_data):
            post = urllib.urlencode(post_data)
        else:
            post = None
        js = self.fetchJSON(
            '/{}/annotations/table-list'.format(pid), post=post)
        if limit is None and len(js['aaData']) != js['iTotalRecords']:
            return self.annotation_table(
                neuron_id=neuron_id, project=project,
                limit=js['iTotalRecords'])
        return js['aaData']

    def adjacency_matrix(self, project=None, save=False, sids=None):
        return algorithms.wiring.to_adjacency_matrix(
            self.wiring_diagram(project, save, sids), save)

    def user_stats(self, project=None):
        """Only works for catmaid1 server"""
        pid = self.find_pid(project)
        return self.fetchJSON('/{}/stats-user-history'.format(pid))

    def fetch_tile_url(self, row, column, z_index, zoom=0, tiletype=4,
                       xyz_format=None, stack_id=None):
        """This function returns the URL for a specific tile (row, column) at
           a specific z index.

           Please refer to the following link for specific documentation on
           the various catmaid tiletypes:
           http://catmaid.readthedocs.io/en/stable/tile_sources.html

           Function Arguments:
           Row = The specific row number for desired tile
           Column = The specific column number for desired tile
           z_index = The z index of desired tile
           tiletype = the tiletype identification number (1-9)
           xyz_format = The formatting of the data structure used primarily
                        for tiletypes 6 and 8, The format is either 'xy',
                        'xz', 'yz', or 'zy'. The last two formats, 'yz' and
                        'zy' return the same result.
           stack_id = The identification number that corresponds to the stack
                      in a specific project.
           catmaid_url = A url to the desired catmaid database. This is only
                         required when fetching with tiletype 3.
           """
        # Set stack info
        if stack_id is not None:
            stack_info = self.stack_info()[stack_id]
        else:
            if len(self.stack_info().keys()) > 1:
                raise Exception("Must specify desired stack. More than 1"
                                "stack in project.")
            else:
                stack_info = self.stack_info().values()[0]
                stack_id = stack_info[u'sid']
        if len(stack_info['mirrors']) > 1:
            print("WARNING: More than 1 mirror information present in stack "
                  "info. Grabbing image dimensions from first mirror")
        mirror_info = stack_info[u'mirrors'][0]
        tile_width = mirror_info[u'tile_width']
        tile_height = mirror_info[u'tile_height']
        max_row = (stack_info[u'dimension'][u'y'] / tile_height) - 1
        max_col = (stack_info[u'dimension'][u'x'] / tile_width) - 1
        if not 0 <= row <= max_row:
            raise errors.InvalidUrl("Invalid row %s" % row)
        if not 0 <= column <= max_col:
            raise errors.InvalidUrl("Invalid column %s" % row)
        info = {'base': str(mirror_info[u'image_base']), 'z_index': z_index,
                'row': row, 'column': column, 'zoom': zoom,
                'ext': str(mirror_info[u'file_extension']),
                'tile_width': tile_width, 'tile_height': tile_height,
                'project_id': stack_info[u'pid'],
                'stack_id': stack_id, 'row_by_height': (row * tile_height),
                'col_by_width': (column * tile_width),
                'catmaid_url': self.server, 'zoomlevel': (2**(-zoom))}
        tile_types = {
            1: '{base}{z_index}/{row}_{column}_{zoom}.{ext}',
            2: ('{base}?x={col_by_width}&y={row_by_height}&z={z_index}&width='
                '{tile_width}&height={tile_height}&scale={zoomlevel}'
                '&row={row}&col={column}'),
            3: ('{catmaid_url}{project_id}/stack/{stack_id}/tile?x='
                '{col_by_width}&y={row_by_height}&z={z_index}&width='
                '{tile_width}&height={tile_height}&scale={zoomlevel}&row={row}'
                '&col={column}&file_extension={ext}&basename={base}&type=all'),
            4: '{base}{z_index}/{zoom}/{row}_{column}.{ext}',
            5: '{base}{zoom}/{z_index}/{row}/{column}.{ext}',
            '6_xy': ('{base}{tile_width}_{tile_height}/{col_by_width}_'
                     '{row_by_height}_{z_index}/{ext}'),
            '6_xz': ('{base}{tile_width}_{tile_height}/{col_by_width}_'
                     '{z_index}_{row_by_height}/{ext}'),
            '6_yz': ('{base}{tile_width}_{tile_height}/{z_index}_'
                     '{row_by_height}_{col_by_width}/{ext}'),
            7: ('{base}largeDataTileSource/{tile_width}/{tile_height}/{zoom}/'
                '{z_index}/{row}/{column}.{ext}'),
            '8_xy': '{base}xy/{zoom}/{column}_{row}_{z_index}',
            '8_xz': '{base}xz/{zoom}/{column}_{z_index}_{row}',
            '8_yz': '{base}yz/{zoom}/{z_index}_{row}_{column}',
            9: '{base}{z_index}/{row}_{column}_{zoom}.{ext}'}
        if tiletype == 8 or tiletype == 6:
            raise NotImplementedError
            """if xyz_format is None:
                raise Exception("Format must be provided for DVID Imagetiles!")
            elif xyz_format == 'xy' or xyz_format == 'xz':
                tile_name = '{}_{}'.format(tile_type, xyz_format)
                return tile_types[tile_name].format(**info)
            elif xyz_format == 'zy' or xyz_format == 'yz':
                return tile_types[8_yz].format(**info)
            else:
                raise Exception("XYZ Format not recognised!")
        elif tiletype == 6:
            if xyz_format is None:
                raise Exception("Format must be provided for DVID Imagetiles!")
            elif xyz_format == 'xy' or xyz_format == 'xz':
                tile_name = '{}_{}'.format(tile_type, xyz_format)
                return tile_types[tile_name].format(**info)
            elif xyz_format == 'zy' or xyz_format == 'yz':
                return tile_types[6_yz].format(**info)
            else:
                raise Exception("XYZ Format not recognised!")"""
        else:
            url = tile_types[tiletype].format(**info)
        if url[:4] != 'http':
            url = self.djangourl(url)
        return url

    def fetch_tile(self, row=None, column=None, z_index=None, zoom=0,
                   tiletype=4, xyz_format=None, stack_id=None, url=None):
        """This function will return a single catmaid tile (row, column).
           If a URL is provided for the tile, this function does not requires
           any further information. If no URL is provided, this function
           requires a row, column, and z index."""
        if url is None:
            if row is None:
                raise Exception('Must provide row if not providing URL')
            if column is None:
                raise Exception('Must provide column if not providing URL')
            if z_index is None:
                raise Exception('Must provide z index if not providing URL')

            url = self.fetch_tile_url(row, column, z_index, zoom,
                                      tiletype, xyz_format, stack_id)
        tile = self.fetch(url)
        return numpy.array(Image.open(StringIO(tile)))

    def openURL(self, project=None, neuron=None, x=None, y=None, z=None,
                zoom=0, skID=None, nodeID=None, stack_index=0,
                openBrowser=False):
                """Returns a url using user input"""
                if project is None:
                    if self._pid is None:
                        logging.critical("need Project")
                        raise Exception("need Project")
                    else:
                        project = self._pid
                if project is int:
                    pid = project
                else:
                    pid = self.find_pid(project)
                if (neuron or (x and y and z)) is None:
                    logging.critical("Neuron OR (x,y,z) are needed to call"
                                     "openURL")
                    raise Exception("missing Neuron or (x,y,z)")
                elif(nodeID and not neuron):
                    logging.critical("Need neuron if nodeID is defined")
                    raise Exception("need neuron if nodeID is used")
                elif neuron and not nodeID:
                    if(x and y and z) is None:
                        nodeID = neuron.root
                    else:
                        neuron = None

                if(x and y and z and not neuron):
                    url = '{}/?pid={}&zp={}&yp={}&xp={}&tool=tracingtool'\
                          '&sid0={}&s0={}'.format(self.server, pid, z, y, x,
                                                  self.find_stackids(pid)[stack_index],
                                                  zoom)
                elif(neuron and nodeID):
                    [x, y, z] = [neuron.skeleton['vertices'][str(nodeID)]['x'],
                                 neuron.skeleton['vertices'][str(nodeID)]['y'],
                                 neuron.skeleton['vertices'][str(nodeID)]['z']]
                    skID = neuron.skeleton['id'] if skID is None else skID
                    url = '{}/?pid={}&zp={}&yp={}&xp={}&tool=tracingtool'\
                          '&active_skeleton_id={}&active_node_id={}'\
                          '&sid0={}&s0={}'.format(self.server, pid, z, y,
                                                  x, skID, nodeID,
                                                  self.find_stackids(pid)[stack_index],
                                                  zoom)
                if(openBrowser):
                    webbrowser.open_new(url)
                return url

    def stack_info(self, project=None):
        '''
        Returns a dictionary of image stacks in an catmaid project and
            dictionaries of associated stack qualities.
        id:{
            'resolution':{
                'x':
                'y':
                'z':}
            'file_extension':
            ...}
        '''
        pid = self.find_pid(project)
        if 'stack_info' in self._cache and pid in self._cache['stack_info']:
            return self._cache['stack_info'][pid]
        if 'stack_info' not in self._cache:
            self._cache['stack_info'] = {}
        stacks = self.fetchJSON('/{}/stacks'.format(pid))
        info = {}
        for stack in stacks:
            stackid = stack['id']
            info.update({stackid:
                         self.fetchJSON('/{}/stack/{}/info'.format(pid,
                                                                   stackid))})
        self._cache['stack_info'][pid] = info
        return info

    def clear_cache(self):
        self._cache = {}


def connect(
        server=None, user=None, password=None, project=None, api_token=None):
    """ connect using environment variables or user input if
    environment variables do not exist"""
    if server is None:
        k = 'CATMAID_SERVER'
        if k not in os.environ:
            server = str(raw_input("Enter Catmaid Server: "))
            if not server.startswith('http'):
                server = 'http://'+server
            if server == "":
                logging.critical("Server must not be empty.")
                raise ValueError("Server cannot be empty.")
        else:
            server = os.environ[k]
    if project is None:
        k = 'CATMAID_PROJECT'
        if k not in os.environ:
            project = str(raw_input("Enter Catmaid Project: "))
            if project == "":
                logging.critical("Project must not be empty.")
                raise ValueError("Project cannot be empty.")
        else:
            project = os.environ[k]
    if user is None:
        k = 'CATMAID_USER'
        if k not in os.environ:
            user = str(raw_input("Enter Catmaid Username: "))
            if user == "":
                logging.critical("User must not be empty.")
                raise ValueError("User cannot be empty.")
        else:
            user = os.environ[k]
    if password is None:
        k = 'CATMAID_PASSWORD'
        if k not in os.environ:
            password = getpass.getpass("Enter Catmaid Password: ")
            if password == "":
                logging.critical("Password cannot be empty.")
                raise ValueError("Password cannot be empty.")
        else:
            password = os.environ[k]
    if api_token is None:
        k = 'CATMAID_API_TOKEN'
        if k in os.environ:
            api_token = os.environ[k]
    if isinstance(project, (str, unicode)) and project.isdigit():
        project = int(project)
    return Connection(
        server, user, password, project=project, api_token=api_token)
