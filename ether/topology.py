import logging
import time
from collections import deque, defaultdict
from typing import List, Dict, NamedTuple, Tuple

from ether.core import Node, Link, Route

logger = logging.getLogger(__name__)

BandwidthGraph = Dict[str, Dict[str, float]]


class Edge(NamedTuple):
    source: object
    target: object
    directed: bool = False


class Graph:
    """
    A graph.

    Example use for an example network topology:

    # a,b,c are three hosts in a LAN, and have up/downlink to the cloud
    n = ['a', 'b', 'c', 'down', 'up', 'cloud']

    edges = [
        Edge(n[0], n[1]),  # a,b
        Edge(n[1], n[2]),  # b,c
        Edge(n[0], n[2]),  # a,c
        Edge(n[3], n[0], True),  # down, a
        Edge(n[3], n[1], True),  # down, b
        Edge(n[3], n[2], True),  # down, c
        Edge(n[0], n[4], True),  # up, a
        Edge(n[1], n[4], True),  # up, b
        Edge(n[2], n[4], True),  # up, c
        Edge(n[4], n[5], True),  # up, cloud
        Edge(n[5], n[3], True),  # cloud, down
    ]

    t = Graph(n, edges)

    print(t.path(n[0], n[1]))  # ['a', 'b']
    print(t.path(n[0], n[5]))  # ['a', 'up', 'cloud']
    print(t.path(n[5], n[0]))  # ['cloud', 'down', 'a']
    """
    nodes: List
    edges: List[Edge]

    def __init__(self, nodes: List, edges: List[Edge]) -> None:
        super().__init__()
        self.nodes = nodes
        self.edges = edges
        self.index = None

    def create_index(self):
        index = defaultdict(list)

        for edge in self.edges:
            n1 = edge.source
            n2 = edge.target
            index[n1].append(n2)
            if not edge.directed:
                index[n2].append(n1)

        self.index = dict(index)

    def successors(self, node):
        return self.index[node] if self.index else self._successors_gen(node)

    def _successors_gen(self, node):
        for edge in self.edges:
            if edge.source == node:
                yield edge.target
            elif not edge.directed and edge.target == node:
                yield edge.source

    def path(self, source, destination) -> List:
        if source == destination:
            return []

        queue = deque([source])
        visited = set()
        parents = dict()

        while queue:
            node = queue.popleft()

            if node == destination:
                # found the destination, collect the path
                path = []
                cur = destination
                while cur:
                    path.append(cur)
                    cur = parents.get(cur)
                return list(reversed(path))

            visited.add(node)

            for successor in self.successors(node):
                if successor is node:
                    continue
                if successor in visited:
                    continue
                if successor not in parents:
                    parents[successor] = node
                queue.append(successor)

        return []


class Topology(Graph):
    """
    A specialized graph that uses ether concepts.
    """

    def __init__(self, nodes: List, edges: List[Edge]) -> None:
        super().__init__(nodes, edges)
        self._bandwidth_graph = None
        self._registry = None
        self._route_cache: Dict[Tuple[Node, Node], Route] = dict()

    def get_route(self, source: Node, destination: Node):
        k = (source, destination)

        if k not in self._route_cache:
            path = self.path(source, destination)
            hops = [node for node in path if isinstance(node, Link)]
            self._route_cache[k] = Route(source, destination, hops)

        return self._route_cache[k]

    def get_host(self, name):
        for node in self.nodes:
            if isinstance(node, Node) and node.name == name:
                return node

        return None

    def get_hosts(self):
        result = list()

        for node in self.nodes:
            if not isinstance(node, Node):
                continue

            result.append(node)

        return result

    def get_links(self):
        links = set()

        for edge in self.edges:
            if isinstance(edge.source, Link):
                links.add(edge.source)
            if isinstance(edge.target, Link):
                links.add(edge.target)

        return list(links)

    def get_all_nodes(self):
        nodes = set()

        for node in self.nodes:
            nodes.add(node)

        for edge in self.edges:
            nodes.add(edge.source)
            nodes.add(edge.target)

        return nodes

    def get_bandwidth_graph(self) -> BandwidthGraph:
        if self._bandwidth_graph is None:
            self._bandwidth_graph = self.create_bandwidth_graph_parallel()

        return self._bandwidth_graph

    def create_bandwidth_graph(self) -> BandwidthGraph:
        """
        From a topology, create the reduced bandwidth graph required by the ClusterContext.
        :return: bandwidth[from][to] = bandwidth in bytes per second
        """
        then = time.time()

        nodes = self.get_hosts()
        graph = defaultdict(dict)

        # route each node to each other and find the highest available bandwidth
        n = len(nodes)
        for i in range(n):
            for j in range(n):
                if i == j:
                    n1 = nodes[i].name
                    graph[n1][n1] = 1.25e+8  # essentially models disk read from itself as 1GBit/s
                    continue

                n1 = nodes[i]
                n2 = nodes[j]

                route = self.get_route(n1, n2)

                if not route.hops:
                    logger.debug('no route from %s to %s', n1, n2)
                    continue

                bandwidth = min([link.bandwidth for link in route.hops])  # get the maximal available bandwidth
                bandwidth = bandwidth * 125000  # link bandwidth is given in mbit/s: * 125000 = bytes/s

                graph[n1.name][n2.name] = bandwidth

        logger.info('creating bandwidth graph took %.4f seconds', (time.time() - then))

        return graph

    def create_bandwidth_graph_parallel(self, p=None) -> BandwidthGraph:
        import multiprocessing as mp
        """
        From a topology, create the reduced bandwidth graph required by the ClusterContext.
        :return: bandwidth[from][to] = bandwidth in bytes per second
        """
        if p is None:
            p = mp.cpu_count()

        then = time.time()

        nodes = self.get_hosts()

        # route each node to each other and find the highest available bandwidth
        n = len(nodes)

        parts = self.partition(list(range(n)), p)
        partitions = [(p, nodes) for p in parts]

        g = dict()

        with mp.Pool(p) as pool:
            part_results = pool.map(self._get_graph_part, partitions)
            for result in part_results:
                g.update(result)

        logger.info('creating bandwidth graph took %.4f seconds', (time.time() - then))

        return g

    def _get_graph_part(self, part):
        irange, nodes = part
        n = len(nodes)

        graph = defaultdict(dict)
        for i in irange:
            for j in range(n):
                if i == j:
                    n1 = nodes[i].name
                    graph[n1][n1] = 1.25e+8  # essentially models disk read from itself as 1GBit/s
                    continue

                n1 = nodes[i]
                n2 = nodes[j]

                route = self.get_route(n1, n2)

                if not route.hops:
                    logger.debug('no route from %s to %s', n1, n2)
                    continue

                bandwidth = min([link.bandwidth for link in route.hops])  # get the maximal available bandwidth
                bandwidth = bandwidth * 125000  # link bandwidth is given in mbit/s: * 125000 = bytes/s

                graph[n1.name][n2.name] = bandwidth

        return graph

    @staticmethod
    def partition(lst, n):
        division = len(lst) / n
        return [lst[round(division * i):round(division * (i + 1))] for i in range(n)]
