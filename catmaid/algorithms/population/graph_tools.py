import networkx
'''
graph_tools meant to act as a medium between matlab, gephi and networkx.
inprogress
TODO:
    add DiGraph implementation
    catch self loops
    add file converters to matlab/gephi
'''


def get_graph(source, sk_list=None, directed=False):
    if sk_list is None:
        sk_list = source.skeleton_ids()
    nr_list = source.get_neuron(sk_list)
    if directed:
        G = networkx.DiGraph()
        # TODO Add DiGraph Implementation
    else:
        G = networkx.Graph()
        G.add_nodes_from(sk_list, bipartite=0)
        for nr in nr_list:
            G.add_nodes_from(nr.connectors.keys(), bipartite=1)
            for con in nr.connectors:
                G.add_edge(nr.sid, con, weight=1)
    proj_multi = networkx.projected_graph(G, set(sk_list), multigraph=True)
    G2 = networkx.Graph()
    unique_edges = set(proj_multi.edges())
    for u, v in unique_edges:
        w = proj_multi.edges().count((u, v))
        G2.add_edge(u, v, weight=w)
    return G2


def get_adj_mat(source, sk_list=None, directed=False):
    # TODO : self loops
    if sk_list is None:
        sk_list = source.skeleton_ids()
    graph = get_graph(source, sk_list, directed)
    n = len(sk_list)
    adj_mat = []
    for i in xrange(n):
        adj_mat.append([0] * n)
    for pair in graph.adjacency_iter():
        ind_a = sk_list.index(pair[0])
        for val in pair[1].keys():
            ind_b = sk_list.index(val)
            if ind_b in adj_mat[ind_a]:
                adj_mat[ind_a][ind_b] += pair[1][val]['weight']
            else:
                adj_mat[ind_a][ind_b] = pair[1][val]['weight']
    return adj_mat, sk_list
