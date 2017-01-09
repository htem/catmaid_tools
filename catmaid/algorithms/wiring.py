#!/usr/bin/env python
try:
    xrange
except NameError as e:
    xrange = range

def diagram_filter(diagram, sids=None, save=False):
    if sids is None:
        return diagram
    data = {'edges': [], 'nodes': []}
    in_graph_sids = set(sids)

    for e in diagram['data']['edges']:
        if e['source'] in sids or e['target'] in sids:
            data['edges'].append(e)
            in_graph_sids.add(e['source'])
            in_graph_sids.add(e['target'])
    
    for n in diagram['data']['nodes']:
        if n['id'] in in_graph_sids:
            data['nodes'].append(n)

    return {'data': data, 'dataSchema': diagram['dataSchema']}

def to_adjacency_matrix(wd, save=False):
    """
    returns adjacency matrix and corresponding skeleton list form wiring
    diagram
    """
    # get all skeletons
    sids = sorted([n['id'] for n in wd['data']['nodes']])
    nsids = len(sids)
    lookup = dict([(sids[i], i) for i in xrange(nsids)])
    # matrix: row & columns = skeletons, values = N connections
    m = []
    for i in xrange(nsids):
        m.append([0] * nsids)
    for e in wd['data']['edges']:
        # [source, target]
        m[lookup[e['source']]][lookup[e['target']]] = e['number_of_connector']
    # save matrix & skeleton list
    sids = [int(sid) for sid in sids]
    return m, sids
