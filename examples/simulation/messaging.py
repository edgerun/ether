import random
from itertools import product

import numpy as np

from ether import vivaldi
from examples.simulation.protocol import *
from examples.vivaldi.client_experiment import ClientExperiment
from examples.vivaldi.urban_sensing import create_topology
from examples.vivaldi.util import execute_vivaldi


def client(env: simpy.Environment, protocol: Protocol, node: Node, initial_broker: Node):
    selected_broker = initial_broker

    def ping_brokers(brokers: List[Node]):
        for (b, _) in product(brokers, range(5)):
            protocol.send(node, b, PingMessage())
            (source, reply) = yield protocol.receive(node)
            if isinstance(reply, PongMessage):
                latency = env.now - reply.timestamp
                vivaldi.execute(node, source, latency * 2)

    def ping_random(n=5):
        protocol.send(node, selected_broker, FindRandomBrokersRequest())
        (_, message) = yield protocol.receive(node)

        if not isinstance(message, FindRandomBrokersResponse):
            raise AssertionError(f'unexpected message received: {message}')
        yield from ping_brokers(message.brokers[:n])

    def ping_closest(n=5):
        protocol.send(node, selected_broker, FindClosestBrokersRequest())
        (_, message) = yield protocol.receive(node)

        if not isinstance(message, FindClosestBrokersResponse):
            raise AssertionError(f'unexpected message received: {message}')
        yield from ping_brokers(message.brokers[:n])

    yield from ping_random()
    while True:
        yield from ping_closest()
        yield env.timeout(60_000)
        yield from ping_random()


def broker(env: simpy.Environment, protocol: Protocol, node: Node, brokers: List[Node]):
    while True:
        source: Node
        message: Message
        (source, message) = yield protocol.receive(node)
        assert isinstance(node.coordinate, VivaldiCoordinate)
        if isinstance(message, PingMessage):
            response = PongMessage(node.coordinate, env.now)
        elif isinstance(message, FindRandomBrokersRequest):
            response = FindRandomBrokersResponse(random.choices(brokers, k=5))
        elif isinstance(message, FindClosestBrokersRequest):
            response = FindClosestBrokersResponse(sorted(brokers, key=lambda b: source.distance_to(b))[:5])
        else:
            continue
        protocol.send(node, source, response)


def main():
    topology = create_topology()
    clients = [n for n in topology.get_nodes() if 'client' in n.name]
    brokers = [n for n in topology.get_nodes() if 'broker' in n.name]
    execute_vivaldi(topology, node_filter=lambda n: 'broker' in n.name, min_executions=300)
    env = simpy.Environment()
    proto = Protocol(env, topology)
    for c in (n for n in topology.get_nodes() if 'client' in n.name):
        env.process(client(env, proto, c, random.choice(brokers)))
    for b in (n for n in topology.get_nodes() if 'broker' in n.name):
        env.process(broker(env, proto, b, brokers))

    experiment = ClientExperiment(topology, clients, brokers)

    headers = ['rmse', 'corr_neigh', 'corr_region', 'vivaldi_runs']
    print(' ' * 7, '\t'.join(map(lambda s: f'{s:>12}', headers)))
    results = []
    for i in range(1, 16):
        for c in random.choices(clients, k=10):
            topology.remove_node(c)

        env.run(until=i * 60 * 1000)  # i minutes
        result = experiment.calculate_errors()
        results.append([i, *result])
        print(f'{i:2d} min:', '\t'.join(map(lambda s: f'{s: 12.3f}', result)))

    results = np.array(results)
    experiment.plot_results(results, 'simulation', 0, 'minutes of execution')


if __name__ == '__main__':
    main()
