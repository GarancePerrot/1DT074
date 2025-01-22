/*
 * Copyright (C) 2022, 2023, 2024  Xiaoyue Chen
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
#include "simulate.h"
#include "unistd.h"
#include "window.h"

#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>

static const int SCREEN_WIDTH = 720;
static const int SCREEN_HEIGHT = 640;
static const int SIM_INTERVAL = 10;

typedef struct epoch {
	bool cmd;
	bool ack;
	bool cmd_self;
} epoch_t;

int main(int argc, char *argv[argc + 1])
{
	unsigned short port_self = atoi(argv[1]);  /* 9930 */
	const char *hostname_other = argv[2];	   /* "127.0.0.1" */
	unsigned short port_other = atoi(argv[3]); /* 9931 */
	int player = atol(argv[4]);		   /* 0 */

	state_t state = sim_init(SCREEN_WIDTH, SCREEN_HEIGHT);
	win_init(SCREEN_WIDTH, SCREEN_HEIGHT);
	net_init(port_self, hostname_other, port_other);

	uint16_t epoch = 0;
	epoch_t epoch_state = {false, false, false};
	cmd_t cmds[2];
	bool quit = false;

	uint32_t previous_tick = win_tick();

	while (!quit) {
		win_event_t e = win_poll_event();
		if (e.quit)
			quit = true;

		for (; win_tick() - previous_tick > SIM_INTERVAL;
		     previous_tick += SIM_INTERVAL) {
			/*
			 * TODO: Poll and handle each packet until no more
			 * packet.
			 *
			 * If we receive a command packet, send an
			 * acknowledgement packet, mark its flag in epoch_state,
			 * and set the command in cmds array. If we receive a
			 * acknowledge packet, just mark its flag in
			 * epoch_state.
			 */
			net_packet_t pkt;
			while (net_poll(&pkt)) {
				if (pkt.cmd == OP_ACK && pkt.epoch==epoch)
					epoch_state.ack = true;
				else if (pkt.cmd == OP_CMD && pkt.epoch<=epoch) {
					if (pkt.epoch==epoch){
						epoch_state.cmd = true;
						cmds[1 - player] = pkt.input;
					}
					net_packet_t ack_pkt = {.cmd = OP_ACK,
								.epoch = pkt.epoch,
								.input = 0};
					net_send(&ack_pkt);
                }
			}

			/* TODO: Update cmds[player] and set cmd_self in
			   epoch_state if cmd_self is not set */
			if (!epoch_state.cmd_self) {
				cmds[player] =
				    (e.up ^ e.down) *
				    (e.up * CMD_UP + e.down * CMD_DOWN);
				epoch_state.cmd_self = true;
			}

			/* TODO: Send a command packet. */
			net_packet_t cmd_pkt = {.cmd = OP_CMD,
						.epoch = epoch,
						.input = cmds[player]};
			net_send(&cmd_pkt);


			/* TODO: Add conditions for simulation. To simulate and
			   move onto the next epoch, we must have received the
			   command packet and the acknowledge packet from the
			   other player. */
			if (epoch_state.ack && epoch_state.cmd) {
				state = sim_update(&state, cmds,
						   SIM_INTERVAL / 1000.f);
				++epoch;
				epoch_state.cmd_self = epoch_state.cmd =
				    epoch_state.ack = false;
                win_render(&state);
			}
		}
	}

	net_fini();
	win_fini();
	return 0;
}
