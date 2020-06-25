from ether.core import Connection
from ether.scenarios.industrialiot import IndustrialIoTScenario
from ether.topology import Topology
from examples import vis


def main():
    topology = Topology()

    IndustrialIoTScenario(num_premises=3, internet='internet_chix').materialize(topology)
    IndustrialIoTScenario(num_premises=1, internet='internet_nyc').materialize(topology)

    topology.add_connection(Connection('internet_chix', 'internet_nyc', 10))

    vis.plot(topology)


if __name__ == '__main__':
    main()
