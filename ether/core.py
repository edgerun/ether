import abc
import logging
from typing import List, Dict, NamedTuple, Union, AnyStr, Optional

import numpy as np
import simpy
from srds import ParameterizedDistribution

logger = logging.getLogger(__name__)

TransparentLink = AnyStr
"""
Helper nodes, such as switches or routers, that are treated transparently (ignored) in a network simulation when
creating routes.
"""

NetworkNode = Union['Node', 'Link', TransparentLink]
"""
A network node is a vertex in a topology. It can either be a node (a computer), a link (a network devices), or helper
links (like switches).
"""


class Connection(NamedTuple):
    """
    A connection is an edge in the topology. It represents physical network connections (like a cable, or wireless
    connection of a WiFi card to an AP).
    """
    source: NetworkNode
    target: NetworkNode
    latency: float = 0
    latency_dist: ParameterizedDistribution = None
    # TODO: better network QoS modeling

    def get_latency(self) -> float:
        if self.latency_dist:
            return self.latency_dist.sample()
        return self.latency

    def get_mode_latency(self) -> float:
        if self.latency_dist:
            dist = self.latency_dist
            # we assume that latency_dist is a log norm distribution
            return np.exp(np.log(dist.scale) - dist.args[0] ** 2) + dist.loc
        return self.latency

    def get_mean_latency(self) -> float:
        if self.latency_dist:
            return self.latency_dist.mean()
        return self.latency


class Capacity:
    """
    Node capacity in terms of system capabilities (CPU, RAM, storage) ...
    """

    def __init__(self, cpu_millis: int = 1 * 1000, memory: int = 1024 * 1024 * 1024):
        self.memory = memory
        self.cpu_millis = cpu_millis

    def __str__(self):
        return 'Capacity(CPU: {0} Memory: {1})'.format(self.cpu_millis, self.memory)


class Coordinate(abc.ABC):
    def distance_to(self, other: 'Coordinate') -> float:
        pass


class Node:
    """
    A node is a machine in the network that can run compute tasks, manage data, and exchanges data with other nodes.
    """
    name: str
    capacity: Capacity
    arch: str
    labels: Dict[str, str]
    coordinate: Optional[Coordinate]

    def __init__(self, name: str, capacity: Capacity = None, arch='x86', labels: Dict[str, str] = None) -> None:
        super().__init__()
        self.name = name
        self.capacity = capacity or Capacity()
        self.arch = arch
        self.labels = labels or dict()
        self.coordinate = None

    def __repr__(self):
        return self.name

    def distance_to(self, other: 'Node') -> float:
        if self.coordinate is None:
            raise AssertionError('node has no coordinate set')
        if other.coordinate is None:
            raise AssertionError('other node has no coordinate set')

        return self.coordinate.distance_to(other.coordinate)

    def __hash__(self):
        return hash(self.name)


class Route:
    source: Node
    destination: Node
    path: List
    hops: List['Link']
    rtt: float = 0  # round-trip latency in milliseconds

    def __init__(self, source: Node, destination: Node, path: list, rtt: float = 0) -> None:
        super().__init__()
        self.source = source
        self.destination = destination
        self.path = path
        self.hops = [hop for hop in path if isinstance(hop, Link)]
        self.rtt = rtt

    def __str__(self) -> str:
        return f'Route[{self.source} ->{self.hops}-> {self.destination} (rtt={self.rtt})]'

    def __copy__(self):
        return Route(self.source, self.destination, self.path, self.rtt)


class Flow:
    sent: int
    size: int
    route: Route

    process: simpy.Process

    def __init__(self, env: simpy.Environment, size: int, route: Route) -> None:
        super().__init__()
        self.env = env
        self.size = size  # size in bytes
        self.route = route
        self.sent = 0

    def start(self):
        self.process = self.env.process(self.run())
        return self.process

    def get_goodput_bps(self):
        return min([link.get_goodput_bps(self) for link in self.route.hops])

    def run(self):
        env = self.env
        size = self.size
        route = self.route
        source = route.source
        hops = route.hops
        sink = route.destination

        if not hops:
            raise ValueError('no hops in route from %s to %s' % (source, sink))

        timer = env.now
        connection_time = ((route.rtt * 1.5) / 1000)  # rough estimate of TCP connection establish time
        if connection_time > 0:
            yield env.timeout(connection_time)

        add_and_rebalance(self)
        goodput = self.get_goodput_bps()

        if goodput <= 0:
            raise ValueError
        # calculate the simulation time
        bytes_remaining = self.size
        transmission_time = bytes_remaining / goodput  # remaining seconds

        try:
            while True:
                started = env.now

                try:
                    logger.debug('%-5.2f sending %s -[%d]-> {%s} at %d bytes/sec',
                                 env.now, source.name, size, sink.name, goodput)
                    yield env.timeout(transmission_time)
                    break
                except simpy.Interrupt as interrupt:
                    self.sent += goodput * (env.now - started)
                    if self.sent >= size:
                        break  # was interrupted, but actually sent everything already

                    bytes_remaining = size - self.sent
                    logger.debug('%-5.2f sending %s -[%d]-> {%s} interrupted, new bw = %.2f (sent: %d, remaining: %d)',
                                 env.now, source.name, size, sink.name, interrupt.cause, self.sent, bytes_remaining)

                    goodput = self.get_goodput_bps()
                    if goodput <= 0:
                        raise ValueError
                    transmission_time = bytes_remaining / goodput  # set new time remaining

            logger.debug('%-5.2f sending %s -[%d]-> {%s} completed in %.2fs',
                         env.now, source.name, size, sink.name, env.now - timer)
        finally:
            remove_and_rebalance(self)

    def establish(self):
        env = self.env
        route = self.route

        connection_time = ((route.rtt * 1.5) / 1000)  # rough estimate of TCP connection establish time
        while connection_time > 0:
            started = env.now
            try:
                yield env.timeout(connection_time)
                break
            except simpy.Interrupt:
                connection_time = connection_time - (env.now - started)


