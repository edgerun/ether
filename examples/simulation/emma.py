from collections import defaultdict
from itertools import count
from typing import List, Dict, Iterator, Optional

import pandas as pd
import simpy

from ether.cell import Broker, Client
from ether.core import Connection
from ether.topology import Topology
from examples.simulation.processes import BrokerProcess, ClientProcess, CoordinatorProcess, log
from examples.simulation.protocol import Protocol


class EmmaScenario:
    broker_counters: Dict[str, Iterator[int]]
    client_counters: Dict[str, Iterator[int]]
    topology: Topology
    env: simpy.Environment
    protocol: Protocol
    broker_procs: List[BrokerProcess]
    client_procs: List[ClientProcess]
    use_vivaldi: bool
    action_interval: int
    clients_per_group: int
    publishers_per_client: int
    publish_interval: int
    ping_all_brokers: bool

    def __init__(self, use_vivaldi=False, action_interval=1, clients_per_group=10,
                 publishers_per_client=7, publish_interval=100, enable_ack=True, ping_all_brokers=True):
        """
        Create a new emma scenario

        :param use_vivaldi: run vivaldi on nodes and use coordinates to estimate distances
        :param action_interval: scenario action interval in minutes
        :param clients_per_group: number of clients per client group
        :param publishers_per_client: number of publishers per client
        :param publish_interval: publish interval in milliseconds
        """
        self.broker_counters = defaultdict(lambda: count(1))
        self.client_counters = defaultdict(lambda: count(1))
        self.env = simpy.Environment()
        self.topology = Topology()
        self.protocol = Protocol(self.env, self.topology, enable_ack)
        self.broker_procs = []
        self.client_procs = []
        self.use_vivaldi = use_vivaldi
        self.action_interval = action_interval
        self.clients_per_group = clients_per_group
        self.publishers_per_client = publishers_per_client
        self.publish_interval = publish_interval
        self.ping_all_brokers = ping_all_brokers

        self.topology.load_inet_graph('cloudping')
        regions = ['internet_eu-west-1', 'internet_eu-central-1', 'internet_us-east-1']
        self.topology.remove_nodes_from([n for n in self.topology.nodes if n not in regions])
        self.env.process(self.scenario_process())

    def spawn_broker(self, region: str) -> BrokerProcess:
        broker = Broker(f'{region}_broker_{next(self.broker_counters[region])}', backhaul=region)
        broker.materialize(self.topology)
        bp = BrokerProcess(self.env, self.protocol, broker, self.broker_procs, self.use_vivaldi)
        self.env.process(bp.run())
        self.env.process(bp.run_pub_process())
        if self.use_vivaldi:
            self.env.process(bp.ping_all(lambda: map(lambda bp: bp.node, self.broker_procs)))
        self.broker_procs.append(bp)
        return bp

    def spawn_client(self, region: str, topic: str, publishers: int = 1) -> ClientProcess:
        client = Client(f'{region}_client_{next(self.client_counters[region])}', backhaul=region)
        client.materialize(self.topology)
        cp = ClientProcess(self.env, self.protocol, client, self.broker_procs[0].node, self.use_vivaldi)
        self.env.process(cp.subscribe(topic))
        for _ in range(publishers):
            self.env.process(cp.run_publisher(topic, self.publish_interval))
        self.env.process(cp.run())
        if self.use_vivaldi:
            self.env.process(cp.run_ping_loop())
        elif self.ping_all_brokers:
            self.env.process(cp.ping_all(lambda: [bp.node for bp in self.broker_procs if bp.running]))
        self.client_procs.append(cp)
        return cp

    def spawn_client_group(self, region: str):
        # a client group consists of 10 VMs, each running a subscriber and 7 publishers
        for _ in range(self.clients_per_group):
            self.spawn_client(region, region, self.publishers_per_client)

    def spawn_coordinator(self):
        coordinator_process = CoordinatorProcess(self.env, self.topology, self.protocol, self.client_procs,
                                                 self.broker_procs, self.use_vivaldi)
        self.topology.add_connection(Connection(coordinator_process.node, 'internet_eu-central-1'))
        self.env.process(coordinator_process.run())

    def sleep(self):
        return self.env.timeout(self.action_interval * 60_000)

    def scenario_process(self):
        log(self.env, '[0] spawn coordinator and initial broker')
        self.spawn_coordinator()
        self.spawn_broker('internet_eu-central-1')
        yield self.sleep()

        log(self.env, '[1] topic global: one publisher and subscriber in `us-east` and `eu-west`, '
                      'one subscriber in `eu-central`')
        self.spawn_client('internet_eu-west-1', 'global')
        central_client = self.spawn_client('internet_eu-central-1', 'global', publishers=0)
        self.spawn_client('internet_us-east-1', 'global')
        yield self.sleep()

        log(self.env, '[2] client group appears in us-east')
        self.spawn_client_group('internet_us-east-1')
        yield self.sleep()

        log(self.env, '[3] broker spawns in eu-west')
        self.spawn_broker('internet_eu-west-1')
        yield self.sleep()

        log(self.env, '[4] client group appears in eu-west')
        self.spawn_client_group('internet_eu-west-1')
        yield self.sleep()

        log(self.env, '[5] broker spawns in us-east')
        us_east_broker = self.spawn_broker('internet_us-east-1')
        yield self.sleep()

        log(self.env, '[6] broker spawns in eu-west')
        self.spawn_broker('internet_eu-west-1')
        yield self.sleep()

        log(self.env, '[7] subscriber to topic `global` in eu-central disappears')
        yield central_client.shutdown()
        yield self.sleep()

        log(self.env, '[8] broker shuts down in us-east')
        yield us_east_broker.shutdown()

    def run(self, minutes: Optional[int] = None, log_stats=False):
        if minutes is None:
            minutes = self.action_interval * 10
        for i in range(minutes):
            self.env.run((i+1) * 60_000)
            if not log_stats:
                continue
            log(self.env)
            if any(len(p.subscribers) > 0 for p in self.broker_procs):
                for p in self.broker_procs:
                    if len(p.subscribers) == 0:
                        continue
                    print(f'--- subscribers on {p.node} ---')
                    for topic, subscribers in p.subscribers.items():
                        if len(subscribers) > 0:
                            print(f'[{topic}] {subscribers}')
            if any(len(s.items) > 0 for _, s in self.protocol.stores.items()):
                print(f'--- message queues ---')
                for p in [*self.broker_procs, *self.client_procs]:
                    p_msgs = self.protocol.stores[p.node].items
                    counts = {t.__name__: len([m for m in p_msgs if isinstance(m, t)])
                              for t in {type(m) for m in p_msgs}}
                    if len(counts) > 0:
                        print(p.node.name, counts)


if __name__ == '__main__':
    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument('-V', '--vivaldi', action='store_true', default=False, help='use vivaldi')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='print stats')
    parser.add_argument('-o', '--output', type=str, help='path to CSV output', required=True)
    parser.add_argument('--ack', action='store_true', help='enable ACK messages')
    args = parser.parse_args(sys.argv[1:])
    scenario = EmmaScenario(use_vivaldi=args.vivaldi, publishers_per_client=1, enable_ack=args.ack, ping_all_brokers=False)
    scenario.run(log_stats=args.verbose)
    df = pd.DataFrame([{
        **m.__dict__,
        'msg_type': type(m).__name__,
        'source': m.source.name,
        'destination': m.destination.name
    } for m in scenario.protocol.history])
    df.to_csv(args.output)
