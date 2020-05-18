from typing import Dict, Optional

import requests

from ether.graphs.model.matrix import LatencyMatrix

base_url = 'https://api-demo.cloudping.co'


def get_average(days: int = 1) -> Optional[LatencyMatrix]:
    url = f'{base_url}/averages/day/{days}'
    response = requests.get(url)
    if response.status_code != 200:
        return None

    return _parse_matrix(response.json())


def _parse_matrix(data: Dict):
    latencies = _parse_latencies(data)
    return LatencyMatrix(regions=list(latencies.keys()), latencies=latencies)


def _parse_latencies(data: Dict) -> Dict[str, Dict[str, float]]:
    latencies = dict()
    for item in data:
        region = item['region']
        averages = dict()
        for x in item['averages']:
            averages[x['regionTo']] = x['average']
        latencies[region] = averages
    return latencies