class Link:
    bandwidth: int  # MBit/s
    tags: dict

    # calculated by rebalance
    allocation: Dict[Flow, float]
    num_flows: int
    max_allocatable: float

    def __init__(self, bandwidth: int = 100, tags=None) -> None:
        super().__init__()
        self.bandwidth = bandwidth
        self.tags = tags or dict()

        self.allocation = dict()
        self.num_flows = 0
        self.max_allocatable = bandwidth

    def recalculate_max_allocatable(self):
        num_flows = self.num_flows
        bandwidth = self.bandwidth

        if num_flows == 0:
            self.max_allocatable = bandwidth
            return

        # fair_per_flow is the maximum bandwidth a flow can get if there are no other flows that require less
        fair_per_flow = bandwidth / num_flows

        # flows that require less than the fair value may keep it
        reserved = {k: v for k, v in self.allocation.items() if v < fair_per_flow}
        allocatable = bandwidth - sum(reserved.values())

        # these are the flows competing for the remaining bandwidth
        competing_flows = num_flows - len(reserved)
        if competing_flows:
            allocatable_per_flow = allocatable / competing_flows
        else:
            allocatable_per_flow = allocatable

        self.max_allocatable = max(fair_per_flow, allocatable_per_flow)

    def get_goodput_bps(self, flow: Flow):
        """
        Returns the TCP goodput for a flow in bytes per second.
        """
        # TODO: calculate more accurately
        # TODO: use some degradation function? https://pdos.csail.mit.edu/~rtm/papers/icnp97-web.pdf

        if flow not in self.allocation:
            return None

        allocated = self.allocation[flow]
        practical_bw = allocated * 125000
        goodput_magic_number = 0.97  # rough estimate of goodput (~ TCP overhead)

        return practical_bw * goodput_magic_number

    def __str__(self) -> str:
        return f'Link({hex(id(self))}){self.tags}'

    def __repr__(self):
        return self.__str__()


def remove_and_rebalance(flow: Flow):
    # first, collect all affected flows and links
    affected_flows, affected_links = collect_subnet(flow)
    affected_flows.remove(flow)

    for link in flow.route.hops:
        link.num_flows -= 1
        del link.allocation[flow]
        link.recalculate_max_allocatable()

    rebalance(flow, affected_flows, affected_links)


def add_and_rebalance(flow: Flow):
    # first, collect all affected flows and links
    affected_flows, affected_links = collect_subnet(flow)

    for link in flow.route.hops:
        link.num_flows += 1
        link.recalculate_max_allocatable()

    rebalance(flow, affected_flows, affected_links)


def rebalance(triggering_flow, affected_flows, affected_links):
    # holds all allocations that have changed (some may be unaffected)
    allocation: Dict[Flow, float] = dict()

    while affected_flows:
        bottlenecks = {flow: min([link.max_allocatable for link in flow.route.hops]) for flow in affected_flows}
        flow: Flow = min(bottlenecks, key=lambda k: bottlenecks[k])
        request = bottlenecks[flow]

        changed = False

        for link in flow.route.hops:
            if link.allocation.get(flow) == request:
                continue
            changed = True
            link.allocation[flow] = request
            link.recalculate_max_allocatable()

        if changed:
            allocation[flow] = request

        del bottlenecks[flow]
        affected_flows.remove(flow)

    for flow, bw in allocation.items():
        if flow is triggering_flow:
            continue
        if not flow.process.is_alive:
            continue
        flow.process.interrupt(bw)

    # logger.info(' >> new allocation:')
    # for link in affected_links:
    #     logger.info(' - %s (%.2f)', link, link.bandwidth)
    #     for flow, bw in link.allocation.items():
    #         logger.info('   - %8.2f %s', bw, flow.route)

    return allocation


def collect_subnet(flow: Flow):
    # first, collect all affected flows and links
    affected_links = set()
    affected_flows = set()

    stack = set()
    stack.add(flow)

    while stack:
        elem = stack.pop()
        if isinstance(elem, Link):
            if elem in affected_links:
                continue
            affected_links.add(elem)

            flows = elem.allocation.keys()
            stack.update(flows)

        elif isinstance(elem, Flow):
            if elem in affected_flows:
                continue
            affected_flows.add(elem)

            links = elem.route.hops
            stack.update(links)
        else:
            raise ValueError('element of type %s not handled: %s' % (type(elem), elem))

    return affected_flows, affected_links
