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
        #exp_retransmissions(tcp_ver)

    

def lab_2():
    import sys
    import ns.applications
    import ns.core
    import ns.internet
    import ns.network
    import ns.point_to_point
    import ns.flow_monitor

    #######################################################################################
    # SEEDING THE RNG
    #
    # Enable this line to have random number being generated between runs.

    #ns.core.RngSeedManager.SetSeed(int(time.time() * 1000 % (2**31-1)))


    #######################################################################################
    # LOGGING
    #
    # Here you may enable extra output logging. It will be printed to the stdout.
    # This is mostly useful for debugging and investigating what is going on in the
    # the simulator. You may use this output to generate your results as well, but
    # you would have to write extra scripts for filtering and parsing the output.
    # FlowMonitor may be a better choice of getting the information you want.


    #ns.core.LogComponentEnable("UdpEchoClientApplication", ns.core.LOG_LEVEL_INFO)
    #ns.core.LogComponentEnable("UdpEchoServerApplication", ns.core.LOG_LEVEL_INFO)
    #ns.core.LogComponentEnable("PointToPointNetDevice", ns.core.LOG_LEVEL_ALL)
    #ns.core.LogComponentEnable("DropTailQueue", ns.core.LOG_LEVEL_LOGIC)
    #ns.core.LogComponentEnable("OnOffApplication", ns.core.LOG_LEVEL_INFO)
    #ns.core.LogComponentEnable("TcpWestwood", ns.core.LOG_LEVEL_LOGIC)
    #ns.core.LogComponentEnable("TcpTahoe", ns.core.LOG_LEVEL_LOGIC)
    ns.core.LogComponentEnable("TcpLinuxReno", ns.core.LOG_LEVEL_LOGIC)


    # in progress : how to get updates to the congestion window size (cwnd)  ??




    #######################################################################################
    # COMMAND LINE PARSING
    #
    # Parse the command line arguments. Some simulation parameters can be set from the
    # command line instead of in the script. You may start the simulation by:
    #
    # /it/kurs/datakom2/lab1/ns3-run sim-udp.py --latency=10
    #
    # You can add your own parameters and there default values below. To access the values
    # in the simulator, you use the variable cmd.something.

    cmd = ns.core.CommandLine()

    # Default values
    cmd.latency = 1
    cmd.rate = 500000
    cmd.on_off_rate = 300000
    cmd.AddValue ("rate", "P2P data rate in bps")
    cmd.AddValue ("latency", "P2P link Latency in miliseconds")
    cmd.AddValue ("on_off_rate", "OnOffApplication data sending rate")
    cmd.Parse(sys.argv)


    #######################################################################################
    # CREATE NODES

    nodes = ns.network.NodeContainer()
    nodes.Create(6)


    #######################################################################################
    # CONNECT NODES WITH POINT-TO-POINT CHANNEL
    #
    # We use a helper class to create the point-to-point channels. It helps us with creating
    # the necessary objects on the two connected nodes as well, including creating the
    # NetDevices (of type PointToPointNetDevice), etc.

    # Set the default queue length to 5 packets (used by NetDevices)
    # The first line is for older ns3 versions and the second for new versions.
    #ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(5))
    #ns.core.Config.SetDefault("ns3::Queue::MaxPackets", ns.core.UintegerValue(5))


    # To connect the point-to-point channels, we need to define NodeContainers for all the
    # point-to-point channels.
    n0n4 = ns.network.NodeContainer()
    n0n4.Add(nodes.Get(0))
    n0n4.Add(nodes.Get(4))

    n1n4 = ns.network.NodeContainer()
    n1n4.Add(nodes.Get(1))
    n1n4.Add(nodes.Get(4))

    n2n5 = ns.network.NodeContainer()
    n2n5.Add(nodes.Get(2))
    n2n5.Add(nodes.Get(5))

    n3n5 = ns.network.NodeContainer()
    n3n5.Add(nodes.Get(3))
    n3n5.Add(nodes.Get(5))

    n4n5 = ns.network.NodeContainer()
    n4n5.Add(nodes.Get(4))
    n4n5.Add(nodes.Get(5))

    # create point-to-point helper with common attributes
    pointToPoint = ns.point_to_point.PointToPointHelper()
    pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
    pointToPoint.SetDeviceAttribute("DataRate",
                                ns.network.DataRateValue(ns.network.DataRate(int(cmd.rate))))
    pointToPoint.SetChannelAttribute("Delay",
                                ns.core.TimeValue(ns.core.MilliSeconds(int(cmd.latency))))

    # install network devices for all nodes based on point-to-point links
    d0d4 = pointToPoint.Install(n0n4)
    d1d4 = pointToPoint.Install(n1n4)
    d2d5 = pointToPoint.Install(n2n5)
    d3d5 = pointToPoint.Install(n3n5)
    d4d5 = pointToPoint.Install(n4n5)

    # Here we can introduce an error model on the bottle-neck link (from node 4 to 5)
    #em = ns.network.RateErrorModel()
    #em.SetAttribute("ErrorUnit", ns.core.StringValue("ERROR_UNIT_PACKET"))
    #em.SetAttribute("ErrorRate", ns.core.DoubleValue(0.02))
    #d4d5.Get(1).SetReceiveErrorModel(em)


    #######################################################################################
    # CONFIGURE TCP
    #
    # Choose a TCP version and set some attributes.

    # Set a TCP segment size (this should be inline with the channel MTU)
    ns.core.Config.SetDefault("ns3::TcpSocket::SegmentSize", ns.core.UintegerValue(1448))

    # If you want, you may set a default TCP version here. It will affect all TCP
    # connections created in the simulator. If you want to simulate different TCP versions
    # at the same time, see below for how to do that.
    ns.core.Config.SetDefault("ns3::TcpL4Protocol::SocketType",
                        #   ns.core.StringValue("ns3::TcpNewReno"))
                            #  ns.core.StringValue("ns3::TcpTahoe"))
                            #  ns.core.StringValue("ns3::TcpReno"))
                            ns.core.StringValue("ns3::TcpLinuxReno"))
                            #  ns.core.StringValue("ns3::TcpWestwood"))

    # Some examples of attributes for some of the TCP versions.
    #ns.core.Config.SetDefault("ns3::TcpLinuxReno::ReTxThreshold", ns.core.UintegerValue(4))
    #ns.core.Config.SetDefault("ns3::TcpWestwood::ProtocolType",
    #                         ns.core.StringValue("WestwoodPlus"))




    #######################################################################################
    # CREATE A PROTOCOL STACK
    #
    # This code creates an IPv4 protocol stack on all our nodes, including ARP, ICMP,
    # pcap tracing, and routing if routing configurations are supplied. All links need
    # different subnet addresses. Finally, we enable static routing, which is automatically
    # setup by an oracle.

    # Install networking stack for nodes
    stack = ns.internet.InternetStackHelper()
    stack.Install(nodes)

    # Here, you may change the TCP version per node. A node can only support on version at
    # a time, but different nodes can run different versions. The versions only affect the
    # sending node. Note that this must called after stack.Install().
    #
    # The code below would tell node 0 to use TCP Tahoe and node 1 to use TCP Westwood.
    #ns.core.Config.Set("/NodeList/0/$ns3::TcpL4Protocol/SocketType",
    #                   ns.core.TypeIdValue(ns.core.TypeId.LookupByName ("ns3::TcpTahoe")))
    #ns.core.Config.Set("/NodeList/1/$ns3::TcpL4Protocol/SocketType",
    #                   ns.core.TypeIdValue(ns.core.TypeId.LookupByName ("ns3::TcpWestwood")))


    # Assign IP addresses for net devices
    address = ns.internet.Ipv4AddressHelper()

    address.SetBase(ns.network.Ipv4Address("10.1.1.0"), ns.network.Ipv4Mask("255.255.255.0"))
    if0if4 = address.Assign(d0d4)

    address.SetBase(ns.network.Ipv4Address("10.1.2.0"), ns.network.Ipv4Mask("255.255.255.0"))
    if1if4 = address.Assign(d1d4)

    address.SetBase(ns.network.Ipv4Address("10.1.3.0"), ns.network.Ipv4Mask("255.255.255.0"))
    if2if5 = address.Assign(d2d5)

    address.SetBase(ns.network.Ipv4Address("10.1.4.0"), ns.network.Ipv4Mask("255.255.255.0"))
    if3if5 = address.Assign(d3d5)

    address.SetBase(ns.network.Ipv4Address("10.1.5.0"), ns.network.Ipv4Mask("255.255.255.0"))
    if4if5 = address.Assign(d4d5)

    # Turn on global static routing so we can actually be routed across the network.
    ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()


    #######################################################################################
    # CREATE TCP APPLICATION AND CONNECTION
    #
    # Create a TCP client at node N0 and a TCP sink at node N2 using an On-Off application.
    # An On-Off application alternates between on and off modes. In on mode, packets are
    # generated according to DataRate, PacketSize. In off mode, no packets are transmitted.

    def SetupTcpConnection(srcNode, dstNode, dstAddr, startTime, stopTime):
        # Create a TCP sink at dstNode
        packet_sink_helper = ns.applications.PacketSinkHelper("ns3::TcpSocketFactory",
                                ns.network.InetSocketAddress(ns.network.Ipv4Address.GetAny(),
                                                            8080))
        sink_apps = packet_sink_helper.Install(dstNode)
        sink_apps.Start(ns.core.Seconds(1.0))
        sink_apps.Stop(ns.core.Seconds(60.0))

        # Create TCP connection from srcNode to dstNode
        on_off_tcp_helper = ns.applications.OnOffHelper("ns3::TcpSocketFactory",
                                ns.network.Address(ns.network.InetSocketAddress(dstAddr, 8080)))
        on_off_tcp_helper.SetAttribute("DataRate",
                            ns.network.DataRateValue(ns.network.DataRate(int(cmd.on_off_rate))))
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
    
    
    
    
    #added: set up UDP communication with node 1 as the packet generator and node 3 as the sink:
    def SetupUdpConnection(srcNode, dstNode, dstAddr, startTime, stopTime):
        # Create a UDP sink at dstNode
        echoServer = ns.applications.UdpEchoServerHelper(9)
        serverApps = echoServer.Install(nodes.Get(1))
        serverApps.Start(ns.core.Seconds(1.0))
        serverApps.Stop(ns.core.Seconds(60.0))

        # Create UDP client at srcNode
        # Unlike TCP, no need to establish a connection before data transmission
        # Create the client application and connect it to node 1 and port 9. Configure number
        # of packets, packet sizes, inter-arrival interval.
        echoClient = ns.applications.UdpEchoClientHelper(dstAddr, 9)
        echoClient.SetAttribute("MaxPackets", ns.core.UintegerValue(1000))
        echoClient.SetAttribute("Interval",
                                ns.core.TimeValue(ns.core.Seconds(0.01)))
        echoClient.SetAttribute("PacketSize", ns.core.UintegerValue(1024))

        # Install the client on srcNode
        clientApps = echoClient.Install(nodes.Get(0))
        clientApps.Start(startTime)
        clientApps.Stop(stopTime)   
        


    SetupTcpConnection(nodes.Get(0), nodes.Get(2), if2if5.GetAddress(0),
                    ns.core.Seconds(1.0), ns.core.Seconds(60.0))
    SetupUdpConnection(nodes.Get(1), nodes.Get(3), if3if5.GetAddress(0),
                    ns.core.Seconds(30.0), ns.core.Seconds(60.0))



    #######################################################################################
    # CREATE A PCAP PACKET TRACE FILE
    #
    # This line creates two trace files based on the pcap file format. It is a packet
    # trace dump in a binary file format. You can use Wireshark to open these files and
    # inspect every transmitted packets. Wireshark can also draw simple graphs based on
    # these files.
    #
    # You will get two files, one for node 0 and one for node 1

    # pointToPoint.EnablePcap("sim-tcp-node0", d0d4.Get(0), True)
    # pointToPoint.EnablePcap("sim-tcp-node1", d1d4.Get(0), True)

    #added: get pcap files for sink nodes, i.e node 2 (TCP) and node 3 (UDP)
    pointToPoint.EnablePcap("sim-tcp-TCPsink", d2d5.Get(0), True)
    pointToPoint.EnablePcap("sim-tcp-UDPsink", d3d5.Get(0), True)

    #######################################################################################
    # FLOW MONITOR
    #
    # Here is a better way of extracting information from the simulation. It is based on
    # a class called FlowMonitor. This piece of code will enable monitoring all the flows
    # created in the simulator. There are four flows in our example, one from the client to
    # server and one from the server to the client for both TCP connections.

    flowmon_helper = ns.flow_monitor.FlowMonitorHelper()
    monitor = flowmon_helper.InstallAll()


    #######################################################################################
    # RUN THE SIMULATION
    #
    # We have to set stop time, otherwise the flowmonitor causes simulation to run forever

    ns.core.Simulator.Stop(ns.core.Seconds(60.0))
    ns.core.Simulator.Run()


    #######################################################################################
    # FLOW MONITOR ANALYSIS
    #
    # Simulation is finished. Let's extract the useful information from the FlowMonitor and
    # print it on the screen.

    # check for lost packets
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


    # This is what we want to do last
    ns.core.Simulator.Destroy()


if __name__ == "__main__":
    main()
    lab_2()
