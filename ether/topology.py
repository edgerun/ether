import abc
import logging
from typing import Dict, Tuple

import networkx as nx

from ether.core import Node, Link, Connection, Route, NetworkNode
from ether.inet.graph import load_latest

logger = logging.getLogger(__name__)


class Template(abc.ABC):
    """
    Structures that can be materialized into a topology need to implement this method. It connects the template to
    the topology.
    """
    def materialize(self, topology: 'Topology'):
        ...


class Topology(nx.DiGraph):

    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data, **attr)
        self._route_cache: Dict[Tuple[NetworkNode, NetworkNode], Route] = dict()

    def conn(self, *args, **kwargs):
        return self.add_connection(*args, **kwargs)

    def add_connection(self, connection: Connection, directed=False):
        if isinstance(connection.source, Node) and isinstance(connection.target, Node):
            raise ValueError('Cannot have direct Node-to-Node connections')

        self.add_edge(connection.source, connection.target, directed=directed, connection=connection)
        if directed is False:
            self.add_edge(connection.target, connection.source, directed=directed, connection=connection)

    def path(self, source, destination):
        return nx.shortest_path(self, source, destination)

    def route(self, source, destination) -> Route:
        k = (source, destination)

        if k not in self._route_cache:
            self._route_cache[k] = self._resolve_route(source, destination)

        return self._route_cache[k]

    def get_nodes(self):
        return [n for n in self.nodes if isinstance(n, Node)]

    def get_links(self):
        return [n for n in self.nodes if isinstance(n, Link)]

    def load_inet_graph(self, source):
        """
        Loads a static internet latency graph into the current topology. For example:

        topo.load_inet_graph('cloudping')

        :param source: the source. find available sources in `ether.inet.fetch.sources`.
        """
        load_latest(self, source)

    def _resolve_route(self, source, destination) -> Route:
        path = self.path(source, destination)
        hops = [hop for hop in path if isinstance(hop, Link)]

        rtt = 0
        # TODO: get Connection object from edges, de-duplicate undirected edges, and extract latency for RTT
        #  edges = self.edges.data(data='connection', nbunch=path)

        return Route(source, destination, hops=hops, rtt=rtt)

    def add(self, cell):
        """
        Materializes a cell or scenario into the topology.

        :param cell: the cell or scenario to create
        :return: the topology for chaining
        """
        cell.materialize(self)
        return self
