import logging
import random
from abc import abstractmethod, ABC
from itertools import product
from typing import Union, Set, Iterable

from ether import vivaldi
from ether.cell import Broker, Client
from ether.vivaldi import VivaldiCoordinate
from examples.simulation.protocol import *

file_log = logging.getLogger()
file_log.handlers.append(logging.FileHandler('simulation.log', mode='w'))
file_log.level = logging.DEBUG


def log(env: simpy.Environment, *messages):
    minutes = int(env.now / 1000 / 60)
    seconds = int(env.now / 1000 % 60)
    print(f'{minutes:02d}:{seconds:02d} {" ".join(messages)}')


def logf(time: int, message, *args):
    minutes = int(time / 1000 / 60)
    seconds = int(time / 1000 % 60)
    file_log.debug(f'{minutes:02d}:{seconds:02d} {message}', *args)


class NodeProcess(ABC):
    env: simpy.Environment
    protocol: Protocol
    node: Node
    handlers: Dict[Type[MessageT], Callable[[MessageT], Union[Generator, None]]]
    running: bool
    execute_vivaldi: bool

    def __init__(self, env: simpy.Environment, protocol: Protocol, execute_vivaldi=False):
        self.env = env
        self.protocol = protocol
        self.handlers = dict()
        self.running = False
        self.execute_vivaldi = execute_vivaldi

    def run(self):
        self.running = True
        if self.execute_vivaldi and self.node.coordinate is None:
            self.node.coordinate = VivaldiCoordinate()
        while True:
            receive_types = [Shutdown, PingMessage, PongMessage, *self.handlers.keys()]
            message: Message = yield self.protocol.receive(self.node, *receive_types)
            logf(self.env.now, '%s %s', self.node.name, message.__class__.__name__)
            if isinstance(message, Shutdown):
                return
            if self.execute_vivaldi and isinstance(message.source.coordinate, VivaldiCoordinate):
                vivaldi.execute(self.node, message.source, message.latency * 2)
            if isinstance(message, PingMessage):
                yield self.send(message.source, PongMessage())
            elif isinstance(message, PongMessage):
                continue
            else:
                result = self.handlers[type(message)](message)
                if isinstance(result, Generator):
                    yield from result

    def send(self, destination: Node, message: Message) -> Generator[simpy.Event, None, None]:
        return self.protocol.send(self.node, destination, message)

    def receive(self, *message_types: Type[MessageT]):
        return self.protocol.receive(self.node, *message_types)

    def ping_all(self, get_nodes: Callable[[], Iterable[Node]], interval=15_000) -> Generator[simpy.Event, None, None]:
        while self.running:
            yield from self.ping_nodes(get_nodes())
            yield self.env.timeout(interval)

    def ping_nodes(self, nodes: Iterable[Node], pings_per_node=5) -> Generator[simpy.Event, None, None]:
        for (b, _) in product(nodes, range(pings_per_node)):
            if b == self.node:
                continue
            yield self.send(b, PingMessage())
            yield self.receive(PongMessage)

    @property
    @abstractmethod
    def node(self) -> Node:
        ...

    def shutdown(self):
        self.running = False
        return self.protocol.send(self.node, self.node, Shutdown())


class ClientProcess(NodeProcess):
    client: Client
    selected_broker: Node
    subscriptions: Set[str]

    def __init__(self, env: simpy.Environment, protocol: Protocol, client: Client, initial_broker: Node,
                 execute_vivaldi=False):
        super().__init__(env, protocol, execute_vivaldi)
        self.client = client
        self.selected_broker = initial_broker
        self.subscriptions = set()
        self.handlers[Connect] = self.handle_reconnect_request
        self.handlers[Pub] = self.handle_publish

    def handle_reconnect_request(self, request: Connect):
        events = []
        for topic in self.subscriptions:
            events.append(self.send(request.broker, Sub(topic)))
            if self.protocol.enable_ack:
                events.append(self.receive(SubAck))
            events.append(self.send(self.selected_broker, Unsub(topic)))
            if self.protocol.enable_ack:
                events.append(self.receive(UnsubAck))
        self.selected_broker = request.broker
        if self.protocol.enable_ack:
            events.append(self.send(request.source, ConnectAck()))
        return simpy.AllOf(self.env, events)

    def handle_publish(self, message: Pub):
        if self.protocol.enable_ack:
            return self.send(message.source, PubAck())

    def run_ping_loop(self):
        while self.running:
            yield from self.ping_random()
            yield self.env.timeout(30_000)
            yield from self.ping_closest()
            yield self.env.timeout(30_000)

    def ping_random(self, n=5):
        yield self.send(self.selected_broker, FindRandomBrokersRequest())
        message = yield self.receive(FindRandomBrokersResponse)
        yield from self.ping_nodes(message.brokers[:n])

    def ping_closest(self, n=5):
        yield self.send(self.selected_broker, FindClosestBrokersRequest())
        response = yield self.receive(FindClosestBrokersResponse)
        yield from self.ping_nodes(response.brokers[:n])

    def subscribe(self, topic: str):
        self.subscriptions.add(topic)
        yield self.send(self.selected_broker, Sub(topic))
        if self.protocol.enable_ack:
            yield self.receive(SubAck)

    def run_publisher(self, topic: str, interval: int):
        while True:
            yield self.send(self.selected_broker, Pub(topic, 'data'))
            if self.protocol.enable_ack:
                yield self.receive(PubAck)
            yield self.env.timeout(interval)

    @property
    def node(self):
        return self.client.node

    def shutdown(self):
        events = []
        for topic in self.subscriptions:
            events.append(self.send(self.selected_broker, Unsub(topic)))
            if self.protocol.enable_ack:
                events.append(self.receive(UnsubAck))
        events.append(super().shutdown())
        return simpy.AllOf(self.env, events)

    def __repr__(self):
        return f'ClientProcess(node={self.node}, broker={self.selected_broker})'


