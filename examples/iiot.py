import matplotlib.pyplot as plt

from ether.core import Connection
from ether.scenarios.industrialiot import IndustrialIoTScenario
from ether.topology import Topology
from ether.vis import draw_basic


def main():
    topology = Topology()

    IndustrialIoTScenario(num_premises=3, internet='internet_chix').materialize(topology)
    IndustrialIoTScenario(num_premises=1, internet='internet_nyc').materialize(topology)

    topology.add_connection(Connection('internet_chix', 'internet_nyc', 10))

    draw_basic(topology)
    fig = plt.gcf()
    fig.set_size_inches(18.5, 10.5)
    plt.show()  # display


if __name__ == '__main__':
    main()
