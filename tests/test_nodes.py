from unittest import TestCase

from ether.blocks.nodes import create_nuc_node, create_rpi3_node


class TestNodes(TestCase):
    def test_create(self):
        node = create_nuc_node('mynucnode')
        self.assertEqual('mynucnode', node.name)
        self.assertEqual('x86', node.arch)
        self.assertEqual(4000, node.capacity.cpu_millis)
        self.assertEqual(17179869184, node.capacity.memory)  # 17179869184 = 16Gi

        node = create_rpi3_node('myrpinode')
        self.assertEqual('myrpinode', node.name)
        self.assertEqual('arm32', node.arch)

    def test_create_counter(self):
        node1 = create_rpi3_node()
        self.assertRegex(node1.name, r'^rpi3_[0-9]+$')

        node2 = create_rpi3_node()
        self.assertRegex(node2.name, r'^rpi3_[0-9]+$')

        i1 = int(node1.name.split('_')[-1])
        i2 = int(node2.name.split('_')[-1])

        self.assertEqual(i1 + 1, i2)
