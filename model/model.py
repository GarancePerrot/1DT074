from email.policy import default
import sys
import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.flow_monitor

from dataclasses import dataclass
from .corrupt_errror import CorruptPacketErrorModel

@dataclass
class NetworkParams:
    latency: float      = 1.
    rate: int           = 500000
    on_off_rate: int    = 300000
    error_rate: float   = 0.0


def create_channel(a: int, b: int, nodes):
    channel = ns.network.NodeContainer()
    channel.Add(nodes.Get(a))
    channel.Add(nodes.Get(b))
    return channel


class Model:
    def __init__(
            self, netparams = NetworkParams(), tcp_type = "ns3::TcpLinuxReno", verbose: bool = False
        ):
        self.netparams = netparams
        ns.core.RngSeedManager.SetSeed(42)
        if verbose:
            ns.core.LogComponentEnable("TcpLinuxReno", ns.core.LOG_LEVEL_LOGIC)
            #ns.core.LogComponentEnable("UdpEchoClientApplication", ns.core.LOG_LEVEL_INFO)
            #ns.core.LogComponentEnable("UdpEchoServerApplication", ns.core.LOG_LEVEL_INFO)
            #ns.core.LogComponentEnable("PointToPointNetDevice", ns.core.LOG_LEVEL_ALL)
            #ns.core.LogComponentEnable("DropTailQueue", ns.core.LOG_LEVEL_LOGIC)
            #ns.core.LogComponentEnable("OnOffApplication", ns.core.LOG_LEVEL_INFO)
            #ns.core.LogComponentEnable("TcpWestwood", ns.core.LOG_LEVEL_LOGIC)
            #ns.core.LogComponentEnable("TcpTahoe", ns.core.LOG_LEVEL_LOGIC)

        self.nodes = ns.network.NodeContainer()
        self.nodes.Create(8)

        self.channels = {
            "n1n6": create_channel(1, 6, self.nodes),
            "n2n6": create_channel(2, 6, self.nodes),
            "n3n7": create_channel(3, 7, self.nodes),
            "n4n7": create_channel(4, 7, self.nodes),
            "n0n5": create_channel(0, 5, self.nodes),
            "n5n6": create_channel(5, 6, self.nodes),
            "n5n7": create_channel(5, 7, self.nodes),
            "n6n7": create_channel(6, 7, self.nodes),
            }

        self.pointToPoint = ns.point_to_point.PointToPointHelper()
        self.pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
        self.pointToPoint.SetDeviceAttribute("DataRate",
                                    ns.network.DataRateValue(ns.network.DataRate(int(netparams.rate))))
        self.pointToPoint.SetChannelAttribute("Delay",
                                    ns.core.TimeValue(ns.core.MilliSeconds(int(netparams.latency))))

        self.p2p_links = {name: self.pointToPoint.Install(channel)
                    for name, channel in self.channels.items()}
        
        ns.core.Config.SetDefault("ns3::TcpSocket::SegmentSize", ns.core.UintegerValue(1448))

        ns.core.Config.SetDefault("ns3::TcpL4Protocol::SocketType",
                            ns.core.StringValue(tcp_type))
        #tcp_type : ns3::TcpNewReno, ns3::TcpTahoe, ns3::TcpReno, ns3::TcpLinuxReno, ns3::TcpWestwood etc.
        
        # Different TCP version may have different protocol type,
        # may cause error when uses a different socket type.

        # Some examples of attributes for some of the TCP versions
        #ns.core.Config.SetDefault("ns3::TcpLinuxReno::ReTxThreshold", ns.core.UintegerValue(4))
        #ns.core.Config.SetDefault("ns3::TcpWestwood::ProtocolType",
        #                         ns.core.StringValue("WestwoodPlus"))
        

        stack = ns.internet.InternetStackHelper()
        stack.Install(self.nodes)

        address = ns.internet.Ipv4AddressHelper()
        self.ip_address = {}
        for i, (name, p2p_link) in enumerate(self.p2p_links.items()):
            address.SetBase(ns.network.Ipv4Address(f"10.1.{i+1}.0"),
                            ns.network.Ipv4Mask("255.255.255.0"))
            self.ip_address[name] = address.Assign(p2p_link)

        ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

        if netparams.error_rate > 0:
            self.error_model = ns.network.RateErrorModel()
            self.error_model.SetAttribute("ErrorRate", ns.core.DoubleValue(self.netparams.error_rate))


    def add_error(self, p2p_link: str):
        if self.netparams.error_rate <= 0:
            raise ValueError(
                f"The error rate {self.netparams.error_rate} should be larger than 0 to introduce error.")
        self.p2p_links[p2p_link].Get(0).SetAttribute("ReceiveErrorModel",
                                                     ns.core.PointerValue(self.error_model))


    def add_application(self, src_node: int, dst_node: int, dst_addr: str, start_time, stop_time, type: str, port: int):
        setup_application = {"TCP": self.SetupTcpConnection,
                            "UDP": self.SetupUdpConnection}
        setup_application[type](self.nodes.Get(src_node), self.nodes.Get(dst_node), self.ip_address[dst_addr].GetAddress(0), ns.core.Seconds(start_time), ns.core.Seconds(stop_time), port)


    def SetupTcpConnection(self, srcNode, dstNode, dstAddr, startTime, stopTime, port: int):
        # Create a TCP sink at dstNode
        packet_sink_helper = ns.applications.PacketSinkHelper("ns3::TcpSocketFactory",
                                ns.network.InetSocketAddress(ns.network.Ipv4Address.GetAny(),
                                                            port))
        sink_apps = packet_sink_helper.Install(dstNode)
        sink_apps.Start(ns.core.Seconds(1.0))
        sink_apps.Stop(ns.core.Seconds(60.0))

        # Create TCP connection from srcNode to dstNode
        on_off_tcp_helper = ns.applications.OnOffHelper("ns3::TcpSocketFactory",
                                ns.network.Address(ns.network.InetSocketAddress(dstAddr, port)))
        on_off_tcp_helper.SetAttribute("DataRate",
                            ns.network.DataRateValue(ns.network.DataRate(int(self.netparams.on_off_rate))))
        on_off_tcp_helper.SetAttribute("PacketSize", ns.core.UintegerValue(1500))
        on_off_tcp_helper.SetAttribute("OnTime",
                            ns.core.StringValue("ns3::ConstantRandomVariable[Constant=2]"))
        on_off_tcp_helper.SetAttribute("OffTime",
                                ns.core.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
        #                      ns.core.StringValue("ns3::UniformRandomVariable[Min=1,Max=2]"))
        #                      ns.core.StringValue("ns3::ExponentialRandomVariable[Mean=2]"))

        # Install the client on node srcNode
        client_apps = on_off_tcp_helper.Install(srcNode)
        client_apps.Start(startTime)
        client_apps.Stop(stopTime)


    def SetupUdpConnection(self, srcNode, dstNode, dstAddr, startTime, stopTime, port: int):
        # Create a UDP sink at dstNode
        echoServer = ns.applications.UdpEchoServerHelper(9)
        serverApps = echoServer.Install(dstNode)
        serverApps.Start(ns.core.Seconds(1.0))
        serverApps.Stop(ns.core.Seconds(60.0))

        # Create UDP client at srcNode
        # Unlike TCP, no need to establish a connection before data transmission
        # Create the client application and connect it to node 1 and port 9. Configure number
        # of packets, packet sizes, inter-arrival interval.
        echoClient = ns.applications.UdpEchoClientHelper(dstAddr, port)
        echoClient.SetAttribute("MaxPackets", ns.core.UintegerValue(1000))
        echoClient.SetAttribute("Interval",
                                ns.core.TimeValue(ns.core.Seconds(0.01)))
        echoClient.SetAttribute("PacketSize", ns.core.UintegerValue(1024))

        # Install the client on srcNode
        clientApps = echoClient.Install(srcNode)
        clientApps.Start(startTime)
        clientApps.Stop(stopTime)

    def enable_PCAP(self, title: str, link: str):
        self.pointToPoint.EnablePcap(title, self.p2p_links[link].Get(0), True)


    def start(self):
        flowmon_helper = ns.flow_monitor.FlowMonitorHelper()
        monitor = flowmon_helper.InstallAll()
        ns.core.Simulator.Stop(ns.core.Seconds(60.0))
        ns.core.Simulator.Run()

        monitor.CheckForLostPackets()

        classifier = flowmon_helper.GetClassifier()

        for flow_id, flow_stats in monitor.GetFlowStats():
            t = classifier.FindFlow(flow_id)
            proto = {6: 'TCP', 17: 'UDP'} [t.protocol]
            print ("FlowID: %i (%s %s/%s --> %s/%i)" %
                    (flow_id, proto, t.sourceAddress, t.sourcePort, t.destinationAddress, t.destinationPort))

            print ("  Tx Bytes: %i" % flow_stats.txBytes)
            print ("  Rx Bytes: %i" % flow_stats.rxBytes)
            print ("  Lost Pkt: %i" % flow_stats.lostPackets)
            print ("  Flow active: %fs - %fs" % (flow_stats.timeFirstTxPacket.GetSeconds(),
                                                flow_stats.timeLastRxPacket.GetSeconds()))
            print ("  Throughput: %f Mbps" % (flow_stats.rxBytes *
                                                8.0 /
                                                (flow_stats.timeLastRxPacket.GetSeconds()
                                                - flow_stats.timeFirstTxPacket.GetSeconds())/
                                                1024/
                                                1024))
        
        ns.core.Simulator.Destroy()
