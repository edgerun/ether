from unittest import TestCase

import matplotlib.pyplot as plt
import networkx as nx

from ether.blocks.nodes import create_nuc_node, create_rpi3_node
from ether.core import Connection, Link
from ether.topology import Topology


class TestNetworkx(TestCase):
    def test_graph(self):
        topology = Topology()

        n0 = create_nuc_node()
        n1 = create_nuc_node()
        n2 = create_nuc_node()
        n3 = create_nuc_node()
        n4 = create_rpi3_node()

        l0 = Link(tags={'name': 'link_%s' % n0.name})
        l1 = Link(tags={'name': 'link_%s' % n1.name})
        l2 = Link(tags={'name': 'link_%s' % n2.name})
        l3 = Link(tags={'name': 'link_%s' % n3.name})
        l4 = Link(tags={'name': 'link_%s' % n4.name})

        topology.add_connection(Connection(n0, l0))
        topology.add_connection(Connection(n1, l1))
        topology.add_connection(Connection(n2, l2))
        topology.add_connection(Connection(n3, l3))
        topology.add_connection(Connection(n4, l4))

        topology.add_connection(Connection(l0, l4), True)
        topology.add_connection(Connection(l1, l2), True)
        topology.add_connection(Connection(l2, l3), True)
        topology.add_connection(Connection(l2, l4), True)
        topology.add_connection(Connection(l1, l4), True)
        topology.add_connection(Connection(l3, l4), True)
        topology.add_connection(Connection(l2, l4), True)

        gen = nx.all_pairs_shortest_path(topology)
        for p in gen:
            print('-----')
            print(p)

        print('path', topology.path(n1, n4))

        r = topology.route(n1, n4)
        print('route', r)

        pos = nx.kamada_kawai_layout(topology)  # positions for all nodes

        nx.draw_networkx_nodes(topology, pos)
        nx.draw_networkx_edges(topology, pos, width=1.0, alpha=0.5)
        nx.draw_networkx_labels(topology, pos, dict(zip([n1, n2, n3, n4], [n1, n2, n3, n4])), font_size=8)

        plt.axis('off')
        fig = plt.gcf()
        fig.set_size_inches(18.5, 10.5)

        plt.show()  # display

        print('num nodes:', len(topology.nodes))
