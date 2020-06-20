import unittest

import networkx as nx

from ether.inet.graph import load_from_file, load_latest, graph_directory


class TestGraph(unittest.TestCase):

    def test_load_to_graph(self):
        g = nx.DiGraph()

        load_from_file(g, f'{graph_directory}/cloudping_latest.graphml')
        self.assertIn('internet_eu-north-1', g.nodes)

    def test_load_latest_to_graph(self):
        g = nx.DiGraph()
        load_latest(g, 'cloudping')
        self.assertIn('internet_eu-north-1', g.nodes)
