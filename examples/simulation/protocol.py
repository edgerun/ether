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
    timestamp: float
    latency: float
    size: int
    management = False

    def __repr__(self):
        return f'{type(self).__name__}({self.__dict__})'


MessageT = TypeVar('MessageT', bound=Message)


class Ping(Message):
    size = 5
    management = True


class Pong(Message):
    ping_latency: float
    rtt: float
    size = 5
    management = True

    def __init__(self, ping_latency: float):
        self.ping_latency = ping_latency


class FindClosestBrokersRequest(Message):
    size = 5
    management = True


class FindClosestBrokersResponse(Message):
    brokers: List[Node]
    management = True

    def __init__(self, brokers: List[Node]):
        self.brokers = brokers
        # 1 byte type/length, 4 bytes IP + 1 byte port for each broker
        self.size = 1 + len(brokers) * 5


class FindRandomBrokersRequest(Message):
    size = 5
    management = True


class FindRandomBrokersResponse(Message):
    brokers: List[Node]
    management = True

    def __init__(self, brokers: List[Node]):
        self.brokers = brokers
        # 1 byte type/length, 4 bytes IP + 1 byte port for each broker
        self.size = 1 + len(brokers) * 5


class ReconnectRequest(Message):
    broker: Node
    optimal_broker: Node
    size = 47
    management = True

    def __init__(self, broker: Node, optimal_broker: Node):
        self.broker = broker
        self.optimal_broker = optimal_broker


class ReconnectAck(Message):
    size = 47
    management = True


class QoSRequest(Message):
    target: Node
    # type/length (1) + packetId (4) + target IP (4) + target port (4)
    size = 13
    management = True

    def __init__(self, target: Node):
        self.target = target


class QoSResponse(Message):
    avg_rtt: float
    # type/length + packetId + avg_rtt
    size = 9
    management = True

    def __init__(self, avg_rtt):
        self.avg_rtt = avg_rtt


class Sub(Message):
    topic: str

    def __init__(self, topic: str):
        self.topic = topic
        # type/length + packetId + topic
        self.size = 1 + 4 + len(topic)


class SubAck(Message):
    # type/length + packetId
    size = 5


class Unsub(Message):
    topic: str

    def __init__(self, topic: str):
        self.topic = topic
        # type/length + packetId + topic
        self.size = 1 + 4 + len(topic)


class UnsubAck(Message):
    # type/length + packetId
    size = 5


pub_counter = itertools.count()


class Pub(Message):
    hops: List[Node]
    first_sent: float
    e2e_latency: float = 0.0
    topic: str
    data: Any

    def __init__(self, topic: str, first_sent: float):
        self.hops = []
        self.first_sent = first_sent
        self.topic = topic
        self.data = str(next(pub_counter))
        # type/length + Pub header + topic + packetId + payload
        self.size = 1 + 1 + len(topic) + 4 + 4


class PubAck(Message):
    # type/length + packetId
    size = 5


class Shutdown(Message):
    # type/length + packetId
    size = 5


csv_fields = {
    'timestamp': lambda m: m.timestamp,
    'msg_type': lambda m: type(m).__name__,
    'source': lambda m: m.source.name,
    'destination': lambda m: m.destination.name,
    'latency': lambda m: m.latency,
    'size': lambda m: m.size,
    'management': lambda m: m.management,
    'topic': lambda m: m.topic if hasattr(m, 'topic') else '',
    'broker': lambda m: m.broker.name if hasattr(m, 'broker') else '',
    'optimal_broker': lambda m: m.optimal_broker.name if hasattr(m, 'optimal_broker') else '',
    'data': lambda m: m.data if hasattr(m, 'data') else '',
    'e2e_latency': lambda m: m.e2e_latency if hasattr(m, 'e2e_latency') else '',
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
        if isinstance(message, Pub):
            message.e2e_latency += message.latency
        if isinstance(message, Pong):
            message.rtt = message.ping_latency + message.latency
        if self.save_history:
            self.history.append(message)
        if self.csv_file:
            self.csv_writer.writerow({field: accessor(message) for field, accessor in csv_fields.items()})
        return self.env.process(self.do_send(message))

    def do_send(self, message: Message):
        yield self.env.timeout(message.latency)
        yield self.stores[message.destination].put(message)

    def receive(self, node: Node, *message_types: Type[MessageT]):
        if len(message_types) > 0:
            return self.stores[node].get(lambda m: type(m) in message_types)
        return self.stores[node].get()
