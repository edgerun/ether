import unittest

import ether.inet.fetch.gcloudping as gcloudping


@unittest.skip("gcloudping api is often down")
class TestGcloudping(unittest.TestCase):

    def test_fetch(self):
        measurements = gcloudping.fetch()

        self.assertIn('us-east4', {m.source for m in measurements}, 'Measurements should contain a region')

        m = measurements[0]
        self.assertGreater(m.avg, 0, 'Measurement should contain latencies')
