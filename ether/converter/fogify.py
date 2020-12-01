from collections import defaultdict
from typing import Dict, NamedTuple, List

from ether.topology import Topology
# TODO: import fogify model and classes instead
from ether.util import to_size_string


class FogifyModel(NamedTuple):
    nodes: List[Dict]
    networks: List[Dict]
    topology: List[Dict]


def serialize(fogify: FogifyModel, yaml_file):
    # TODO
    pass


def topology_to_fogify(topology: Topology) -> FogifyModel:
    nodes = list()
    networks = defaultdict(dict)
    fogify_topology = list()

    for n in topology.get_nodes():
        nodes.append({
            'name': n.name,
            'capabilities': {
                'processors': {
                    'cores': int(n.capacity.cpu_millis / 1000),
                    'clock': 0,  # TODO
                },
                'memory': to_size_string(n.capacity.memory, 'G'),
                # TODO: ether has more capabilities hidden in labels (GPU, TPU, etc.)
            }
        })

    # TODO: need to clarify fogify internet network
    # this is kinda roundabout, as we're reconstructing the original higher-level 'Cloudlet', 'LANCell', etc structure
    for link in topology.get_links():
        if link.tags.get('type') == 'downlink':
            name = link.tags['name'][5:]  # cut off 'down_' prefix of uplink
            networks[name]['name'] = name
            networks[name]['uplink'] = {
                'bandwidth': f'{link.bandwidth}Mbps',
                'latency': {
                    'delay': 0,
                },
                'drop': '0.1%',  # TODO: QoS modelling is still quite rudimentary in ether
            }

            for edge in topology.in_edges([link]):
                connection = topology.get_edge_data(edge[0], edge[1])['connection']
                networks[name]['downlink']['latency']['delay'] = float(connection.get_mode_latency())
                break  # should only be one edge

        elif link.tags.get('type') == 'uplink':
            name = link.tags['name'][3:]  # cut off 'up_' prefix of uplink
            networks[name]['name'] = name
            networks[name]['downlink'] = {
                'bandwidth': f'{link.bandwidth}Mbps',
                'latency': {
                    'delay': 0,
                },
                'drop': '0.1%',  # TODO: QoS modelling is still quite rudimentary in ether
            }

            for edge in topology.out_edges([link]):
                connection = topology.get_edge_data(edge[0], edge[1])['connection']
                networks[name]['downlink']['latency']['delay'] = float(connection.get_mode_latency())
                break  # should only be one edge

        # TODO: internet

    # TODO: collapse uplink/downlink to 'bidirectional' (fogify concept) if uplink == downlink with all QoS values

    model = FogifyModel(nodes, list(networks.values()), fogify_topology)
    print(model)
    return model
