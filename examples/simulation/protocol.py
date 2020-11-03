from collections import defaultdict
from typing import List, Dict

import simpy

from ether.core import Node
from ether.topology import Topology
from ether.vivaldi import VivaldiCoordinate


class Message:
    pass


class PingMessage(Message):
    pass


class PongMessage(Message):
    coordinate: VivaldiCoordinate
    timestamp: int

    def __init__(self, coordinate: VivaldiCoordinate, timestamp: int):
        self.coordinate = coordinate
        self.timestamp = timestamp


class FindClosestBrokersRequest(Message):
    pass


class FindClosestBrokersResponse(Message):
    brokers: List[Node]

    def __init__(self, brokers: List[Node]):
        self.brokers = brokers


class FindRandomBrokersRequest(Message):
    pass


class FindRandomBrokersResponse(Message):
    brokers: List[Node]

    def __init__(self, brokers: List[Node]):
        self.brokers = brokers


class Protocol(object):
    env: simpy.Environment
    stores: Dict[Node, simpy.Store]
    topology: Topology

    def __init__(self, env: simpy.Environment, topology: Topology):
        self.env = env
        self.stores = defaultdict(lambda: simpy.Store(env))
        self.topology = topology

    def send(self, source, destination, message):
        self.env.process(self._do_send(source, destination, message))

    def _do_send(self, source: Node, destination: Node, message: Message):
        yield self.env.timeout(int(self.topology.route(source, destination).rtt))
        self.stores[destination].put((source, message))

    def receive(self, node: Node):
        return self.stores[node].get()

    def has_item(self, node: Node):
        return len(self.stores[node].items) > 0


