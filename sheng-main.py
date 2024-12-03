from model import Model, NetworkParams
import os


def main():
    mymodel = Model(NetworkParams(error_rate=0.01))
    mymodel.add_application(4, 1, "n1n6", 1, 60, "TCP", 8080)
    mymodel.add_application(0, 1, "n1n6", 5, 60, "TCP", 8081)
    # mymodel.add_application(3, 2, "n2n6", 30, 60, "UDP")
    mymodel.add_error("n5n6")
    mymodel.enable_PCAP("n1n6", "n1n6")
    mymodel.enable_PCAP("n5n7", "n5n7")
    mymodel.enable_PCAP("n5n6", "n5n6")
    mymodel.start()

if __name__ == "__main__":
    main()
