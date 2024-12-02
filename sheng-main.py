from model import Model
import os

def main():
    mymodel = Model()
    mymodel.add_application(4, 1, "n1n6", 1, 60, "TCP")
    mymodel.add_application(3, 2, "n2n6", 30, 60, "UDP")
    mymodel.enable_PCAP("abc", "n1n6")
    mymodel.start()

if __name__ == "__main__":
    main()
