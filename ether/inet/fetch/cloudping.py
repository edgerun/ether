from typing import List

import requests

from ether.inet.fetch.data import Measurement

resource = 'https://api.cloudping.co/averages/day'


def fetch() -> List[Measurement]:
    data = _get_averages()

    result = list()

    for region_from in data:
        src = region_from['region']

        for region_to in region_from['averages']:
            dst = region_to['regionTo']
            avg = region_to['average']
            result.append(Measurement(src, dst, avg))

    return result


def _get_averages(days: int = 7):
    url = f'{resource}/{days}'
    response = requests.get(url)

    if response.status_code != 200:
        raise RuntimeError(f'invalid response with code {response.status_code}')

    return response.json()
