from model import Model
import os

def main():
    mymodel = Model(tcp_type = "TcpBbr") 
    #tcp_type : TcpLinuxReno, TcpWestwood, TcpCubic, TcpHybla, TcpHighSpeed, TcpVegas, TcpScalable, TcpVeno
    #           TcpBic, TcpIllinois, TcpLedbat, TcpDctcp, TcpBbr
    
    # "Logging component not found" for: TcpTahoe, TcpReno, TcpNewReno, TcpYeAH, TcpHTCP, TcpLP, 

    # add_application(src_node: int, dst_node: int, dst_addr: str, start_time, stop_time, type: str)
    mymodel.add_application(4, 1, "n1n6", 1, 60, "TCP")  
    mymodel.add_application(3, 2, "n2n6", 30, 60, "UDP") 
    mymodel.enable_PCAP("abc", "n1n6") #pcap file for node 1 
    
    mymodel.start()

if __name__ == "__main__":
    main()
