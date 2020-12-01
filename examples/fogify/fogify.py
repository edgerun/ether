import matplotlib.pyplot as plt
import yaml

from ether.converter.fogify import topology_to_fogify
from ether.scenarios.industrialiot import IndustrialIoTScenario
from ether.topology import Topology
from ether.vis import draw_basic

if __name__ == '__main__':
    t = Topology()

    scen = IndustrialIoTScenario(1)
    scen.materialize(t)

    fogify_model = topology_to_fogify(t)

    print(yaml.dump({'x-fogify': {
        'nodes': fogify_model.nodes,
        'networks': fogify_model.networks,
        'topology': fogify_model.topology,
    }}))

    draw_basic(t)
    fig = plt.gcf()
    fig.set_size_inches(18.5, 10.5)
    plt.show()  # display
