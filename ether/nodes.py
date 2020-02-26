import itertools
from collections import defaultdict
from typing import Dict

from ether.core import Node, Capacity
from ether.util import parse_size_string

counters = defaultdict(lambda: itertools.count(0, 1))


def create_vm_node(name=None) -> Node:
    name = name if name is not None else 'cloudvm_%d' % next(counters['cloudvm'])

    return create_node(name=name,
                       cpus=4, arch='x86', mem='8167784Ki',
                       labels={
                           'ether.taufaas.io/type': 'vm',
                           'ether.taufaas.io/model': 'vm'
                       })


def create_server_node(name=None) -> Node:
    name = name if name is not None else 'server_%d' % next(counters['server'])

    return create_node(name=name,
                       cpus=88, arch='x86', mem='188G',
                       labels={
                           'ether.taufaas.io/type': 'server',
                           'ether.taufaas.io/model': 'server'
                       })


def create_rpi3_node(name=None) -> Node:
    name = name if name is not None else 'rpi3_%d' % next(counters['rpi3'])

    return create_node(name=name,
                       cpus=4, arch='arm32', mem='999036Ki',
                       labels={
                           'ether.taufaas.io/type': 'sbc',
                           'ether.taufaas.io/model': 'rpi3b+'
                       })


def create_nuc_node(name=None) -> Node:
    name = name if name is not None else 'nuc_%d' % next(counters['nuc'])

    return create_node(name=name,
                       cpus=4, arch='x86', mem='16Gi',
                       labels={
                           'ether.taufaas.io/type': 'sffc',
                           'ether.taufaas.io/model': 'nuci5'
                       })


def create_tx2_node(name=None) -> Node:
    name = name if name is not None else 'tx2_%d' % next(counters['tx2'])

    return create_node(name=name,
                       cpus=4, arch='aarch64', mem='8047252Ki',
                       labels={
                           'ether.taufaas.io/type': 'embai',
                           'ether.taufaas.io/model': 'nvidia_jetson_tx2',
                           'ether.taufaas.io/capabilities/cuda': '10',
                           'ether.taufaas.io/capabilities/gpu': 'pascal',
                       })


def create_node(name: str, cpus: int, mem: str, arch: str, labels=Dict[str, str]) -> Node:
    capacity = Capacity(cpu_millis=cpus * 1000, memory=parse_size_string(mem))
    return Node(name, capacity=capacity, arch=arch, labels=labels)
