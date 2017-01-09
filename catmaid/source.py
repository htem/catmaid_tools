'''
Source Class is a Skeleton/Neuron source, loading skeletons/neurons from
a local cache(FileSource) or from a server(ServerSource).
'''
import glob
import json
import logging
import os
import re

from . import connection
from . import neuron
from .algorithms import population
from . import algorithms

# By default, skeletons will be saved in a .json named by skeleton id
sk_format = "{}.json"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SkeletonReadException(Exception):
    pass


def get_source(skel_source=None, cache=True, dict_skeletons=True,
               ignore_none_skeletons=False):
    '''
    Basic Source Handler, returns either ServerSource or FileSource based
    on parameters passed.
    Parameters
    ----------
    skel_source: Directory name, or Connection object. default None
         if skel_source is None or a Connection object, return a ServerSource
         if skel_source is a directory name, a FileSource is returned.
    cache: boolean. default True
         allows loaded skeletons and neurons to be cached in self._cache
         useful if you do not want to continually load neurons or skeletons.
    dict_skeletons: boolean. default True
         Forces skeletons to be loaded in the catmaid1 format. Will take list
         skeletons and convert them into the catmaid1 dictionary form. Useful
         as it allows functions meant to be used on catmaid1 skeletons on the
         catmaid2 skeletons.
    Returns
    -------
    ServerSource or FileSource based on arg
    '''
    if skel_source is None:
        logger.info("Attempting to connect to a ServerSource")
        # attempts to create connection object from environ variables
        return ServerSource(skel_source, cache, dict_skeletons,
                            ignore_none_skeletons)
    if isinstance(skel_source, (str, unicode)):
        if len(skel_source) > 4 and skel_source[:4] == 'http':
            logger.info("Attempting to create a ServerSource")
            conn = connection.connect(skel_source)
            return ServerSource(
                conn, cache, dict_skeletons, ignore_none_skeletons)
        else:
            logger.info("Attempting to create a FileSource")
            return FileSource(skel_source, cache, dict_skeletons,
                              ignore_none_skeletons)
    elif isinstance(skel_source, connection.Connection):
        logger.info("Attemping to connect to a ServerSource")
        # creates serversource with skel_source if it is a connection object
        return ServerSource(skel_source, cache, dict_skeletons,
                            ignore_none_skeletons)
    else:
        logger.critical("Must initialize with a directory"
                         " or connection object")
        raise ValueError("must be a Directory Name or Connection Object")


