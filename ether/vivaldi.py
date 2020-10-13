import random
from typing import Tuple

import numpy as np

from ether.core import Node, Coordinate

"""
Implementation of the vivaldi algorithm [1] to calculate network coordinates. Parts of the implementation (especially
apply_force) were ported from Hashicorp's Go implementation 'Serf' [2].

[1] F. Dabek, R. Cox, F. Kaashoek, and R. Morris, ‘Vivaldi: A Decentralized Network Coordinate System’,
    in Proceedings of the 2004 Conference on Applications, Technologies, Architectures, and Protocols for
    Computer Communications, New York, NY, USA, 2004, pp. 15–26, doi: 10.1145/1015467.1015471.
[2] https://github.com/hashicorp/serf/blob/master/coordinate/coordinate.go
"""

c_e = 0.9
"a tuning parameter that influences the weight of the current error in each cycle"
c_c = 0.25
"tuning parameter that modulates the force"
dimensions = 8
"dimensionality of the vector space"

max_error = 1.5
min_height = 10e-6


class VivaldiCoordinate(Coordinate):
    """
    Coordinate holds network coordinates and local error, used by the Vivaldi coordinate mapping algorithm.
    """
    position: np.ndarray
    height: float
    error: float
    vivaldi_runs: int

    def __init__(self, position: np.ndarray = None, height: float = None, error: float = None):
        super().__init__()
        self.position = position if position is not None else np.array([0.0] * dimensions)
        self.height = height if height is not None else min_height
        self.error = error or max_error
        self.vivaldi_runs = 0

    def __repr__(self) -> str:
        return f'Coordinate({self.position}, height={self.height}, error={self.error})'

    def apply_force(self, force: float, other: 'VivaldiCoordinate'):
        unit, norm = self._unit_vector_at(self.position, other.position)
        self.position += unit * force
        if norm > 0:
            self.height += (self.height + other.height) * force / norm
            self.height = max(self.height, 10e-3)

    def distance_to(self, other: 'VivaldiCoordinate'):
        return np.linalg.norm(self.position - other.position) + self.height + other.height

    @staticmethod
    def _unit_vector_at(v1: np.ndarray, v2: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        returns a unit vector pointing at v1 from v2
        """
        result = v1 - v2
        norm = np.linalg.norm(result)
        if result.any():
            return result/norm, norm
        else:
            result = [random.gauss(0, 1) for _ in result]
            norm = np.linalg.norm(result)
            return result/norm, 0.0


def execute(node: Node, other: Node, rtt: float):
    if not node.coordinate:
        node.coordinate = VivaldiCoordinate()
    if not other.coordinate:
        other.coordinate = VivaldiCoordinate()
    elif not isinstance(other.coordinate, VivaldiCoordinate):
        raise TypeError('Nodes have different Coordinate types')

    # sample weight balances local and remote error
    weight = node.coordinate.error / (node.coordinate.error + other.coordinate.error)
    old_distance = np.linalg.norm(node.coordinate.position - other.coordinate.position)
    old_distance += node.coordinate.height + other.coordinate.height
    sample_error = np.abs(old_distance - rtt) / rtt
    node.coordinate.error = sample_error * c_e * weight + node.coordinate.error * (1 - c_e * weight)
    node.coordinate.error = min(node.coordinate.error, max_error)
    delta = c_c * weight
    force = delta * (rtt - old_distance)
    node.coordinate.apply_force(force, other.coordinate)
    node.coordinate.vivaldi_runs += 1
