from ether.inet.fetch import cloudping, gcloudping, wondernetwork
from ether.inet.fetch.data import Measurement

name = 'fetch'

sources = {
    'cloudping': cloudping,
    'gcloudping': gcloudping,
    'wondernetwork': wondernetwork
}

__all__ = [
    Measurement,
    sources
]
