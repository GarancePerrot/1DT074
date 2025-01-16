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

#ifndef NETWORK_H
#define NETWORK_H

#include "includes.h"



typedef struct net_packet {
  /* TODO: Declare variables according to the protocol. */
  uint8_t opcode; // 1 byte: 0 or 1
  uint16_t epoch; // 2 bytes : epoch nb
  uint8_t input; // 1 byte : 0 none, 1 up, 2 down
} net_packet_t;

void net_init(int sock, struct sockaddr_in* sock_addr_other, unsigned short port_self, const char *hostname_other,
              unsigned short port_other, socklen_t sao_size);
void net_fini(int sock);
void net_send(int sock, const struct sockaddr_in* sock_addr_other, const net_packet_t *pkt,  unsigned char *buff, socklen_t sao_size);
int net_poll(net_packet_t *pkt);

void serialise(unsigned char *buff, const net_packet_t *pkt);
void deserialise(net_packet_t *pkt, const unsigned char *buff);
#endif
