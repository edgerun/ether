import matplotlib.pyplot as plt
import networkx as nx
from srds import ParameterizedDistribution

from ether.blocks.cells import IoTComputeBox, Cloudlet, FiberToExchange, MobileConnection
from ether.blocks.nodes import create_rpi3_node, create_nuc_node, create_tx2_node
from ether.cell import SharedLinkCell, GeoCell
from ether.core import Node, Link
from ether.topology import Topology


class nodes:
    nuc = create_nuc_node
    rpi3 = create_rpi3_node
    tx2 = create_tx2_node


lognorm = ParameterizedDistribution.lognorm


def node_name(obj):
    if isinstance(obj, Node):
        return obj.name
    elif isinstance(obj, Link):
        return f'link_{id(obj)}'
    else:
        return str(obj)


def main():
    topology = Topology()

    aot_node = IoTComputeBox(nodes=[nodes.rpi3, nodes.rpi3])
    neighborhood = lambda size: SharedLinkCell(
        nodes=[
            [aot_node] * size,
            IoTComputeBox([nodes.nuc] + ([nodes.tx2] * size * 2))
        ],
        shared_bandwidth=500,
        backhaul=MobileConnection('internet_chix'))
    city = GeoCell(
        5, nodes=[neighborhood], density=lognorm((0.82, 2.02)))
    cloudlet = Cloudlet(
        5, 2, backhaul=FiberToExchange('internet_chix'))

    topology.add(city)
    topology.add(cloudlet)

    #######################

    pos = nx.spring_layout(topology)  # positions for all nodes

    # nodes

    netnodes = [node for node in topology.nodes if
                not str(node).startswith('link_') and
                not str(node).startswith('switch_') and
                not str(node).startswith('internet')
                ]
    links = [node for node in topology.nodes if str(node).startswith('link_')]
    switches = [node for node in topology.nodes if str(node).startswith('switch_')]

    nx.draw_networkx_nodes(topology, pos,
                           nodelist=netnodes,
                           node_color='b',
                           node_size=300,
                           alpha=0.8)
    nx.draw_networkx_nodes(topology, pos,
                           nodelist=links,
                           node_color='g',
                           node_size=50,
                           alpha=0.9)
    nx.draw_networkx_nodes(topology, pos,
                           nodelist=switches,
                           node_color='y',
                           node_size=200,
                           alpha=0.8)
    nx.draw_networkx_nodes(topology, pos,
                           nodelist=[node for node in topology.nodes if
                                     isinstance(node, str) and node.startswith('internet')],
                           node_color='r',
                           node_size=800,
                           alpha=0.8)

    nx.draw_networkx_edges(topology, pos, width=1.0, alpha=0.5)
    nx.draw_networkx_labels(topology, pos, dict(zip(netnodes, netnodes)), font_size=8)
    # nx.draw_networkx_labels(topology, pos, dict(zip(links, links)), font_size=8)
    plt.axis('off')
    fig = plt.gcf()
    fig.set_size_inches(18.5, 10.5)

    plt.show()  # display

    print('num nodes:', len(topology.nodes))


if __name__ == '__main__':
    main()
