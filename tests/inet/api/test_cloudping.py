import unittest

import ether.inet.api.cloudping as cloudping

class CloudPingTest(unittest.TestCase):

    def test_get_average(self):
        matrix = cloudping.get_average()
        self.assertIsNotNone(matrix, 'Matrix should not be None. Server returned different status code than 200')
        self.assertTrue(len(matrix.latencies) > 0, 'Matrix should contain latencies')
        self.assertTrue(len(matrix.regions) > 0, 'Matrix should contain regions')
