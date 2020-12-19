import inspect
import itertools
from collections import defaultdict, Iterable
from typing import Callable, List, Union

from srds import RandomSampler, ConstantSampler, IntegerTruncationSampler, ParameterizedDistribution

from ether.qos import latency
from ether.core import Node, Link, NetworkNode
from ether.topology import Topology, Connection

counters = defaultdict(lambda: itertools.count(0, 1))


class UpDownLink:
    bw_down: int
    bw_up: int
    backhaul: NetworkNode
    latency_dist: ParameterizedDistribution

    def __init__(self, bw_down, bw_up=None, backhaul='internet', latency_dist=None) -> None:
        super().__init__()
        self.bw_down = bw_down
        self.bw_up = bw_up if bw_up is not None else bw_down
        self.backhaul = backhaul
        self.latency_dist = latency_dist


class Cell:
    size: Union[int, RandomSampler]
    nodes = List[Union[Node, 'Cell', Callable]]
    entropy: float

    def __init__(self, nodes=None, size=None, entropy=None, backhaul=None) -> None:
        super().__init__()
        self.nodes = nodes
        self.size = size
        self.entropy = entropy
        self.backhaul = backhaul

    def materialize(self, topology: Topology, parent=None):
        raise NotImplementedError

    def generate(self) -> Topology:
        t: Topology = Topology()
        self.materialize(t)
        return t

    def _materialize(self, topology: Topology, c: object, backhaul=None):
        if isinstance(c, Iterable):
            for elem in c:
                self._materialize(topology, elem, backhaul)
            return

        if callable(c):
            c = c()  # TODO: propagate parameters

        if isinstance(c, Node):
            c = Host(c, backhaul=backhaul)
        elif isinstance(c, Cell):
            if backhaul:
                c.backhaul = backhaul

        c.materialize(topology, self)


class Host(Cell):
    node: Node
    link: Link

    def __init__(self, node: Node, link_bw=1000, backhaul=None) -> None:
        super().__init__(nodes=[node], backhaul=backhaul)
        self.node = node
        self.link_bw = link_bw
        self.link = Link(bandwidth=self.link_bw, tags={'name': 'link_%s' % node.name, 'type': 'node'})

    def materialize(self, topology: Topology, parent=None, latency_dist=latency.lan):
        node = self.nodes[0]

        topology.add_connection(Connection(node, self.link, latency_dist=latency_dist))
        if self.backhaul:
            topology.add_connection(Connection(self.link, self.backhaul))

    def __str__(self):
        return 'Host[node=%s, link=%s] -> %s' % (self.node, self.link, self.backhaul)

    def __repr__(self):
        return self.__str__()


class Client(Host):
    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(Node(name), **kwargs)


class Broker(Host):
    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(Node(name), **kwargs)


class LANCell(Cell):

    def __init__(self, nodes, backhaul=None) -> None:
        super().__init__(nodes=nodes, backhaul=backhaul)

    def _create_identity(self):
        self.nr = next(counters['lan'])
        self.name = 'lan_%d' % self.nr
        self.switch = 'switch_%s' % self.name

    def materialize(self, topology: Topology, parent=None):
        self._create_identity()

        for cell in self.nodes:
            self._materialize(topology, cell, self.switch)

        if self.backhaul:
            if isinstance(self.backhaul, UpDownLink):
                uplink = Link(self.backhaul.bw_up, tags={'type': 'uplink', 'name': 'up_%s' % self.name})
                downlink = Link(self.backhaul.bw_down, tags={'type': 'downlink', 'name': 'down_%s' % self.name})

                topology.add_connection(Connection(self.switch, uplink, latency_dist=self.backhaul.latency_dist),
                                        directed=True)
                topology.add_connection(Connection(downlink, self.switch), directed=True)

                topology.add_connection(Connection(self.backhaul.backhaul, downlink,
                                                   latency_dist=self.backhaul.latency_dist), directed=True)
                topology.add_connection(Connection(uplink, self.backhaul.backhaul), directed=True)

            else:
                topology.add_connection(Connection(self.switch, self.backhaul, latency_dist=latency.lan))


class SharedLinkCell(Cell):

    def __init__(self, nodes, shared_bandwidth=300, backhaul=None) -> None:
        super().__init__(nodes=nodes, backhaul=backhaul)
        self.shared_bandwidth = shared_bandwidth

    def _create_identity(self):
        self.nr = next(counters['shared'])
        self.name = 'shared_%d' % self.nr
        self.link = Link(bandwidth=self.shared_bandwidth, tags={'name': self.name, 'type': 'shared'})

    def materialize(self, topology: Topology, parent=None):
        self._create_identity()

        for cell in self.nodes:
            self._materialize(topology, cell, self.link)

        if self.backhaul:
            if isinstance(self.backhaul, UpDownLink):
                uplink = Link(self.backhaul.bw_up, tags={'type': 'uplink', 'name': 'up_%s' % self.name})
                downlink = Link(self.backhaul.bw_down, tags={'type': 'downlink', 'name': 'down_%s' % self.name})

                topology.add_connection(Connection(self.link, uplink, latency_dist=self.backhaul.latency_dist), True)
                topology.add_connection(Connection(downlink, self.link), True)

                topology.add_connection(Connection(self.backhaul.backhaul, downlink,
                                                   latency_dist=self.backhaul.latency_dist), directed=True)
                topology.add_connection(Connection(uplink, self.backhaul.backhaul), directed=True)

            else:
                topology.add_connection(Connection(self.link, self.backhaul))


class GeoCell(Cell):

    def __init__(self, size, density, nodes) -> None:
        super().__init__(nodes, size)
        if isinstance(density, int):
            self.density = ConstantSampler(density)
        elif isinstance(density, RandomSampler):
            self.density = IntegerTruncationSampler(density)
        else:
            raise ValueError('unknown density type %s' % type(density))

    def materialize(self, topology: Topology, parent=None):
        for i in range(self.size):
            n = self.density.sample()

            for c in self.nodes:
                if callable(c):
                    sig: inspect.Signature = inspect.signature(c)
                    # TODO: correctly propagate parameters
                    if len(sig.parameters) > 0:
                        c = c(n)
                    else:
                        c = c()
                self._materialize(topology, c)
