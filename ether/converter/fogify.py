from collections import defaultdict
from typing import Dict, NamedTuple, List

from ether.topology import Topology
from ether.util import to_size_string
from FogifySDK import FogifySDK
from ether.core import Node

class Placement(object):
    """
    A small class for placement policy definition.
    The services (services names) should be described in the initial docker-compose file.
    """

    def __init__(self):
        self.topology = dict()

    def deploy_service_to_node(self, service_name: str, node: Node):
        self.topology[node.name] = service_name

    def get_nodes(self) -> list:
        return [node_name for node_name in self.topology]

def topology_to_fogify(topology: Topology, fogify: FogifySDK, placement: Placement) -> FogifySDK:

    #  Node translation from ether to Fogify model
    for n in topology.get_nodes():
        if n.name in placement.get_nodes():
            num_of_cores = int(n.capacity.cpu_millis / 1000)

            fogify.add_node(n.name,
                            cpu_cores=num_of_cores,
                            cpu_freq= 1000,  # TODO update the frequency
                            memory=to_size_string(n.capacity.memory, 'G'))
                            # the limit of memory is 7 due to the PC's limitation power
            # TODO: ether has more capabilities hidden in labels (GPU, TPU, etc.)
    fogify.add_network("ether_net", bidirectional={})  # Maybe we need to describe the general network characteristics

    for n in topology.get_nodes():
        for j in topology.get_nodes():
            if type(n) == Node and type(j) == Node and n != j \
                    and n.name in placement.get_nodes() and j.name in placement.get_nodes():  # introduce link connection between compute nodes
                bandwidth = min([k.bandwidth for k in topology.route(n, j).hops])
                latency = round(float(topology.route(n, j).rtt/2), 2)
                fogify.add_link(
                    "ether_net",
                    from_node=n.name,
                    to_node=j.name,
                    bidirectional=False,
                    properties={
                        'latency': {
                            'delay': f'{latency}ms',
                        },
                        'bandwidth': f'{bandwidth}Mbps'
                    }
                )
    for node_name in placement.topology:
        fogify.add_deployment_node(
            node_name,
            placement.topology[node_name],  # How can we introduce services in ether?
            node_name,
            networks=["ether_net"]
        )

    return fogify