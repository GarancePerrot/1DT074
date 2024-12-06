from model import Model, NetworkParams, TCPVersion


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


def main():
    # for tcp_ver in [TCPVersion.WestWood,]:
    for tcp_ver in [TCPVersion.LinuxReno, TCPVersion.WestWood, TCPVersion.Vegas]:
        print(tcp_ver.name)
        exp_control(tcp_ver)
        exp1(tcp_ver)
        exp2(tcp_ver)
        exp3(tcp_ver)


if __name__ == "__main__":
    main()
