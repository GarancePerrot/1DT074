/*
 * Copyright (C) 2022, 2023  Xiaoyue Chen
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "network.h"


void net_init(unsigned short port_self, const char *hostname_other,
              unsigned short port_other) {
  /* TODO:
   * 1. Create a UDP socket.
   * 2. Bind the socket to port_self.
   * 3. Set sock_addr_other to the socket address at hostname_other and
   * port_other. */

// 1. Create a UDP socket.
  sock = socket(AF_INET, SOCK_DGRAM, 0); //UDP socket
  if (sock < 0) {
		perror("\nCannot create socket");
	    return;
	}

// 2. (Prepare sock add structure and) bind the socket to port_self
  struct sockaddr_in sock_addr;
  memset(&sock_addr, '\0', sizeof(sock_addr));
  sock_addr.sin_family = AF_INET; 
  sock_addr.sin_addr.s_addr = INADDR_ANY; // bind to any available IP address
  sock_addr.sin_port = htons(port_self);

  if (bind(sock, (struct sockaddr *)&sock_addr, sizeof(sock_addr)) < 0) {
    perror("\nError: bind failed");
    return;
  }

// 3. Set sock_addr_other to the socket address at hostname_other and port_other.
  memset(&sock_addr_other, '\0' , sizeof(sock_addr_other));
  sock_addr_other.sin_family = AF_INET;
  sock_addr_other.sin_port = htons(port_other);
  sock_addr_other.sin_addr.s_addr = inet_addr(hostname_other); //inet_addr converts the char into a valid ip address

}

void net_fini() { /* TODO: Shutdown the socket. */
  close(sock); 
}

void serialise(unsigned char *buff, const net_packet_t *pkt) {
  // converting the data within the packet into a sequence of bytes that can be transmitted

  /* TODO:
   * Serialise the packet according to the protocol.
   * Note that it must use network endian.*/

  // htons convert data from the host's native byte order to the network byte order before transmission

  *(uint8_t*)buff = htons(pkt->opcode);  // casts buff to a pointer of the type of opcode and copies
  buff += sizeof(uint8_t);  // increments pointer

  *(uint16_t*)buff = htons(pkt->epoch);
  buff += sizeof(uint16_t);

  *(uint8_t*)buff = htons(pkt->input);
  buff += sizeof(uint8_t);

}

void deserialise(net_packet_t *pkt, const unsigned char *buff) {
  /* TODO: Deserialise the packet into the net_packet structure. */

  //ntohs converts data from network byte order to the host's native byte order.

  pkt->opcode = ntohs(*(uint8_t*)buff); 
  buff += sizeof(uint8_t);

  pkt->epoch = ntohs(*(uint16_t*)buff);
  buff += sizeof(uint16_t);

  pkt->input = ntohs(*(uint8_t*)buff);
  buff += sizeof(uint8_t);
}

int net_poll(net_packet_t *pkt) {
  /* TODO: Poll a packet from the socket.
   * Returns 0 if nothing to be read from the socket.
   * Returns 1 otherwise.*/
  int res = !(pkt->opcode); //if opcode is 1 (ack), there is nothing to be read so return 0, and conversely
  return res;
}

void net_send(const net_packet_t *pkt) {
  /* TODO: Serialise and send the packet to the other's socket. */

  unsigned char buff[100]; 
  serialise(buff,pkt);

  int len = sendto(sock,(const char*)buff, sizeof(buff), 0,
      (const struct sockaddr *)&sock_addr_other, sizeof(sock_addr_other)); 
  if (len < 0) {
      perror("\nCannot send packet");
      return;
  } 
}
/**/