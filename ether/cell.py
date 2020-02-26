import itertools
from collections import defaultdict
from typing import Callable, List, Union

from srds import RandomSampler

from ether.core import Node, Link
from ether.nodes import create_server_node
from ether.topology import Topology, Edge

counters = defaultdict(lambda: itertools.count(0, 1))


class UpDownLink:
    bw_down: int
    bw_up: int
    backhaul: object

    def __init__(self, bw_down, bw_up=None, backhaul='internet') -> None:
        super().__init__()
        self.bw_down = bw_down
        self.bw_up = bw_up if bw_up is not None else bw_down
        self.backhaul = backhaul


class MobileConnection(UpDownLink):

    def __init__(self, backhaul='internet') -> None:
        super().__init__(125, 26, backhaul)


class BusinessIsp(UpDownLink):

    def __init__(self, backhaul='internet') -> None:
        super().__init__(500, 50, backhaul)


class FiberToExchange(UpDownLink):

    def __init__(self, backhaul='internet') -> None:
        super().__init__(1000, 1000, backhaul)


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


class NodeCell(Cell):

    def __init__(self, node: Node, link_bw=1000, backhaul=None) -> None:
        super().__init__(nodes=[node], backhaul=backhaul)
        self.link_bw = link_bw

    def materialize(self, topology: Topology, parent=None):
        node = self.nodes[0]
        link = Link(bandwidth=self.link_bw, tags={'name': 'link_%s' % node.name, 'type': 'node'})

        topology.edges.append(Edge(node, link))
        if self.backhaul:
            topology.edges.append(Edge(link, self.backhaul))


class LANCell(Cell):

    def __init__(self, nodes, size=None, backhaul=None) -> None:
        super().__init__(nodes=nodes, size=size, backhaul=backhaul)

    def _create_identity(self):
        self.nr = next(counters['lan'])
        self.name = 'lan_%d' % self.nr
        self.switch = 'switch_%s' % self.name

    def materialize(self, topology: Topology, parent=None):
        self._create_identity()

        for cell in self.nodes:
            if callable(cell):
                cell = cell()  # TODO: propagate parameters

            if isinstance(cell, Node):
                cell = NodeCell(cell, backhaul=self.switch)
            elif isinstance(cell, Cell):
                cell.backhaul = self.switch

            cell.materialize(topology, self)

        if self.backhaul:
            if isinstance(self.backhaul, UpDownLink):
                uplink = Link(self.backhaul.bw_up, tags={'type': 'uplink', 'name': 'up_%s' % self.name})
                downlink = Link(self.backhaul.bw_down, tags={'type': 'downlink', 'name': 'down_%s' % self.name})

                topology.edges.append(Edge(self.switch, uplink, directed=True))
                topology.edges.append(Edge(downlink, self.switch, directed=True))

                topology.edges.append(Edge(self.backhaul.backhaul, downlink, directed=True))
                topology.edges.append(Edge(uplink, self.backhaul.backhaul, directed=True))

            else:
                topology.edges.append(Edge(self.switch, self.backhaul))


class Cloudlet(LANCell):
    def __init__(self, server_per_rack=5, racks=1, backhaul=None) -> None:
        self.racks = racks
        self.server_per_rack = server_per_rack

        nodes = [self._create_rack] * racks

        super().__init__(nodes, backhaul=backhaul)

    def _create_identity(self):
        self.nr = next(counters['cloudlet'])
        self.name = 'cloudlet_%d' % self.nr
        self.switch = 'switch_%s' % self.name

    def _create_rack(self):
        return LANCell([create_server_node] * self.server_per_rack, backhaul=self.switch)
