import csv
import itertools
import math
from collections import defaultdict
from typing import List, Dict, TypeVar, Any, Type, TextIO, Optional
from uuid import uuid4

import simpy

from ether.core import Node
from ether.topology import Topology


class Message:
    source: Node
    destination: Node
    timestamp: int
    latency: float

    def __repr__(self):
        return f'{type(self).__name__}({self.__dict__})'


MessageT = TypeVar('MessageT', bound=Message)


class Ping(Message):
    pass


class Pong(Message):
    pass


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


class Connect(Message):
    broker: Node

    def __init__(self, broker: Node):
        self.broker = broker


class ConnectAck(Message):
    pass


class Sub(Message):
    topic: str

    def __init__(self, topic: str):
        self.topic = topic


class SubAck(Message):
    pass


class Unsub(Message):
    topic: str

    def __init__(self, topic: str):
        self.topic = topic


class UnsubAck(Message):
    pass


pub_counter = itertools.count()


class Pub(Message):
    hops: List[Node]
    topic: str
    data: Any

    def __init__(self, topic: str):
        self.hops = []
        self.topic = topic
        self.data = str(next(pub_counter))


class PubAck(Message):
    pass


class Shutdown(Message):
    pass


csv_fields = {
    'timestamp': lambda m: str(m.timestamp),
    'msg_type': lambda m: type(m).__name__,
    'source': lambda m: m.source.name,
    'destination': lambda m: m.destination.name,
    'latency': lambda m: str(round(m.latency, 3)),
    'topic': lambda m: m.topic if hasattr(m, 'topic') else '',
    'broker': lambda m: m.broker.name if hasattr(m, 'broker') else '',
    'data': lambda m: m.data if hasattr(m, 'data') else '',
}


class Protocol(object):
    env: simpy.Environment
    stores: Dict[Node, simpy.FilterStore]
    topology: Topology
    history: List[Message]
    enable_ack: bool
    csv_file: Optional[TextIO]
    csv_writer: csv.DictWriter
    save_history: bool

    def __init__(self, env: simpy.Environment, topology: Topology, enable_ack=True, csv_file: Optional[TextIO] = None,
                 save_history=False):
        self.env = env
        self.stores = defaultdict(lambda: simpy.FilterStore(env))
        self.topology = topology
        self.history = list()
        self.enable_ack = enable_ack
        self.csv_file = csv_file
        if csv_file:
            self.csv_writer = csv.DictWriter(csv_file, fieldnames=csv_fields.keys())
            self.csv_writer.writeheader()
        self.save_history = save_history

    def send(self, source: Node, destination: Node, message: MessageT):
        message.source = source
        message.destination = destination
        message.timestamp = self.env.now
        message.latency = self.topology.latency(source, destination)
        if self.save_history:
            self.history.append(message)
        if self.csv_file:
            self.csv_writer.writerow({field: accessor(message) for field, accessor in csv_fields.items()})
        return self.stores[message.destination].put(message)

    def receive(self, node: Node, *message_types: Type[MessageT]):
        if len(message_types) > 0:
            return self.stores[node].get(lambda m: type(m) in message_types)
        return self.stores[node].get()
