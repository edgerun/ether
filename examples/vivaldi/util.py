import random
from itertools import permutations, combinations
from typing import List, Callable, Iterable, Tuple

import matplotlib.pyplot as plt
import numpy as np

from ether import vivaldi
from ether.core import Node
from ether.topology import Topology


def random_neighbors(nodes: List[Node]) -> Iterable[Tuple[Node, Node]]:
    """Continuously yields random permutations of tuples chosen from the given node list."""
    pairs = list(permutations(nodes, 2))
    while True:
        random.shuffle(pairs)
        yield from pairs


def execute_vivaldi(topology: Topology, node_filter: Callable[[Node], bool] = lambda _: True,
                    neighbor_generator: Callable[[List[Node]], Iterable[Tuple[Node, Node]]] = random_neighbors,
                    min_executions: int = 100) -> int:
    """
    Executes vivaldi on each node of the topology until each node has executed vivaldi at least min_executions times.

    :param topology: the topology to operate on
    :param node_filter: can be used to run vivaldi only on certain nodes
    :param neighbor_generator: a generator that, given the topology and the selected nodes, yields (n1, n2) neighbor
    tuples. The default value is a function that yields shuffled permutations of the nodes.
    :param min_executions: the minimum number of executions per node, which serves as break condition
    :return: the total number of vivaldi executions
    """
    nodes = list(filter(node_filter, topology.get_nodes()))
    executions = 0
    for node1, node2 in neighbor_generator(nodes):
        if all(map(lambda n: n.coordinate and n.coordinate.vivaldi_runs >= min_executions, nodes)):
            break
        vivaldi.execute(node1, node2, topology.route(node1, node2).rtt)
        executions += 1
    return executions


def distances(topology: Topology, node_filter: Callable[[Node], bool] = lambda _: True) -> (List[float], List[float]):
    """
    Calculates `true_distances`, i.e., the list of distances when calculating the routes using the mode of the
    distance distributions, and `vivaldi_distances`, i.e., the list of distances calculated using vivaldi coordinates

    :param topology: the topology to run calculations on
    :param node_filter: if set, filters the set of nodes
    :return: a tuple of (true_distances, vivaldi_distances)
    """
    pairs = list(combinations(filter(node_filter, topology.get_nodes()), 2))
    true_distances = [topology.route(node1, node2, use_mode=True).rtt for node1, node2 in pairs]
    vivaldi_distances = [node1.distance_to(node2) for node1, node2 in pairs]
    return true_distances, vivaldi_distances


def qq_plot_distances(measured_distances, coordinate_distances, ax: plt.Axes = None):
    """Plots a QQ–plot comparing distances predicted by vivaldi and ground truth distances"""
    if ax is None:
        ax = plt.axes()
    ax.scatter(np.sort(measured_distances), np.sort(coordinate_distances), s=5)
    line = np.arange(np.min(measured_distances), np.max(measured_distances))
    ax.plot(line, line, color='r', linewidth=1.0)
    ax.set_xlabel('measured rtt')
    ax.set_ylabel('estimated rtt')
