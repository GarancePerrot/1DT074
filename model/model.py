import sys
import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.flow_monitor

from dataclasses import dataclass

@dataclass
class NetworkParams:
    latency = 1
    rate = 500000
    on_off_rate = 300000


def create_channel(a: int, b: int, nodes):
    channel = ns.network.NodeContainer()
    channel.Add(nodes.Get(a))
    channel.Add(nodes.Get(b))
    return channel

def start(netparams = NetworkParams()):
    ns.core.RngSeedManager.SetSeed(42)
    ns.core.LogComponentEnable("TcpLinuxReno", ns.core.LOG_LEVEL_LOGIC)

    nodes = ns.network.NodeContainer()
    nodes.Create(8)

    channels = {"n1n6": create_channel(1, 6, nodes),
                "n1n6": create_channel(2, 6, nodes),
                "n3n7": create_channel(3, 7, nodes),
                "n4n7": create_channel(4, 7, nodes),
                "n0n5": create_channel(0, 5, nodes),
                "n5n6": create_channel(5, 6, nodes),
                "n5n7": create_channel(5, 7, nodes),
                "n6n7": create_channel(6, 7, nodes),
                }

    pointToPoint = ns.point_to_point.PointToPointHelper()
    pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
    pointToPoint.SetDeviceAttribute("DataRate",
                                ns.network.DataRateValue(ns.network.DataRate(int(netparams.rate))))
    pointToPoint.SetChannelAttribute("Delay",
                                ns.core.TimeValue(ns.core.MilliSeconds(int(netparams.latency))))

    p2p_links = {name: pointToPoint.Install(channel) for name, channel in channels.items()}