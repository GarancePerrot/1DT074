from model import Model, NetworkParams, TCPVersion
import os


def main():
    tcp_type = TCPVersion.WestWood
    end_time = 60

    mymodel = Model(NetworkParams(error_rate=0.1), tcp_type=tcp_type)
    mymodel.add_application(4, 1, "n1n6", 1, end_time, "TCP", 8080)
    mymodel.add_application(0, 1, "n1n6", 5, end_time, "TCP", 8081)
    # mymodel.add_application(3, 2, "n2n6", 30, 60, "UDP")
    mymodel.add_error("n1n6")
    mymodel.enable_PCAP(f"results/{tcp_type.name}-n1n6", "n1n6")
    mymodel.enable_PCAP(f"results/{tcp_type.name}-n2n6", "n2n6")
    #mymodel.enable_PCAP("n5n7", "n5n7")
    #mymodel.enable_PCAP("n5n6", "n5n6")
    mymodel.start()

if __name__ == "__main__":
    main()
