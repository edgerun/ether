from typing import List, Optional

import requests

from ether.inet.model.matrix import LatencyMatrix


def get_matrix() -> Optional[LatencyMatrix]:
    """
    Fetches the latency matrix for google cloud servers from gcloudping.com
    :return: in case of a successful request the matrix, otherwise None
    """
    url = 'http://35.197.238.199/api/latencies/matrix'
    response = requests.get(url)
    if response.status_code != 200:
        return None
    response = response.json()
    return create_latency_matrix(regions=response['regions'], latencies=response['latencies'])


def create_latency_matrix(regions: List[str], latencies: List[List[str]]) -> LatencyMatrix:
    matrix_latencies = dict()
    for region_index, region in enumerate(regions):
        region_latencies = dict()
        for region_to_index, latency in enumerate(latencies[region_index]):
            if latency is not None:
                region_latencies[regions[region_to_index]] = float(latency)
            else:
                region_latencies[regions[region_to_index]] = -1
        matrix_latencies[region] = region_latencies
    return LatencyMatrix(regions, matrix_latencies)
