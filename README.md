ether: Edge Topology Synthesizer
================================

[![PyPI Version](https://badge.fury.io/py/edgerun-ether.svg)](https://badge.fury.io/py/edgerun-ether)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

<img src="https://github.com/edgerun/ether/raw/master/logo/logo.png" height="100">

*Ether* is a Python tool to generate plausible edge infrastructure configurations.
It arose from the need to evaluate edge computing systems in different infrastructure scenarios where no appropriate
testbeds are available.


Use cases
---------

Some of the uses cases for *ether* include

* Evaluating resource allocation strategies
* Creating topologies for network simulations
* Infrastructure capacity planing

Examples
--------

### Code example

Creating a topology for an urban sensing scenario, similar to that of the
[Array of Things](http://arrayofthings.github.io/node-locations.html) could look like this:

```python
topology = Topology()

aot_node = IoTComputeBox(nodes=[nodes.rpi3, nodes.rpi3])
neighborhood = lambda size: SharedLinkCell(
    nodes=[
        [aot_node] * size,
        IoTComputeBox([nodes.nuc] + ([nodes.tx2] * size * 2))
    ],
    shared_bandwidth=500,
    backhaul=MobileConnection('internet_chix'))
city = GeoCell(
    5, nodes=[neighborhood], density=lognorm((0.82, 2.02)))
cloudlet = Cloudlet(
    5, 2, backhaul=FiberToExchange('internet_chix'))

topology.add(city)
topology.add(cloudlet)
```

We have pre-parameterized versions of these scenarios that can be readily used:

```python
topology = Topology()
UrbanSensingTopology().materialize(topology)
```

### Example usage

The following example shows how we used generated topology to evaluate the effect on uplink usage of different resource
allocation strategies in an edge computing platform.
The node-link diagram of the topology is augmented with a
[topographic attribute map](https://hydra.cgv.tugraz.at/preiner/papers/psksm20-tam.pdf) ([rpreiner/tam](https://github.com/rpreiner/tam)) that the data exchange in
log bytes.
The left part of the figure shows the baseline resource allocation strategy, the right part shows our improved strategy
that takes data-locality into account.
The visualization helps to see how much the backhaul network is relieved, and how data transfer is isolated into edge
networks.  

<a href="https://edgerun.io/static/ether/iiot-scenario-comparing-scheduling-strategies.jpg" target="_blank">
  <img src="https://edgerun.io/static/ether/iiot-scenario-comparing-scheduling-strategies.jpg" alt="Comparing  a sub-community in a generated IIoT-scenario topology" width="100%"/>
</a>

Related publications
--------------------

1. Rausch, T., Lachner, C., Frangoudis, P. A., Raith, P., & Dustdar, S. (2020).
   Synthesizing Plausible Infrastructure Configurations for Evaluating Edge Computing Systems.
   In *3rd USENIX Workshop on Hot Topics in Edge Computing (HotEdge 20)*. USENIX Association.
   [[Preprint](https://dsg.tuwien.ac.at/team/trausch/pub/hotedge20-synthesizing.pdf)]