class Source(object):
    def __init__(self, skel_source, cache=True, dict_skeletons=True,
                 ignore_none_skeletons=False):
        if cache:
            self._cache = {}
        else:
            self._cache = None
        self._skel_source = skel_source
        self._dict_skeletons = dict_skeletons
        self._ignore_none_skeletons = ignore_none_skeletons

    def skeleton_ids_iter(self):
        """Defined in Child Class"""
        logger.critical("function defined in child class"
                         " FileSource or ServerSource")
        raise NotImplementedError("Must call File or Server Source")

    def skeleton_ids(self):
        """returns a list of all skeleton IDs on the source"""
        return list(self.skeleton_ids_iter())

    def _load_skeleton(self, sk_id):
        """Defined in child class"""
        logger.critical("function defind in child class"
                         " FileSource or ServerSource")
        raise NotImplementedError("Must call File or Server Source")

    def get_skeleton(self, sk_id):
        """Defined in child class"""
        if isinstance(sk_id, (list, tuple)):
            return [self.get_skeleton(i) for i in sk_id]
        logger.debug("fetching skeleton %s", sk_id)
        if self._cache is None:  # don't cache
            skel = self._load_skeleton(sk_id)
        elif sk_id in self._cache:
            logger.debug("returning cached skeleton: %s", sk_id)
            return self._cache[sk_id].skeleton
        else:
            skel = self._load_skeleton(sk_id)
        if self._dict_skeletons:
            if isinstance(skel, list):
                skel = algorithms.skeleton_json_new_to_old.convert_new_to_old(
                    skel)
        if self._cache is not None:
            logger.debug("caching skeleton %s", sk_id)
            # cache skeletons as neurons to save property caches
            if skel is None:
                logger.error("Cannot cache None skeleton %s", sk_id)
            else:
                self._cache[sk_id] = neuron.Neuron(skel)
        return skel

    def get_neuron(self, sk):
        """Fetches Single Neuron From SkelSource"""
        if isinstance(sk, (list, tuple)):
            return [self.get_neuron(i) for i in sk]
        if isinstance(sk, (str, unicode, int)):
            if self._cache is not None and sk in self._cache:
                return self._cache[sk]
            sk = self.get_skeleton(sk)
        return neuron.Neuron(sk)

    def all_skeletons_iter(self):
        for sk_id in self.skeleton_ids_iter():
            sk = self.get_skeleton(sk_id)
            if sk is None:
                if self._ignore_none_skeletons:
                    continue
                else:
                    raise SkeletonReadException('skeleton {} is '
                                                'Nonetype!'.format(sk_id))
            yield self.get_skeleton(sk_id)

    def all_skeletons(self):
        """Fetches all skeletons from the skel_source"""
        return list(self.all_skeletons_iter())

    def save_skels(self, path=None, skels=None, fn_format=None):
        if fn_format is None:
            fn_format = sk_format
        if path is None:
            path = 'skeletons'
        path = os.path.realpath(os.path.expanduser(path))
        if not os.path.exists(path):
            os.makedirs(path)
        if skels is None:
            skels = self.all_skeletons_iter()
        logger.debug("saving skeletons")
        for sk in skels:
            # get skeleton
            if isinstance(sk, int):
                sk_id = sk
                sk = self.get_skeleton(sk)
            else:
                # get id
                if isinstance(sk, dict):
                    sk_id = sk['id']
                elif isinstance(sk, list):
                    sk_id = sk[5]
                else:
                    raise ValueError("Invalid skeleton type: %s" % type(sk))
            logger.debug("saving skeleton %s", sk_id)
            # make filename
            fn = os.path.join(path, fn_format.format(sk_id))
            # save
            with open(fn, 'w') as f:
                json.dump(sk, f)

    def wipe_skeletons(self, path, fn_format=None):
        '''
        Removes all numeric filenames matching fn_format variable from
            the directory provided by path.
        '''
        if self._cache is not None:
            self._cache = {}
        if fn_format is None:
            fn_format = sk_format
        sk_id_regex = fn_format.format('([0-9]+)')
        if os.path.isdir(path):
            dirfiles = [f for f in os.listdir(path)
                        if os.path.isfile(os.path.join(path, f))]
            for fil in dirfiles:
                if re.match(sk_id_regex, os.path.basename(fil)):
                    os.remove(os.path.join(path, fil))

    def all_neurons(self):
        """Fetches all Neurons from the source"""
        return list(self.all_neurons_iter())

    def all_neurons_iter(self):
        """Fetches all Neurons from the source iteratively"""
        for sk in self.all_skeletons_iter():
            yield self.get_neuron(sk)

    def where(self, test=None, function=None, return_neurons=False):
        """
        Iterator that returns all neurons where test evalues to true.
        If function is not None then runs a function to extract a result
        from each neuron. If function is a string (or unicode) than that
        attribute is fetched for each neuron.
        If function is None, where returns neurons
        If return_neurons is true, return tuples of (neuron, function(neuron))
        this is only really useful if function is not None.
        """
        if test is None:
            test = lambda n: True
        if isinstance(function, (str, unicode)):  # attribute
            extract = lambda n: getattr(n, function)
        if function is not None:
            extract = function
        else:
            extract = lambda n: n
        for n in self.all_neurons_iter():
            if test(n):
                if return_neurons:
                    yield n, extract(n)
                else:
                    yield extract(n)

    def pairs(self, function, testa=None, testb=None, same=False,
              return_neurons=True):
        """
        Compute some function on pairs of neurons.
        function of form = function(neuron_a, neuron_b)
        testa/b when not None should be a function that returns True/False
        to see if they should be included in the pairs.
        If return_neurons is True, return tuples of (neuron_a, neuron_b, r)
        where r is the result of the function evaluated on a and b.
        """
        for na in self.where(testa):
            for nb in self.where(testb):
                if na is nb and not same:
                    continue
                if return_neurons:
                    yield na, nb, function(na, nb)
                else:
                    yield function(na, nb)

    # TODO find a place for these, or make more general helper functions
    def neuron_overlap(self, sk_a, sk_d, s=1000., sig=10000.):
        n_a = self.get_neuron(sk_a)
        n_d = self.get_neuron(sk_d)
        ov = population.synapses.skeleton_overlap(n_a, n_d, s, sig)
        return ov

    def list_overlap(self, sk_list, s=1000., sig=10000.):
        ov_dict = population.synapses.overlap_list(self, sk_list)
        return ov_dict

    def get_tags(self, save=True):
        """gets all tags and saves file if save==True"""
        population.all_tags.get_tags(self, save)

    def unlabeled_leaves(self, save=True):
        """gets all unlabeled leaves and saves to file if save==True"""
        population.unlabeled_leaves.get_unlabeled_leaves(self, save=save)


