import networkx as nx

from ether.graphs.model.matrix import LatencyMatrix


def create_latency_network_graph(matrix: LatencyMatrix) -> nx.Graph:
    G = nx.complete_graph(matrix.regions)

    for region in matrix.regions:
        for region_to in matrix.regions:
            if region != region_to:
                G[region][region_to]['weight'] = -1
                G[region_to][region]['weight'] = -1

    for region, latencies in matrix.latencies.items():
        for region_to, latency in latencies.items():
            if region != region_to:
                G[region][region_to]['weight'] = latency
                G[region_to][region]['weight'] = latency
    return G


def save_network_graph(g: nx.Graph, path: str) -> None:
    nx.write_graphml(g, path=path)


def read_network_graph(path: str) -> nx.Graph:
    return nx.read_graphml(path)
