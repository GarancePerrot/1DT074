from enum import Enum


class TCPVersion(Enum):
    NewReno     = "TcpNewReno"
    Tahoe       = "TcpTahoe"
    Reno        = "TcpReno"
    LinuxReno   = "TcpLinuxReno"
    WestWood    = "TcpWestwood"
