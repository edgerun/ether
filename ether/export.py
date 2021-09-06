from typing import Callable
from topology import Topology
from core import Node
import json


def export_to_tam_json(topology: Topology, output_file: str, value_projector: Callable[[Node], int]):
    """
    Function to export a topology to the format read by https://github.com/rpreiner/tam
    :param topology: The topology you wish to export
    :param output_file: A valid path (including the filename) where you want the output to be written to
    :param value_projector: A function which takes a Node as argument (can also be ether.Link) and ouptuts a value.
    This value is then used for the heatmap-like visualization. If you omit this all values will be 0 instead.
    :return:
    """
    nodes = []
    links = []
    if value_projector is None:
        value_projector = lambda: 0
    for node in topology.nodes:
        if isinstance(node, str):
            nodes.append({
                'id': id(node),
                'name': node,
                'value': 0
            })
            continue
        nodes.append({
            'id': id(node),
            'name': node.name if isinstance(node, Node) else node.tags['name'],
            'value': value_projector(node)
        })
    for edge in topology.edges.values():
        links.append({
            'source': id(edge['connection'].source),
            'target': id(edge['connection'].target),
            'directed': edge['directed']
        })
    full = {
        'nodes': nodes,
        'links': links
    }
    with open(output_file, 'w') as file:
        json.dump(full, file)
        file.flush()
        file.close()
