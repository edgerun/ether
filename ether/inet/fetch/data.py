from typing import NamedTuple


class Measurement(NamedTuple):
    source: str
    destination: str

    avg: float
    max: float = -1
    min: float = -1
