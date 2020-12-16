import abc
import logging
from copy import copy
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

    def latency(self, source: Node, destination: Node, use_coordinates=False) -> float:
        if use_coordinates:
            return source.distance_to(destination)
        return self.route(source, destination).rtt / 2

    def route(self, source, destination, use_mode: bool = False) -> Route:
        """
        Returns the route from source to destination.
        :param source: the starting point of the route
        :param destination: the destination point of the route
        :param use_mode: whether to use the mode of the latency distributions along the path or a sample
        :return:
        """
        k = (source, destination)

        if k not in self._route_cache:
            self._route_cache[k] = self._resolve_route(source, destination)

        if not use_mode:
            route = copy(self._route_cache[k])
            self._update_rtt(route)
        else:
            route = self._route_cache[k]

        return route

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
        route = Route(source, destination, path=path)
        self._update_rtt(route, use_mode=True)
        return route

    def _update_rtt(self, route: Route, use_mode: bool = False):
        latency: float = 0
        for i in range(len(route.path)-1):
            edge_data = self.get_edge_data(route.path[i], route.path[i + 1])
            if 'connection' in edge_data and isinstance(edge_data['connection'], Connection):
                # the edge has a connection object attached
                # use either get_latency() or get_mode_latency() respectively to calculate latency
                connection: Connection = edge_data['connection']
                latency += connection.get_mode_latency() if use_mode else connection.get_latency()
            elif 'latency' in edge_data:
                # the edge has a constant latency attached (i.e., in case of inet datasets)
                latency += edge_data['latency']
        route.rtt = latency * 2

    def add(self, cell):
        """
        Materializes a cell or scenario into the topology.

        :param cell: the cell or scenario to create
        :return: the topology for chaining
        """
        cell.materialize(self)
        return self
