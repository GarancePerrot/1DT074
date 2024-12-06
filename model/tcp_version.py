from enum import Enum
import ns.core


class TCPVersion(Enum):
    NewReno     = "TcpNewReno"
    Reno        = "TcpReno"
    LinuxReno   = "TcpLinuxReno"
    WestWood    = "TcpWestwood"
    Vegas       = "TcpVegas"
    Cubic       = "TcpCubic"
    Bic         = "TcpBic"
    HighSpeed   =  "TcpHighSpeed"
    Hybla       = "TcpHybla"
    Veno        = "TcpVeno"
    Illinois    = "TcpIllinois"
    Ledbat      = "TcpLedbat"
    Scalable    = "TcpScalable"
    Dctcp       = "TcpDctcp"
    Bbr         = "TcpBbr"
    

def map_tcp_verbose(tcp_version: TCPVersion):
    return ns.core.iLOG_LEVEL_LOGIC