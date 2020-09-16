import os
from typing import List

import networkx as nx

from ether.inet.fetch import Measurement

graph_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'graphs'))


def load_latest(graph: nx.DiGraph, source, *args, **kwargs):
    return load_tagged(graph, source, 'latest', *args, **kwargs)


def load_tagged(graph: nx.DiGraph, source, tag, *args, **kwargs):
    path = os.path.join(graph_directory, f'{source}_{tag}.graphml')
    print('loading from', path)
    return load_from_file(graph, path, *args, **kwargs)


def load_from_file(graph: nx.DiGraph, file_path, node_prefix='internet_'):
    inet_graph: nx.Graph = load_graph(file_path)

    for src, dst, data in inet_graph.edges.data():
        graph.add_edge(node_prefix + src, node_prefix + dst, **data)


def fetch_to_graph(graph: nx.DiGraph, module, *args, **kwargs):
    add_to_graph(graph, module.fetch(), *args, **kwargs)


def add_to_graph(graph: nx.DiGraph, measurements: List[Measurement], node_prefix=''):
    for m in measurements:
        if m.source == m.destination:
            continue

        src = f'{node_prefix}{m.source}'
        dst = f'{node_prefix}{m.destination}'

        graph.add_edge(src, dst, latency=m.avg)


def save_graph(g: nx.Graph, path: str) -> None:
    nx.write_graphml(g, path=path)


def load_graph(path: str) -> nx.Graph:
    return nx.read_graphml(path)
