import itertools
import random
from collections import defaultdict

from srds import ParameterizedDistribution

from ether.blocks.cells import IoTComputeBox, MobileConnection
from ether.cell import Client, GeoCell, SharedLinkCell, Broker
from ether.converter.pyvis import topology_to_pyvis
from ether.topology import Topology
from examples.vivaldi.client_experiment import ClientExperiment
from examples.vivaldi.util import execute_vivaldi


def create_topology() -> Topology:
    topology = Topology()
    counters = defaultdict(lambda: itertools.count(0, 1))
    lognorm = ParameterizedDistribution.lognorm

    def client_factory_with_region(region: str):
        def create_client():
            name = 'client_%d_%s' % (next(counters['client']), region)
            return Client(name)

        return create_client

    def edge_broker_factory_with_region(region: str):
        def create_edge_broker() -> Broker:
            name = 'edge-broker_%d_%s' % (next(counters['edge-brokers']), region)
            return Broker(name)

        return create_edge_broker

    # load cloudping dataset and select 5 random regions
    topology.load_inet_graph('cloudping')
    regions = random.choices(list(topology.nodes), k=5)

    # remove unused regions from topology
    unused_regions = topology.nodes - regions
    for r in unused_regions:
        topology.remove_node(r)

    # create 1 city (including one edge broker per neighborhood) plus 1 cloud broker per region
    for region in regions:
        aot_node = IoTComputeBox(nodes=[client_factory_with_region(region)])
        neighborhood = lambda size: SharedLinkCell(
            nodes=[[aot_node] * size, [edge_broker_factory_with_region(region)]],
            backhaul=MobileConnection(region)
        )
        city = GeoCell(5, nodes=[neighborhood], density=lognorm((0.82, 2.02)))
        topology.add(city)

        broker = Broker(f'cloud-broker_{region}', backhaul=region)
        topology.add(broker)

    return topology


def run_experiment(topology: Topology):
    execute_vivaldi(topology, node_filter=lambda n: 'broker' in n.name, min_executions=300)
    nodes = topology.get_nodes()
    clients = [n for n in nodes if 'client' in n.name]
    brokers = [n for n in nodes if 'broker' in n.name]
    experiment = ClientExperiment(topology, clients, brokers)
    experiment.run_and_plot('5 random brokers, 3 closest brokers',
                            lambda _: random.choices(brokers, k=5),
                            lambda c: experiment.find_vivaldi_closest_brokers(c)[:3])


def show_graph(topology):
    net = topology_to_pyvis(topology)
    net.show('urbansensing.html')


def main():
    topology = create_topology()
    show_graph(topology)
    run_experiment(topology)


if __name__ == '__main__':
    main()
