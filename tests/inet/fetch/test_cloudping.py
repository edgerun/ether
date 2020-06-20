import unittest

import ether.inet.fetch.cloudping as cloudping


class TestCloudping(unittest.TestCase):

    def test_fetch(self):
        measurements = cloudping.fetch()

        self.assertIn('eu-central-1', {m.source for m in measurements}, 'Measurements should contain a region')

        m = measurements[0]
        self.assertGreater(m.avg, 0, 'Measurement should contain latencies')
