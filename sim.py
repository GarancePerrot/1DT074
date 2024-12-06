from enum import Enum
from dataclasses import dataclass

import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.flow_monitor


class TCPVersion(Enum):
    NewReno     = "TcpNewReno"
    Reno        = "TcpReno"
    LinuxReno   = "TcpLinuxReno"
    WestWood    = "TcpWestwood"
    Vegas       = "TcpVegas"


@dataclass
class NetworkParams:
    latency_ms: float   = 1.
    rate: int           = 500000
    on_off_rate: int    = 300000
    error_rate: float   = 0.0


class Model:
    """
    > To run the basic function of the model:
        '''
        NETPARAMS = NetworkParams(latency_ms=10, error_rate=0.1)

        mymodel = Model(NETPARAMS, tcp_version=TCPVersion.LinuxReno)
        mymodel.add_application(4, 1, "n1n6", 1, 20, "TCP", 8080)
        mymodel.add_error("n1n6)
        mymodel.enable_PCAP(f"results/exp1.1-{TCPVersion.LinuxReno.name}-n5n7", "n5n7")
        mymodel.start()
        '''
    > The topology of the Network is fixed and all nodes are DISABLED by default.
    > Use the model.add_application function to enable certain nodes. They can be either TCP or
      UDP class.
    > The global TCP version is configured using the TCPVersion enum class, see example on top.
    > Error on a specific link can be introduced using the add_error function.
    > All links can be accessed by typing n#1n#2, where #1 and #2 are the nodes the link
      connected with. For instance, n1n6. #1 will always be the number smaller than #2.
    """
    def __init__(
            self, netparams = NetworkParams(), tcp_version: TCPVersion = TCPVersion.LinuxReno, verbose: bool = False
        ):
        self.netparams = netparams
        ns.core.RngSeedManager.SetSeed(42)
        if verbose:
            ns.core.LogComponentEnable(tcp_version.value, map_tcp_verbose(tcp_version))

        self.nodes = ns.network.NodeContainer()
        self.nodes.Create(8)

        self.channels = {
            "n0n5": self.create_channel(0, 5, self.nodes),
            "n1n6": self.create_channel(1, 6, self.nodes),
            "n2n6": self.create_channel(2, 6, self.nodes),
            "n3n7": self.create_channel(3, 7, self.nodes),
            "n4n7": self.create_channel(4, 7, self.nodes),
            "n5n6": self.create_channel(5, 6, self.nodes),
            "n5n7": self.create_channel(5, 7, self.nodes),
            "n6n7": self.create_channel(6, 7, self.nodes),
            }

        self.pointToPoint = ns.point_to_point.PointToPointHelper()
        self.pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
        self.pointToPoint.SetDeviceAttribute("DataRate",
                                    ns.network.DataRateValue(ns.network.DataRate(int(netparams.rate))))
        self.pointToPoint.SetChannelAttribute("Delay",
                                    ns.core.TimeValue(ns.core.MilliSeconds(int(netparams.latency_ms))))

        self.p2p_links = {name: self.pointToPoint.Install(channel)
                    for name, channel in self.channels.items()}
        
        ns.core.Config.SetDefault("ns3::TcpSocket::SegmentSize", ns.core.UintegerValue(1448))
        ns.core.Config.SetDefault("ns3::TcpL4Protocol::SocketType",
                                  ns.core.StringValue(f"ns3::{tcp_version.value}"))

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
            self.error_model.SetAttribute("ErrorUnit", ns.core.StringValue("ERROR_UNIT_PACKET"))
            self.error_model.SetAttribute("ErrorRate", ns.core.DoubleValue(netparams.error_rate))


    def add_error(self, p2p_link: str):
        if self.netparams.error_rate <= 0:
            raise ValueError(
                f"The error rate {self.netparams.error_rate} should be larger than 0 to introduce error.")
        self.p2p_links[p2p_link].Get(1).SetReceiveErrorModel(self.error_model)


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

    def create_channel(self, a: int, b: int, nodes):
        channel = ns.network.NodeContainer()
        channel.Add(nodes.Get(a))
        channel.Add(nodes.Get(b))
        return channel

NETPARAMS = NetworkParams(latency_ms=10, error_rate=0.0)


def exp_control(tcp_type: TCPVersion):
    print("=====Control Experiment====")
    nodes = [2, 3, 4, 0]
    for node in nodes:
        mymodel = Model(NETPARAMS, tcp_version=tcp_type)
        mymodel.add_application(4, 1, "n1n6", 1, 20, "TCP", 8080)
        mymodel.enable_PCAP(f"results/exp_control-{tcp_type.name}-node-{node}-n1n6", "n1n6")
        mymodel.enable_PCAP(f"results/exp_control-{tcp_type.name}-node-{node}-n6n7", "n6n7")
        mymodel.start()