class BrokerProcess(NodeProcess):
    broker: Broker
    brokers: List['BrokerProcess']
    subscribers: Dict[str, Set[Node]]

    def __init__(self, env: simpy.Environment, protocol: Protocol, broker: Broker, brokers: List['BrokerProcess'],
                 execute_vivaldi=False):
        super().__init__(env, protocol, execute_vivaldi)
        self.broker = broker
        self.brokers = brokers
        self.subscribers = defaultdict(lambda: set())
        self.handlers[FindRandomBrokersRequest] = self.handle_random_brokers
        self.handlers[FindClosestBrokersRequest] = self.handle_closest_brokers
        self.handlers[Sub] = self.handle_subscribe
        self.handlers[Unsub] = self.handle_unsubscribe

    def handle_random_brokers(self, message: FindRandomBrokersRequest):
        yield self.send(message.source, FindRandomBrokersResponse([b.node for b in random.choices(self.brokers, k=5)]))

    def handle_closest_brokers(self, message: FindClosestBrokersRequest):
        closest_brokers = sorted(self.brokers, key=lambda b: message.source.distance_to(b.node))
        yield self.send(message.source, FindClosestBrokersResponse([b.node for b in closest_brokers[:5]]))

    def handle_subscribe(self, message: Sub):
        self.subscribers[message.topic].add(message.source)
        if self.protocol.enable_ack:
            return self.send(message.source, SubAck())

    def handle_unsubscribe(self, message: Unsub):
        self.subscribers[message.topic].remove(message.source)
        if self.protocol.enable_ack:
            return self.send(message.source, UnsubAck())

    def run_pub_process(self):
        while self.running:
            msg = yield self.receive(Pub, PubAck)
            if isinstance(msg, Pub):
                logf(self.env.now, f'{self.node.name} Pub from {msg.source.name}')
                yield self.handle_publish(msg)

    def handle_publish(self, message: Pub):
        events = []
        if self.protocol.enable_ack:
            events.append(self.send(message.source, PubAck()))

        for dest in self.subscribers[message.topic]:
            if dest != message.source:
                events.append(self.send(dest, message))
                if self.protocol.enable_ack:
                    events.append(self.receive(PubAck))

        for broker in self.brokers:
            if broker.node == message.source or broker == self:
                # prevent message loops
                continue
            if len(broker.subscribers[message.topic]) > 0:
                # forward message if other broker has subscribers
                events.append(self.send(broker.node, message))
                if self.protocol.enable_ack:
                    events.append(self.receive(PubAck))

        return simpy.AllOf(self.env, events)

    def total_subscribers(self):
        return len(set().union(*self.subscribers.values()))

    @property
    def node(self) -> Node:
        return self.broker.node

    def shutdown(self):
        events = []
        # reconnect active clients to random available broker
        node: Node
        for node in set().union(*self.subscribers.values()):
            events.append(self.send(node, Connect(random.choice(self._running_brokers()).node)))
            if self.protocol.enable_ack:
                events.append(self.receive(ConnectAck))

        events.append(super().shutdown())
        return simpy.AllOf(self.env, events)

    def _running_brokers(self) -> List['BrokerProcess']:
        return list(filter(lambda bp: bp.running, self.brokers))

    def __repr__(self):
        return f'BrokerProcess(node={self.node})'


class CoordinatorProcess:
    env: simpy.Environment
    topology: Topology
    protocol: Protocol
    client_procs: List[ClientProcess]
    broker_procs: List[BrokerProcess]
    use_coordinates: bool
    node: Node

    def __init__(self, env: simpy.Environment, topology: Topology, protocol: Protocol,
                 client_procs: List[ClientProcess], broker_procs: List[BrokerProcess], use_coordinates=False):
        self.env = env
        self.topology = topology
        self.protocol = protocol
        self.client_procs = client_procs
        self.broker_procs = broker_procs
        self.use_coordinates = use_coordinates
        self.node = Node('coordinator')

    def run(self):
        while True:
            for client in self.client_procs:
                current_broker = self.get_broker(client.selected_broker)
                possible_brokers = self.brokers_in_lowest_latency_group(client.node)
                if len(possible_brokers) == 0:
                    break
                new_broker = sorted(possible_brokers, key=lambda b: b.total_subscribers())[0]
                if new_broker == current_broker:
                    continue
                if current_broker in possible_brokers:
                    theta = 0.1
                    delta = theta * sum(map(lambda b: b.total_subscribers(), possible_brokers))
                    if new_broker.total_subscribers() + delta >= current_broker.total_subscribers():
                        continue
                self.protocol.send(self.node, client.node, Connect(new_broker.node))
                if self.protocol.enable_ack:
                    yield self.protocol.receive(self.node, ConnectAck)
            yield self.env.timeout(15_000)

    def get_broker(self, node: Node) -> BrokerProcess:
        return next(b for b in self.broker_procs if b.node == node)

    def brokers_in_lowest_latency_group(self, node: Node) -> List[BrokerProcess]:
        running_brokers = sorted([(self.topology.latency(node, bp.node, self.use_coordinates), bp)
                                  for bp in self.broker_procs if bp.running], key=lambda t: t[0])
        group_boundaries = [0, 2, 5, 10, 20, 50, 100, 200, 500, 1000, float('Inf')]
        for (low, high) in zip(group_boundaries, group_boundaries[1:]):
            group_brokers = [b[1] for b in running_brokers if low <= b[0] < high]
            if len(group_brokers) > 0:
                return group_brokers
        return []
