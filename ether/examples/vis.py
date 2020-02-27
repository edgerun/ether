import matplotlib.pyplot as plt
import networkx as nx
from srds import ParameterizedDistribution

from ether.cell import Cloudlet, FiberToExchange, MobileConnection, SharedLinkCell, IoTComputeBox, GeoCell, Cell
from ether.core import Node, Link
from ether.nodes import create_rpi3_node, create_nuc_node, create_tx2_node
from ether.topology import Topology


class nodes:
    nuc = create_nuc_node
    rpi3 = create_rpi3_node
    tx2 = create_tx2_node


lognorm = ParameterizedDistribution.lognorm


class FriendlyTopology(Topology):
    def __lshift__(self, other):
        if isinstance(other, Cell):
            other.materialize(self)
        return self


topology = FriendlyTopology(list(), list())

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

topology << city
topology << cloudlet

t = topology

#######################

G = nx.Graph()


def node_name(obj):
    if isinstance(obj, Node):
        return obj.name
    elif isinstance(obj, Link):
        return f'link_{id(obj)}'
    else:
        return str(obj)


for edge in t.edges:
    a = edge.source
    b = edge.target

    la = node_name(a)
    lb = node_name(b)

    G.add_edge(la, lb)

print(G.nodes)

pos = nx.spring_layout(G)  # positions for all nodes

# nodes

netnodes = [node for node in G.nodes if
            not str(node).startswith('link_') and
            not str(node).startswith('switch_') and
            not str(node).startswith('internet')
            ]
links = [node for node in G.nodes if str(node).startswith('link_')]
switches = [node for node in G.nodes if str(node).startswith('switch_')]

nx.draw_networkx_nodes(G, pos,
                       nodelist=netnodes,
                       node_color='b',
                       node_size=300,
                       alpha=0.8)
nx.draw_networkx_nodes(G, pos,
                       nodelist=links,
                       node_color='r',
                       node_size=50,
                       alpha=0.8)
nx.draw_networkx_nodes(G, pos,
                       nodelist=switches,
                       node_color='y',
                       node_size=200,
                       alpha=0.8)
nx.draw_networkx_nodes(G, pos,
                       nodelist=[node for node in G.nodes if node.startswith('internet')],
                       node_color='g',
                       node_size=800,
                       alpha=0.8)

nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)
nx.draw_networkx_labels(G, pos, dict(zip(netnodes, netnodes)), font_size=8)
# nx.draw_networkx_labels(G, pos, dict(zip(links, links)), font_size=8)
plt.axis('off')
fig = plt.gcf()
fig.set_size_inches(18.5, 10.5)

plt.show()  # display

print('num nodes:', len(G.nodes))
