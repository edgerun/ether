from srds import ParameterizedDistribution

from ether.blocks import nodes
from ether.blocks.cells import Cloudlet, IoTComputeBox, MobileConnection, FiberToExchange
from ether.cell import GeoCell, SharedLinkCell
from ether.topology import Topology

default_num_cells = 3
default_cloudlet_size = (5, 2)
default_cell_density = ParameterizedDistribution.lognorm((0.82, 2.02))


class UrbanSensingScenario:
    def __init__(self, num_cells=default_num_cells, cell_density=default_cell_density,
                 cloudlet_size=default_cloudlet_size, internet='internet') -> None:
        """
        The UrbanSensingScenario builds on ideas from the Array of Things project, but extends it with proximate compute
        resources and adds a cloudlet to the city.

        The city is divided into cells, e.g., neighborhoods, and each cell has multiple urban sensing nodes and
        proximate compute resources. The devices in a cell are connected via a shared link. The city also hosts a
        cloudlet composed of server computers.

        The high-level parameters are: the number of cells, the cell density (number of nodes per cell), and the
        cloudlet size.

        :param num_cells: the number of cells to create, e.g., the neighborhoods in a city
        :param cell_density: the distribution describing the number of nodes in each neighborhood
        :param cloudlet_size: a tuple describing the number of servers in each rack, and the number of racks
        :param internet: the internet backbone that's being connected to (see `inet` package)
        """
        super().__init__()
        self.num_cells = num_cells
        self.cell_density = cell_density
        self.cloudlet_size = cloudlet_size
        self.internet = internet

    def materialize(self, topology: Topology):
        topology.add(self.create_city())
        topology.add(self.create_cloudlet())

    def create_city(self) -> GeoCell:
        aot_node = IoTComputeBox(nodes=[nodes.rpi3, nodes.rpi3])

        neighborhood = lambda size: SharedLinkCell(
            nodes=[
                [aot_node] * size,
                IoTComputeBox([nodes.nuc] + ([nodes.tx2] * size * 2))
            ],
            shared_bandwidth=500,
            backhaul=MobileConnection(self.internet)
        )

        city = GeoCell(self.num_cells, nodes=[neighborhood], density=self.cell_density)

        return city

    def create_cloudlet(self) -> Cloudlet:
        return Cloudlet(*self.cloudlet_size, backhaul=FiberToExchange(self.internet))
