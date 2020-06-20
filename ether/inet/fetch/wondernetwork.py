from typing import Dict, List

import requests

from ether.inet.fetch.data import Measurement

resource = 'https://wondernetwork.com/ping-data'

regions = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 26, 37, 208, 67, 47, 50, 96, 43, 200, 22, 104, 91, 19, 153, 60, 66, 34,
           244, 108]


def fetch() -> List[Measurement]:
    return _query(regions)


def _query(region_ids) -> List[Measurement]:
    regions_encoded = ','.join(map(str, region_ids))
    json = _get_json({'sources': regions_encoded, 'destinations': regions_encoded})
    data = json['pingData']

    result = list()

    for from_regions, to_regions in data.items():
        for _, measurement in to_regions.items():
            result.append(_parse_measurement(measurement))

    return result


def _get_json(params):
    response = requests.get(resource, params)

    if response.status_code != 200 and response.json():
        raise RuntimeError(f'invalid response with code {response.status_code}')

    return response.json()


def _parse_measurement(data: Dict) -> Measurement:
    return Measurement(
        avg=float(data['avg']),
        max=float(data['max']),
        min=float(data['min']),
        source=data['source_name'],
        destination=data['destination_name']
    )
