from dataclasses import dataclass
from typing import Optional, Dict, List

import requests

from ether.graphs.model.matrix import LatencyMatrix


@dataclass
class Measurement:
    avg: float
    max: float
    min: float
    source: str
    destination: str
    country: str
    source_name: str
    destination_name: str


def get_matrix() -> Optional[LatencyMatrix]:
    """
    Fetches the latency matrix for google cloud servers from https://wondernetwork.com/pings
    :return: in case of a successful request the matrix, otherwise None
    """
    regions = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 26, 37, 208, 67, 47, 50, 96, 43, 200, 22, 104, 91, 19, 153, 60, 66, 34,
               244, 108]
    regions_encoded = str(regions).replace('[', '').replace(']', '').replace(' ', '')
    url = f'https://wondernetwork.com/ping-data?sources={regions_encoded}&destinations={regions_encoded}'
    response = requests.get(url)
    if response.status_code != 200 and response.json():
        return None
    response = response.json()
    return create_latency_matrix(response['pingData'], response['sourcesList'], response['destinationsList'])


def create_latency_matrix(ping_data: Dict[str, Dict[str, Dict[str, any]]], sources_list: List[Dict],
                          destinations_list: List[Dict]):
    latencies = dict()
    regions = dict()

    for source in sources_list:
        regions[source['id']] = source['name']

    for destination in destinations_list:
        regions[destination['id']] = destination['name']

    for region_name in regions.values():
        latencies[region_name] = dict()

    for from_region, to_regions in ping_data.items():
        for to_region, measurement in to_regions.items():
            measurement = _parse_measurement(measurement)
            latencies[regions[from_region]][regions[to_region]] = measurement.avg

    return LatencyMatrix(
        regions=list(regions.values()),
        latencies=latencies
    )


def _parse_measurement(data: Dict) -> Measurement:
    return Measurement(
        avg=float(data['avg']),
        max=float(data['max']),
        min=float(data['min']),
        source=data['source'],
        destination=data['destination'],
        country=data['country'],
        source_name=data['source_name'],
        destination_name=data['destination_name']
    )
