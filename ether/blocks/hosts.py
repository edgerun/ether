from typing import Callable

from ether.cell import Host
from ether.core import Node

Configurator = Callable[[Host], None]


def node_name(the_name: str) -> Configurator:
    def cfg(host: Host):
        node: Node = host.nodes[0]
        node.name = the_name

    return cfg


def as_host(node, *configurators: [Configurator]) -> Host:
    host = Host(node)

    for cfg in configurators:
        cfg(host)

    return host


def create_host(*configurators: [Configurator]):
    node = Node('')

    return as_host(node, *configurators)


def main():

    def set_hostname_foo(host):
        host.node.name = 'foo'

    def set_linkname(host):
        host.link.tags['name'] = 'link_%s' % host.node.name
        host.link.tags['hostname'] = host.node.name

    h = create_host(
        set_hostname_foo,
        set_linkname
    )

    print(h)


if __name__ == '__main__':
    main()
