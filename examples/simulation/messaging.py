import random
from itertools import product

import numpy as np

from ether import vivaldi
from ether.vivaldi import VivaldiCoordinate
from examples.simulation.protocol import *
from examples.vivaldi.client_experiment import ClientExperiment
from examples.vivaldi.urban_sensing import create_topology
from examples.vivaldi.util import execute_vivaldi


random.seed(0)
np.random.seed(0)


def client(env: simpy.Environment, protocol: Protocol, node: Node, initial_broker: Node):
    selected_broker = initial_broker

    def ping_brokers(brokers: List[Node]):
        for (b, _) in product(brokers, range(5)):
            protocol.send(node, b, PingMessage())
            reply = yield protocol.receive(node)
            if isinstance(reply, PongMessage):
                vivaldi.execute(node, reply.source, reply.latency * 2)

    def ping_random(n=5):
        yield protocol.send(node, selected_broker, FindRandomBrokersRequest())
        message = yield protocol.receive(node)
        yield from ping_brokers(message.brokers[:n])

    def ping_closest(n=5):
        yield protocol.send(node, selected_broker, FindClosestBrokersRequest())
        message = yield protocol.receive(node)
        yield from ping_brokers(message.brokers[:n])

    while True:
        yield from ping_random()
        yield from ping_closest()
        yield env.timeout(60_000)


def broker(protocol: Protocol, node: Node, brokers: List[Node]):
    while True:
        message = yield protocol.receive(node)
        assert isinstance(node.coordinate, VivaldiCoordinate)
        if isinstance(message, PingMessage):
            response = PongMessage()
        elif isinstance(message, FindRandomBrokersRequest):
            response = FindRandomBrokersResponse(random.choices(brokers, k=5))
        elif isinstance(message, FindClosestBrokersRequest):
            response = FindClosestBrokersResponse(sorted(brokers, key=lambda b: message.source.distance_to(b))[:5])
        else:
            continue
        yield protocol.send(node, message.source, response)


def main():
    topology = create_topology()
    clients = [n for n in topology.get_nodes() if 'client' in n.name]
    brokers = [n for n in topology.get_nodes() if 'broker' in n.name]
    execute_vivaldi(topology, node_filter=lambda n: 'broker' in n.name, min_executions=300)
    env = simpy.Environment()
    proto = Protocol(env, topology)
    for c in clients:
        env.process(client(env, proto, c, brokers[0]))
    for b in brokers:
        env.process(broker(proto, b, brokers))

    experiment = ClientExperiment(topology, clients, brokers)

    headers = ['rmse', 'corr_neigh', 'corr_region', 'vivaldi_runs']
    print(' ' * 7, '\t'.join(map(lambda s: f'{s:>12}', headers)))
    results = []
    for i in range(1, 16):
        env.run(until=i * 60 * 1000)  # i minutes
        result = experiment.calculate_errors()
        results.append([i, *result])
        print(f'{i:2d} min:', '\t'.join(map(lambda s: f'{s: 12.3f}', result)))

    results = np.array(results)
    experiment.plot_results(results, 'simulation', 0, 'minutes of execution')


if __name__ == '__main__':
    main()