class ServerSource(Source):
    def __init__(self, skel_source=None, cache=True, dict_skeletons=True,
                 ignore_none_skeletons=False):
        Source.__init__(self, skel_source, cache, dict_skeletons,
                        ignore_none_skeletons)
        if self._skel_source is None:
            self._skel_source = connection.connect()

    def _load_skeleton(self, sk_id):
        sk = self._skel_source.skeleton(sk_id)
        if isinstance(sk, dict):
            sk['id'] = sk_id
        return sk

    def skeleton_ids_iter(self):
        """iterates through the skeleton_ids"""
        for sk_id in self._skel_source.skeleton_ids():
            yield int(sk_id)

    # TODO find a place for this
    def get_graph(self, sk_list=None, directed=False):
        if sk_list is None:
            adj, sk_list = self._skel_source.adjacency_matrix()
        else:
            adj, sk_list = population.graph_tools.get_adj_mat(
                self, sk_list, directed)
        return adj, sk_list


class FileSource(Source):
    def __init__(self, skel_source=None, cache=True, dict_skeletons=True,
                 ignore_none_skeletons=False, fn_format=None):
        if fn_format is None:
            fn_format = sk_format
        Source.__init__(self, skel_source, cache, dict_skeletons,
                        ignore_none_skeletons)
        self.filename_format = fn_format
        self._skel_source = os.path.realpath(os.path.expanduser(skel_source))
        if not os.path.isdir(self._skel_source):
            raise IOError(
                "FileSource source directory %s is not a directory",
                self._skel_source)

    def _load_skeleton(self, sk_id):
        fn = os.path.join(
            self._skel_source, self.filename_format.format(sk_id))
        with open(fn, 'r') as f:
            sk = json.load(f)
            if isinstance(sk, dict) and ('id' not in sk):
                sk['id'] = sk_id
        return sk

    def skeleton_ids_iter(self):
        """iterates through the skeleton_ids"""
        file_names = glob.glob(os.path.join(
            self._skel_source, self.filename_format.format('*')))
        sk_id_regex = self.filename_format.format('([0-9]+)')
        for fn in file_names:
            m = re.findall(sk_id_regex, os.path.basename(fn))
            if len(m) != 1:
                raise Exception
            yield int(m[0])

    # TODO find a place for this
    def get_graph(self, sk_list=None, directed=False):
        adj, sk_list = population.graph_tools.get_adj_mat(
            self, sk_list, directed)
        return adj, sk_list