def exp1(tcp_type: TCPVersion):
    print("====Experiment 1====")
    mymodel = Model(NETPARAMS, tcp_version=tcp_type)
    mymodel.add_application(4, 1, "n1n6", 1, 20, "TCP", 8080)
    mymodel.add_application(3, 1, "n1n6", 1, 20, "TCP", 8081)
    mymodel.enable_PCAP(f"results/exp1.1-{tcp_type.name}-n1n6", "n1n6")
    mymodel.enable_PCAP(f"results/exp1.1-{tcp_type.name}-n5n7", "n5n7")
    mymodel.enable_PCAP(f"results/exp1.1-{tcp_type.name}-n6n7", "n6n7")
    mymodel.start()


def exp2(tcp_type: TCPVersion):
    print("====Experiment 2=====")
    mymodel = Model(NETPARAMS, tcp_version=tcp_type)
    mymodel.add_application(4, 1, "n1n6", 1, 20, "TCP", 8080)
    mymodel.add_application(3, 1, "n1n6", 1, 20, "TCP", 8081)
    mymodel.add_application(0, 1, "n1n6", 1, 20, "TCP", 8082)
    mymodel.enable_PCAP(f"results/exp1.2-{tcp_type.name}-n1n6", "n1n6")
    mymodel.enable_PCAP(f"results/exp1.2-{tcp_type.name}-n5n7", "n5n7")
    mymodel.enable_PCAP(f"results/exp1.2-{tcp_type.name}-n5n6", "n5n6")
    mymodel.enable_PCAP(f"results/exp1.2-{tcp_type.name}-n6n7", "n6n7")
    mymodel.start() 


def exp3(tcp_type: TCPVersion):
    print("====Experiment 3====")
    mymodel = Model(NETPARAMS, tcp_version=tcp_type)
    mymodel.add_application(4, 1, "n1n6", 1, 20, "TCP", 8080)
    mymodel.add_application(3, 1, "n1n6", 1, 20, "TCP", 8081)
    mymodel.add_application(0, 1, "n1n6", 1, 20, "TCP", 8082)
    mymodel.add_application(2, 1, "n1n6", 1, 20, "TCP", 8083)
    mymodel.enable_PCAP(f"results/exp1.3-{tcp_type.name}-n1n6", "n1n6")
    mymodel.enable_PCAP(f"results/exp1.3-{tcp_type.name}-n5n7", "n5n7")
    mymodel.enable_PCAP(f"results/exp1.3-{tcp_type.name}-n5n6", "n5n6")
    mymodel.enable_PCAP(f"results/exp1.3-{tcp_type.name}-n6n7", "n6n7")
    mymodel.start() 
    
    
    
def exp_retransmissions(tcp_type: TCPVersion):
    print("=====Retransmission Experiment====")
    mymodel = Model(NETPARAMS, tcp_version=tcp_type)
    mymodel.add_application(4, 1, "n1n6", 1, 20, "TCP", 8080)
    mymodel.add_application(0, 1, "n1n6", 1, 20, "TCP", 8081)
    mymodel.add_application(3, 2, "n2n6", 10, 20, "UDP", 8082)
    mymodel.enable_PCAP(f"results/exp_retransmissions-{tcp_type.name}-n1n6", "n1n6")
    mymodel.enable_PCAP(f"results/exp_retransmissions-{tcp_type.name}-n6n7", "n6n7")
    mymodel.enable_PCAP(f"results/exp_retransmissions-{tcp_type.name}-n5n6", "n5n6")
    mymodel.start()


def main():
    # for tcp_ver in [TCPVersion.WestWood,]:
    for tcp_ver in [TCPVersion.LinuxReno, TCPVersion.WestWood, TCPVersion.Vegas]:
    #for tcp_ver in [TCPVersion.LinuxReno, TCPVersion.Cubic, TCPVersion.Bic ]: #family 1
    #for tcp_ver in [TCPVersion.Westwood, TCPVersion.Highspeed, TCPVersion.Hybla, TCPVersion.Veno, TCPVersion.Illinois,TCPVersion.Ledbat , TCPVersion.Scalable]: #family 2
    #for tcp_ver in [TCPVersion.Vegas, TCPVersion.Dctcp, TCPVersion.Bbr ]: #family 3
        print(tcp_ver.name)
        exp_control(tcp_ver)
        exp1(tcp_ver)
        exp2(tcp_ver)
        exp3(tcp_ver)
        exp_retransmissions(tcp_ver)


if __name__ == "__main__":
    main()
