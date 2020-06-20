import unittest

import ether.inet.fetch.wondernetwork as wondernetwork


class TestWondernetwork(unittest.TestCase):

    def test_fetch(self):
        measurements = wondernetwork.fetch()

        self.assertIn('Amsterdam', {m.source for m in measurements}, 'Measurements should contain a region')

        m = measurements[0]
        self.assertGreater(m.avg, 0, 'Measurement should contain latencies')
