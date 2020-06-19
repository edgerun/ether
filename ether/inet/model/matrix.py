from dataclasses import dataclass
from typing import Dict, List


@dataclass
class LatencyMatrix:
    regions: List[str]
    latencies: Dict[str, Dict[str, float]]
