import unittest

from ether.graphs.model.matrix import LatencyMatrix
from ether.graphs.network import create_latency_network_graph


class NetworkTest(unittest.TestCase):

    def test_create_latency_network_graph(self):
        regions = ['a', 'b', 'c', 'd']
        latencies = {
            'a': {'b': 10.2, 'c': 200.12, 'd': 59},
            'b': {'a': 10.2, 'c': 5.12},
            'c': {'a': 200.12, 'b': 5.12}
        }
        matrix = LatencyMatrix(regions, latencies)

        network_graph = create_latency_network_graph(matrix)

        self.assertIsNotNone(network_graph)

        self.assertEqual(network_graph['a']['b']['weight'], latencies['a']['b'])
        self.assertEqual(network_graph['a']['c']['weight'], latencies['a']['c'])
        self.assertEqual(network_graph['a']['d']['weight'], latencies['a']['d'])
        self.assertEqual(network_graph['b']['a']['weight'], latencies['b']['a'])
        self.assertEqual(network_graph['b']['c']['weight'], latencies['b']['c'])
        self.assertEqual(network_graph['c']['a']['weight'], latencies['c']['a'])
        self.assertEqual(network_graph['c']['b']['weight'], latencies['c']['b'])
        self.assertEqual(network_graph['d']['a']['weight'], latencies['a']['d'])
        self.assertEqual(network_graph['d']['b']['weight'], -1)
        self.assertEqual(network_graph['d']['c']['weight'], -1)
