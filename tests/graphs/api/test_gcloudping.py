import unittest

import ether.graphs.api.gcloudping as gcloudping


class GCloudPingTest(unittest.TestCase):

    def test_get_matrix(self):
        matrix = gcloudping.get_matrix()
        self.assertIsNotNone(matrix, 'Matrix should not be None. Server returned different status code than 200')
        self.assertTrue(len(matrix.latencies) > 0, 'Matrix should contain latencies')
        self.assertTrue(len(matrix.regions) > 0, 'Matrix should contain regions')
