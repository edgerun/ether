from typing import List

import networkx as nx

from ether.inet.fetch import Measurement


def fetch_to_graph(graph: nx.DiGraph, module, *args, **kwargs):
    add_to_graph(graph, module.fetch(), *args, **kwargs)


def load_to_graph(graph: nx.DiGraph, file_path, node_prefix=''):
    pass


def add_to_graph(graph: nx.DiGraph, measurements: List[Measurement], node_prefix=''):
    for m in measurements:
        if m.source == m.destination:
            continue

        src = f'{node_prefix}{m.source}'
        dst = f'{node_prefix}{m.destination}'

        graph.add_edge(src, dst, latency=m.avg)


def save_network_graph(g: nx.Graph, path: str) -> None:
    nx.write_graphml(g, path=path)


def read_network_graph(path: str) -> nx.Graph:
    return nx.read_graphml(path)
