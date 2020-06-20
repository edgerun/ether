from srds import ParameterizedDistribution

from ether.blocks import nodes
from ether.blocks.cells import Cloudlet, IoTComputeBox, MobileConnection, FiberToExchange
from ether.cell import GeoCell, SharedLinkCell
from ether.topology import Topology

default_num_cells = 3
default_cloudlet_size = (5, 2)
default_cell_density = ParameterizedDistribution.lognorm((0.82, 2.02))


class UrbanSensingTopology:
    def __init__(self, num_cells=default_num_cells, cell_density=default_cell_density,
                 cloudlet_size=default_cloudlet_size, internet='internet') -> None:
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
