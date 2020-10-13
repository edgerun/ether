from sklearn.metrics import mean_squared_error

import matplotlib.pyplot as plt
from ether.scenarios.cloudregions import CloudRegionsScenario
from ether.topology import Topology
from examples.vivaldi.util import execute_vivaldi, distances, qq_plot_distances


def main():
    topology = Topology()
    topology.load_inet_graph('cloudping')
    regions = list(topology.nodes)

    scenario = CloudRegionsScenario(regions, [(5, 1)] * len(regions))
    scenario.materialize(topology)

    execute_vivaldi(topology)
    (measured, calculated) = distances(topology)
    qq_plot_distances(measured, calculated)
    plt.show()

    print('rmse:', mean_squared_error(measured, calculated, squared=False))


if __name__ == '__main__':
    main()
