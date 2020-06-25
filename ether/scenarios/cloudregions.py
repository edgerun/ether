from typing import List, Tuple

from ether.blocks.cells import Cloudlet
from ether.topology import Topology


class CloudRegionsScenario:

    def __init__(self, regions: List[str], region_size: List[Tuple[int, int]]) -> None:
        super().__init__()
        self.regions = regions
        self.region_size = region_size

    def materialize(self, topology: Topology):
        for i in range(len(self.regions)):
            size = self.region_size[i]
            Cloudlet(*size, backhaul=self.regions[i]).materialize(topology)
