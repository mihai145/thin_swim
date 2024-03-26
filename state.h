#ifndef STATE_H
#define STATE_H

#include <pthread.h>
#include "gossip_message.h"

#define CAPACITY 100
#define FAN_OUT 2

struct broadcast {
    int tcp_port, udp_port;
    int status;  // 0 -> removed, 1 -> joined

    int remaining_rounds;
};

struct node_state {
    pthread_mutex_t lock;

    int own_tcp_port, own_udp_port;

    int capacity;
    int num_peers;

    int* tcp_ports;
    int* udp_ports;

    int cnt_probing;
    int* tcp_ports_to_probe;
    int* udp_ports_to_probe;

    int current_tcp_port_to_probe;
    int current_udp_port_to_probe;
    int probed;

    int cnt_broadcast, broadcast_list_capacity;
    struct broadcast* broadcast_list;
};

void populate_peers(struct node_state *state, int num_peers, int* tcp_ports, int *udp_ports);

int append_member(struct node_state *state, int tcp_port, int udp_port);

char *print_peers(struct node_state *state);

void append_broadcast(struct node_state *state, int tcp_port, int udp_port, int status);

void gossip_changes(struct node_state *state, int node_name, int node_time);

void process_updates(struct node_state *state, struct gossip_message *gossip);

void probe_next(struct node_state *state);

void reply_probe(struct node_state *state, int udp_port);

void check_ack(struct node_state *state, int udp_port);

void check_probed(struct node_state *state);

#endif