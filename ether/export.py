import logging

from ether.core import Topology, Node, Link

logger = logging.getLogger(__name__)


class TopologyJsonExporter:

    def write(self, topology: Topology, fd, *args, **kwargs):
        import json
        json.dump(self.to_dict(topology), fd, *args, **kwargs)

    def get_values(self, vertex):
        return []

    def get_id(self, node):
        if isinstance(node, str):
            return node
        if isinstance(node, Node):
            return node.name
        if isinstance(node, Link):
            return '%s_%s' % (node.tags['type'], node.tags['name'])

    def get_node_type(self, node):
        if isinstance(node, Node):
            return 'HOST'
        if isinstance(node, Link):
            return 'LINK'
        if isinstance(node, str):
            if node.startswith('switch_'):
                return 'SWITCH'
            if node.startswith('internet'):
                return 'BACKHAUL'

    def get_record(self, node):
        if isinstance(node, Node):
            return {
                'id': self.get_id(node),
                'name': node.name,
                'type': self.get_node_type(node),
                'values': self.get_values(node)
            }
        if isinstance(node, Link):
            return {
                'id': self.get_id(node),
                'name': str(node.tags['name']),
                'type': self.get_node_type(node),
                'values': self.get_values(node)
            }

        if isinstance(node, str):
            if node.startswith('switch_'):
                return {
                    'id': self.get_id(node),
                    'name': node,
                    'type': self.get_node_type(node),
                    'values': self.get_values(node)
                }
            if node.startswith('internet'):
                return {
                    'id': self.get_id(node),
                    'name': node,
                    'type': self.get_node_type(node),
                    'values': self.get_values(node)
                }

        raise ValueError('Unknown node type %s' % node)

    def to_dict(self, topology: Topology):
        nodes = list()
        edges = list()

        for node in topology.get_all_nodes():
            nodes.append(self.get_record(node))

        for edge in topology.edges:
            edges.append({
                'from': self.get_id(edge.source),
                'to': self.get_id(edge.target),
                'directed': edge.directed
            })

        return {'nodes': nodes, 'links': edges}
