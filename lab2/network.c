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
#include "sys/socket.h"

#include <arpa/inet.h>
#include <assert.h>
#include <errno.h>
#include <netdb.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int sock;
static struct sockaddr_in sock_addr_other;

void net_init(unsigned short port_self, const char *hostname_other,
	      unsigned short port_other)
{
	/*
	 * TODO:
	 *
	 * 1. Create a UDP socket.
	 *
	 * 2. Bind the socket to port_self.
	 *
	 * 3. Set sock_addr_other to the socket address at hostname_other and
	 * port_other.
	 *
	 */
	// #1
	sock = socket(AF_INET, SOCK_DGRAM, 0);
	if (sock < 0) {
		perror("Socket creation failed");
		exit(EXIT_FAILURE);
	}

	// #2
	struct sockaddr_in sock_addr_self;
	memset(&sock_addr_self, 0, sizeof(sock_addr_self));
	sock_addr_self.sin_family = AF_INET;
	sock_addr_self.sin_addr.s_addr = htonl(INADDR_ANY);
	sock_addr_self.sin_port = htons(port_self);

	if (bind(sock, (struct sockaddr *)&sock_addr_self,
		 sizeof(sock_addr_self)) < 0) {
		perror("Bind failed");
		close(sock);
		exit(EXIT_FAILURE);
	}

	// #3
	memset(&sock_addr_other, 0, sizeof(sock_addr_other));
	sock_addr_other.sin_family = AF_INET;
	sock_addr_other.sin_port = htons(port_other);

	struct hostent *host = gethostbyname(hostname_other);
	if (host == NULL) {
		perror("Failed to resolve hostname");
		close(sock);
		exit(EXIT_FAILURE);
	}
	memcpy(&sock_addr_other.sin_addr, host->h_addr_list[0], host->h_length);
}

void net_fini()
{ /* TODO: Shutdown the socket. */
	close(sock);
}

static void serialise(unsigned char *buff, const net_packet_t *pkt)
{
	/* TODO:
	 *
	 * Serialise the packet according to the protocol.
	 *
	 * Note that it must use network endian.
	 */
    buff[0] = pkt->cmd;
    uint16_t epoch_net = htons(pkt->epoch);
    memcpy(buff+1, &epoch_net, sizeof(epoch_net));
    buff[3] = pkt->input;
}

static void deserialise(net_packet_t *pkt, const unsigned char *buff)
{
	/* TODO: Deserialise the packet into the net_packet structure. */
    pkt->cmd = buff[0];
    uint16_t epoch_net;
    memcpy(&epoch_net, buff + 1, sizeof(epoch_net));
    pkt->epoch = ntohs(epoch_net);
    pkt->input = buff[3];  
}

int net_poll(net_packet_t *pkt)
{
	/* TODO: Poll a packet from the socket.
	 *
	 * Returns 0 if nothing to be read from the socket.
	 *
	 * Returns 1 otherwise.
	 */
    struct pollfd pfd = {.fd=sock, .events=POLLIN};
    int ret = poll(&pfd, 1, 0);
    if (ret <= 0) {
        return 0;
    }
    unsigned char buffer[1024];
    socklen_t addr_len = sizeof(sock_addr_other);
    ssize_t bytes_received = recvfrom(sock, buffer, sizeof(buffer), 0,
                                      (struct sockaddr *)&sock_addr_other, &addr_len);
    if (bytes_received > 0) {
        deserialise(pkt, buffer);
        return 1;
    }
	return 0;
}

void net_send(const net_packet_t *pkt)
{
	/* TODO: Serialise and send the packet to the other's socket. */
    unsigned char buffer[1024];
    serialise(buffer, pkt);

    sendto(sock, buffer, sizeof(buffer), 0, (struct sockaddr *)&sock_addr_other,
           sizeof(sock_addr_other));
}
