import argparse
import logging
import random
import sys
from collections import defaultdict
from concurrent.futures.process import ProcessPoolExecutor
from datetime import datetime
from itertools import count
from os import chdir
from typing import List, Dict, Iterator

import numpy
import pandas as pd
import simpy

from ether.cell import Broker, Client
from ether.topology import Topology
from examples.simulation.processes import BrokerProcess, ClientProcess, CoordinatorProcess
from examples.simulation.protocol import Protocol


class EmmaScenario:
    name: str
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
    logger: logging.Logger

    def __init__(self, name: str, use_vivaldi=False, action_interval=1, verbose=False,
                 clients_per_group=10, publishers_per_client=7, publish_interval=100, enable_ack=False,
                 ping_all_brokers=True):
        """
        Create a new emma scenario

        :param use_vivaldi: run vivaldi on nodes and use coordinates to estimate distances
        :param action_interval: scenario action interval in minutes
        :param clients_per_group: number of clients per client group
        :param publishers_per_client: number of publishers per client
        :param publish_interval: publish interval in milliseconds
        """
        self.name = f"{name}.{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
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
        self.logger = logging.getLogger('scenario')

        logging.basicConfig(force=True, filename=f'{self.name}.log', level=logging.DEBUG)
        if verbose:
            console_handler = logging.StreamHandler()
            logging.getLogger().addHandler(console_handler)
            console_handler.level = logging.INFO

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
        # self.topology.add_connection(Connection(coordinator_process.node, 'internet_eu-central-1'))
        self.env.process(coordinator_process.run())

    def sleep(self):
        return self.env.timeout(self.action_interval * 60_000)

    def scenario_process(self):
        self.logger.info(f'===== STARTING SCENARIO {self.name.upper()} =====')
        self.log('[0] spawn coordinator and initial broker')
        self.spawn_coordinator()
        self.spawn_broker('internet_eu-central-1')
        yield self.sleep()

        self.log('[1] topic global: one publisher and subscriber in `us-east` and `eu-west`, '
                 'one subscriber in `eu-central`')
        self.spawn_client('internet_eu-west-1', 'global')
        central_client = self.spawn_client('internet_eu-central-1', 'global', publishers=0)
        self.spawn_client('internet_us-east-1', 'global')
        yield self.sleep()

        self.log('[2] client group appears in us-east')
        self.spawn_client_group('internet_us-east-1')
        yield self.sleep()

        self.log('[3] broker spawns in eu-west')
        self.spawn_broker('internet_eu-west-1')
        yield self.sleep()

        self.log('[4] client group appears in eu-west')
        self.spawn_client_group('internet_eu-west-1')
        yield self.sleep()

        self.log('[5] broker spawns in us-east')
        us_east_broker = self.spawn_broker('internet_us-east-1')
        yield self.sleep()

        self.log('[6] broker spawns in eu-west')
        self.spawn_broker('internet_eu-west-1')
        yield self.sleep()

        self.log('[7] subscriber to topic `global` in eu-central disappears')
        yield central_client.shutdown()
        yield self.sleep()

        self.log('[8] broker shuts down in us-east')
        yield us_east_broker.shutdown()

    def run(self):
        random.seed(0)
        numpy.random.seed(0)

        self.topology.load_inet_graph('cloudping')
        regions = ['internet_eu-west-1', 'internet_eu-central-1', 'internet_us-east-1']
        self.topology.remove_nodes_from([n for n in self.topology.nodes if n not in regions])
        self.env.process(self.scenario_process())

        minutes = self.action_interval * 10
        for i in range(minutes):
            self.env.run((i+1) * 60_000)
            if self.logger.level > logging.DEBUG:
                continue
            if any(len(p.subscribers) > 0 for p in self.broker_procs):
                for p in self.broker_procs:
                    if len(p.subscribers) == 0:
                        continue
                    self.log(f'--- subscribers on {p.node} ---')
                    for topic, subscribers in p.subscribers.items():
                        if len(subscribers) > 0:
                            self.log(f'[{topic}] {subscribers}')
            if any(len(s.items) > 0 for s in self.protocol.stores.values()):
                self.log(f'--- message queues ---')
                for p in [*self.broker_procs, *self.client_procs]:
                    p_msgs = self.protocol.stores[p.node].items
                    counts = {t.__name__: len([m for m in p_msgs if isinstance(m, t)])
                              for t in {type(m) for m in p_msgs}}
                    if len(counts) > 0:
                        self.log(p.node.name)

    def export(self, filename: str):
        df = pd.DataFrame([{
            'timestamp': m.timestamp,
            'msg_type': type(m).__name__,
            'source': m.source.name,
            'destination': m.destination.name,
            'latency': m.latency,
            'topic': m.topic if hasattr(m, 'topic') else None,
            'broker': m.broker if hasattr(m, 'broker') else None
        } for m in self.protocol.history])
        df.to_csv(filename)

    def run_and_export(self):
        self.run()
        self.export(f'{self.name}.csv')

    def log(self, message):
        minutes = int(self.env.now / 1000 / 60)
        seconds = int(self.env.now / 1000 % 60)
        logging.info(f'{minutes:02d}:{seconds:02d} {message}')


def run_scenario(**kwargs):
    EmmaScenario(**kwargs).run_and_export()


def main():
    logging.basicConfig(filename='emma.log', level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='print stats')
    parser.add_argument('-o', '--output', type=str, help='path to CSV output')
    parser.add_argument('--publishers-per-client', type=int, default=7)
    parser.add_argument('--publish-interval', type=int, default=100, help='publish interval in ms')
    args = parser.parse_args(sys.argv[1:])
    if args.output:
        chdir(args.output)
    common_kwargs = {
        'publishers_per_client': args.publishers_per_client,
        'publish_interval': args.publish_interval,
        'verbose': args.verbose
    }

    scenario_configs = [
        {
            **common_kwargs,
            'name': 'emma_ack',
            'enable_ack': True,
        },
        {
            **common_kwargs,
            'name': 'emma',
        },
        {
            **common_kwargs,
            'name': 'emma_vivaldi',
            'use_vivaldi': True,
        },
        {
            **common_kwargs,
            'name': 'emma_no_ping',
            'ping_all_brokers': False,
        }
    ]

    if args.verbose:
        print('running emma scenarios sequentially')
        for config in scenario_configs:
            run_scenario(**config)
    else:
        print('running emma scenarios in separate processes')
        executor = ProcessPoolExecutor(len(scenario_configs))
        for config in scenario_configs:
            executor.submit(run_scenario, **config)


if __name__ == '__main__':
    main()
