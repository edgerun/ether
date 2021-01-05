import os

from FogifySDK import FogifySDK
import matplotlib.pyplot as plt
from ether.converter.fogify import topology_to_fogify, Placement
from ether.scenarios.industrialiot import IndustrialIoTScenario
from ether.topology import Topology
from ether.vis import draw_basic

if __name__ == '__main__':
    ether_topology = Topology()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    docker_compose_file = dir_path+"/simple-docker-compose.yaml"
    fogify = FogifySDK("http://contorller:5000", docker_compose_file)
    scen = IndustrialIoTScenario()
    scen.materialize(ether_topology)

    # determine the placement
    # for testing reasons we will deploy the same service ("test") on every node
    placement = Placement()
    for node in ether_topology.get_nodes():
        placement.deploy_service_to_node("test", node)

    # Generate the fogify model
    fogify_model = topology_to_fogify(ether_topology, fogify, placement)
    fogify_model.upload_file(False)  # with False as parameter, the function generates the fogified-docker-compose file
    # here we can deploy the generated mode with fogify.deploy() function
    draw_basic(ether_topology)
    fig = plt.gcf()
    fig.set_size_inches(18.5, 10.5)
    plt.show()  # display
