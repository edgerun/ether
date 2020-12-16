from typing import List, Union, Callable

import networkx as nx
import numpy as np
from matplotlib import pyplot as plt
from sklearn.metrics import mean_squared_error

from ether import vivaldi
from ether.core import Node
from ether.topology import Topology
from ether.vivaldi import VivaldiCoordinate


class ClientExperiment:
    """
    This experiment assumes that the topology consists of a set of clients and a set of brokers. Furthermore,
    each node resides in a region, which is determined by the closest node with the name internet_%s, e.g.,
    internet_eu-west-1 (where eu-west-1 is the region name).
    """
    topology: Topology
    clients: List[Node]
    brokers: List[Node]

    def __init__(self, topology: Topology, clients: List[Node], brokers: List[Node]):
        self.topology = topology
        self.clients = clients
        self.brokers = brokers

    @staticmethod
    def region_of(node: Node):
        return node.name[node.name.index('internet_'):]

    def find_true_neighbor_broker(self, node: Node) -> Node:
        return next(n for n in nx.dfs_preorder_nodes(self.topology, node) if n in self.brokers)

    def find_vivaldi_closest_brokers(self, node):
        return sorted(self.brokers, key=lambda b: node.distance_to(b))

    def client_vivaldi(self, client: Node, brokers: List[Node], n=5):
        for broker in brokers:
            for _ in range(n):
                dist = self.topology.route(client, broker).rtt
                vivaldi.execute(client, broker, dist)

    def run(self, *neighbor_selectors: Union[Callable[[Node], List[Node]], List[Node]]) -> np.ndarray:
        # reset coordinates of clients
        for client in self.clients:
            client.coordinate = VivaldiCoordinate()
        # contains results of measurements for each iteration
        results = []
        for n in range(20):
            for client in self.clients:
                for neighbors in neighbor_selectors:
                    if callable(neighbors):
                        neighbors = neighbors(client)
                    self.client_vivaldi(client, neighbors)

            result = self.calculate_errors()
            results.append([n, *result])

        return np.array(results)

    def calculate_errors(self):
        vivaldi_runs = np.mean([c.coordinate.vivaldi_runs for c in self.clients])
        # distances to closest neighbor of each client as estimated by vivaldi
        pred_dists = []
        # distances to closest neighbor calculated from ground truth
        true_dists = []
        # number of clients where vivaldi-estimated neighbor equals true neighbor
        correct_neighbors = 0
        # number of clients where the vivaldi-estimated neighbor is in same region as the client itself
        correct_regions = 0
        for c in self.clients:
            # find closest broker using vivaldi and append distance
            vivaldi_neighbor = self.find_vivaldi_closest_brokers(c)[0]
            pred_dists.append(c.distance_to(vivaldi_neighbor))
            # find closest broker using topology graph and append mode distance
            true_neighbor = self.find_true_neighbor_broker(c)
            true_dists.append(self.topology.route(c, true_neighbor, use_mode=True).rtt)
            if true_neighbor == vivaldi_neighbor:
                correct_neighbors += 1
            if self.region_of(true_neighbor) == self.region_of(vivaldi_neighbor):
                correct_regions += 1
        # calculate root mean squared error of estimated neighbor distances.
        # note: we compare the distance between the neighbor as seen by vivaldi
        # and the distance to the actual neighbor
        rmse = mean_squared_error(true_dists, pred_dists, squared=False)
        result = [rmse, correct_neighbors / len(self.clients) * 100,
                  correct_regions / len(self.clients) * 100, vivaldi_runs]
        return result

    @staticmethod
    def plot_results(results: np.ndarray, title: str, x_index=4, x_label='executions per client'):
        """
        Renders the following two plots side-by-side in one figure:
          * the root mean squared error over time (i.e., vivaldi executions)
          * percentage of correctly predicted region and neighbor of each client over time

        :param results: ndarray of results as returned by self.run
        :param title: the title of the figure
        :param x_index: index of results array for x values
        :param x_label: label for x axis
        """
        # 0: n
        # 1: rmse
        # 2: correct_neighbors
        # 3: correct_regions
        # 4: vivaldi_runs
        fig: plt.Figure
        ax1: plt.Axes
        ax2: plt.Axes
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
        fig.suptitle(title)

        color = 'tab:blue'
        ax1.set_xlabel(x_label)
        ax1.set_ylabel('RMSE')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.set_ylabel('rmse', color=color)
        ax1.scatter(results[:, x_index], results[:, 1], color=color)
        ax1.set_ylim(ymin=0)
        _ = ax1.legend()

        ax2.set_xlabel(x_label)
        ax2.set_ylabel('percent correctly predicted')
        ax2.plot(results[:, x_index], results[:, 3], color='tab:blue', label='region')
        ax2.plot(results[:, x_index], results[:, 2], color='tab:red', label='neighbor')
        ax2.set_ylim(ymin=0, ymax=110)
        _ = ax2.legend(loc='lower right')

        fig.tight_layout()
        fig.subplots_adjust(top=0.88)  # this is required to leave space for suptitle
        plt.show()

    def run_and_plot(self, title: str, *neighbor_selectors: Union[Callable[[Node], List[Node]], List[Node]]):
        """
        Wrapper that runs the experiment and plots the result.

        :param title: title to use for plots
        :param neighbor_selectors: determine how clients select neighbors to which they perform measurements
        """
        self.plot_results(self.run(*neighbor_selectors), title)
