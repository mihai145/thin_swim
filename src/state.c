#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "log.h"
#include "state.h"
#include "gossip_message.h"


void populate_peers(struct node_state *state, int num_peers, int* tcp_ports, int *udp_ports) {
    if (pthread_mutex_init(&state->lock, NULL) != 0) {
        logg(LEVEL_FATAL, "Failed to init state lock");
        exit(1);
    }

    pthread_mutex_lock(&state->lock);
    state->capacity = CAPACITY;
    state->num_peers = num_peers;

    state->tcp_ports = (int*)malloc(sizeof(int) * state->capacity);
    state->udp_ports = (int*)malloc(sizeof(int) * state->capacity);

    memcpy(state->tcp_ports, tcp_ports, sizeof(int) * num_peers);
    memcpy(state->udp_ports, udp_ports, sizeof(int) * num_peers);
    pthread_mutex_unlock(&state->lock);
}

int append_member(struct node_state *state, int tcp_port, int udp_port) {
    pthread_mutex_lock(&state->lock);
    if (state->num_peers + 1 > state->capacity) {
      pthread_mutex_unlock(&state->lock);
      return -1;
    }

    state->tcp_ports[state->num_peers] = tcp_port;
    state->udp_ports[state->num_peers] = udp_port;
    state->num_peers++;

    pthread_mutex_unlock(&state->lock);
    return 0;
}

char *print_peers(struct node_state *state) {
    pthread_mutex_lock(&state->lock);
    char *peer_string = malloc(50 + state->num_peers * 15);
    memset(peer_string, 0, 50 + state->num_peers * 15);

    sprintf(peer_string, "%d peers: ", state->num_peers);
    for (int i = 0; i < state->num_peers; i++) {
        char peer_repr[13], sep=' ';
        if (i < state->num_peers - 1) sep = ',';
        sprintf(peer_repr, "%d-%d%c ", state->tcp_ports[i], state->udp_ports[i], sep);
        strcat(peer_string, peer_repr);
    }

    pthread_mutex_unlock(&state->lock);
    return peer_string;
}

int get_gossip_rounds(struct node_state *state) {
    if (state->num_peers == 0) return 1;
    return 2 * (int)log(state->num_peers);
}

void add_broadcast_to_list(struct node_state *state, int tcp_port, int udp_port, int status) {
    struct broadcast b;
    b.tcp_port = tcp_port;
    b.udp_port = udp_port;
    b.status = status;
    b.remaining_rounds = get_gossip_rounds(state);

    if (state->cnt_broadcast >= state->broadcast_list_capacity) {  // extend broadcast list capacity
        state->broadcast_list_capacity *= 2;
        state->broadcast_list = (struct broadcast*)realloc(state->broadcast_list, sizeof(struct broadcast) * state->broadcast_list_capacity);
    }

    state->broadcast_list[state->cnt_broadcast] = b;
    state->cnt_broadcast++;
}

void append_broadcast(struct node_state *state, int tcp_port, int udp_port, int status) {
    pthread_mutex_lock(&state->lock);

    add_broadcast_to_list(state, tcp_port, udp_port, status);

    pthread_mutex_unlock(&state->lock);
}

void tidy_broadcast_list(struct node_state *state) {
    struct broadcast* tidied_list = (struct broadcast*)malloc(sizeof(struct broadcast) * state->cnt_broadcast);

    int rem_broadcasts = 0;
    for (int i = 0; i < state->cnt_broadcast; i++) {
        if (state->broadcast_list[i].remaining_rounds > 0) {
            tidied_list[rem_broadcasts] = state->broadcast_list[i];
            rem_broadcasts++;
        }
    }

    state->cnt_broadcast = rem_broadcasts;
    for (int i = 0; i < rem_broadcasts; i++) {
        state->broadcast_list[i] = tidied_list[i];
    }
    free(tidied_list);
}

void gossip_changes_to(int udp_port, struct gossip_message *gossip) {
    logg(LEVEL_DBG, "Gossiping %d changes to %d", gossip->cnt_updates, udp_port);

    int fd_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_socket < 0) {
        logg(LEVEL_DBG, "Failed to open UDP socket");
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(udp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (sendto(fd_socket, gossip, sizeof(*gossip), 0, (const struct sockaddr *) &server_addr, sizeof(server_addr)) < 0) {
        logg(LEVEL_DBG, "Failed to reach send UDP message to %d", udp_port);
    }
}

void gossip_changes(struct node_state *state) {
    pthread_mutex_lock(&state->lock);
    if (state->cnt_broadcast == 0) {
        pthread_mutex_unlock(&state->lock);
        return;
    }

    struct gossip_message gossip;

    gossip.message_type = GOSSIP_UPDATE;
    gossip.node_name_tcp = state->own_tcp_port;
    gossip.node_time = state->lamport_time;
    gossip.cnt_updates = state->cnt_broadcast;
    for (int i = 0; i < gossip.cnt_updates; i++) {
        gossip.tcp_ports[i] = state->broadcast_list[i].tcp_port;
        gossip.udp_ports[i] = state->broadcast_list[i].udp_port;
        gossip.statuses[i] = state->broadcast_list[i].status;
        state->broadcast_list[i].remaining_rounds--;
    }

    tidy_broadcast_list(state);

    // send message to fan_out random peers (in the current implementation, may not be distinct)
    if (state->num_peers > 0) {
        for (int i = 0; i < FAN_OUT; i++) {
            int idx_peer = rand() % state->num_peers;
            gossip_changes_to(state->udp_ports[idx_peer], &gossip);
        }
    }
    pthread_mutex_unlock(&state->lock);
}

int idx_of(struct node_state *state, int tcp_port, int udp_port) {
    int idx_state = -1;
    for (int i = 0; i < state->num_peers; i++) {
        if (state->tcp_ports[i] == tcp_port && state->udp_ports[i] == udp_port) {
            idx_state = i;
            break;
        }
    }
    return idx_state;
}

void remove_peer(struct node_state *state, int idx_peer) {
    int *tcp_ports = malloc(sizeof(int) * (state->num_peers - 1));
    int *udp_ports = malloc(sizeof(int) * (state->num_peers - 1));

    int ptr = 0;
    for (int i = 0; i < state->num_peers; i++) {
        if (i != idx_peer) {
            tcp_ports[ptr] = state->tcp_ports[i];
            udp_ports[ptr] = state->udp_ports[i];
            ptr++;
        }
    }

    state->num_peers--;
    for (int i = 0; i < ptr; i++) {
        state->tcp_ports[i] = tcp_ports[i];
        state->udp_ports[i] = udp_ports[i];
    }

    free(tcp_ports);
    free(udp_ports);
}

void add_peer(struct node_state *state, int tcp_port, int udp_port) {
    state->tcp_ports[state->num_peers] = tcp_port;
    state->udp_ports[state->num_peers] = udp_port;
    state->num_peers++;
}

void update_member(struct node_state *state, int tcp_port, int udp_port, int status) {
    int append_to_broadcast = 0;
    int idx_peer = idx_of(state, tcp_port, udp_port);

    if (status == 0) {
        // node is declared removed
        // if it is in state (or is self), remove it and append to broadcast list
        if (idx_peer > 0) {
            remove_peer(state, idx_peer);
            append_to_broadcast = 1;
        }
    } else {
        // node is joining
        // if it is not in state, add it and append to broadcast list
        if (idx_peer == -1 && !(tcp_port == state->own_tcp_port && udp_port == state->own_udp_port)) {
            add_peer(state, tcp_port, udp_port);
            append_to_broadcast = 1;
        }
    }

    if (append_to_broadcast) {
        add_broadcast_to_list(state, tcp_port, udp_port, status);
    }
}

void process_updates(struct node_state *state, struct gossip_message *gossip) {
    pthread_mutex_lock(&state->lock);

    for (int i = 0; i < gossip->cnt_updates; i++) {
        update_member(state, gossip->tcp_ports[i], gossip->udp_ports[i], gossip->statuses[i]);
    }

    pthread_mutex_unlock(&state->lock);
}

void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

void fisher_yates(struct node_state *state) {
    state->cnt_probing = state->num_peers;
    if (state->tcp_ports_to_probe != NULL) free(state->tcp_ports_to_probe);
    if (state->udp_ports_to_probe != NULL) free(state->udp_ports_to_probe);

    state->tcp_ports_to_probe = (int*)malloc(sizeof(int) * state->cnt_probing);
    state->udp_ports_to_probe = (int*)malloc(sizeof(int) * state->cnt_probing);
    memcpy(state->tcp_ports_to_probe, state->tcp_ports, sizeof(int) * state->cnt_probing);
    memcpy(state->udp_ports_to_probe, state->udp_ports, sizeof(int) * state->cnt_probing);

    for (int i = state->cnt_probing - 1; i >= 0; i--) {
        int rand_idx = rand() % (i + 1);

        swap(&state->tcp_ports_to_probe[i], &state->tcp_ports_to_probe[rand_idx]);
        swap(&state->udp_ports_to_probe[i], &state->udp_ports_to_probe[rand_idx]);
    }

    // printf("Node %d-%d: fisher_yates udp result: ", state->own_tcp_port, state->own_udp_port);
    // for (int i = 0; i < state->cnt_probing; i++) {
    //     printf("%d ", state->udp_ports_to_probe[i]);
    // }
    // puts("");
}

void probe(struct node_state *state, int udp_port) {
    struct gossip_message gossip;
    gossip.message_type = PROBE;
    gossip.node_name_tcp = state->own_tcp_port;
    gossip.node_name_udp = state->own_udp_port;

    logg(LEVEL_DBG, "Probing %d", udp_port);

    int fd_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_socket < 0) {
        logg(LEVEL_DBG, "Failed to open UDP socket");
        state->probed = 1;    // asume probe ok
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(udp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (sendto(fd_socket, &gossip, sizeof(struct gossip_message), 0, (const struct sockaddr *) &server_addr, sizeof(server_addr)) < 0) {
        logg(LEVEL_DBG, "Failed to probe %d", udp_port);
        state->probed = 1;    // asume probe ok
    }
}

void probe_next(struct node_state *state) {
    pthread_mutex_lock(&state->lock);

    state->current_tcp_port_to_probe = -1;
    state->current_udp_port_to_probe = -1;
    state->probed = -1;
    if (state->cnt_probing == 0) {
        if (state->num_peers > 0)
            fisher_yates(state);
    }

    if (state->cnt_probing > 0) {
        state->cnt_probing--;
        state->current_tcp_port_to_probe = state->tcp_ports_to_probe[state->cnt_probing];
        state->current_udp_port_to_probe = state->udp_ports_to_probe[state->cnt_probing];

        probe(state, state->current_udp_port_to_probe);
    }

    pthread_mutex_unlock(&state->lock);
}

void reply_probe(struct node_state *state, int udp_port) {
    // should be fine lock-free

    struct gossip_message gossip;
    gossip.message_type = ACK_PROBE;
    gossip.node_name_tcp = state->own_tcp_port;
    gossip.node_name_udp = state->own_udp_port;

    logg(LEVEL_DBG, "Ack probe to %d", udp_port);

    int fd_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_socket < 0) {
        logg(LEVEL_DBG, "Failed to open UDP socket");
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(udp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (sendto(fd_socket, &gossip, sizeof(struct gossip_message), 0, (const struct sockaddr *) &server_addr, sizeof(server_addr)) < 0) {
        logg(LEVEL_DBG, "Failed to ack probe to %d", udp_port);
    }
}

void check_ack(struct node_state *state, int udp_port) {
    pthread_mutex_lock(&state->lock);

    if (state->current_udp_port_to_probe == udp_port) state->probed = 1;

    pthread_mutex_unlock(&state->lock);
}

void check_probed(struct node_state *state) {
  pthread_mutex_lock(&state->lock);

  if (state->current_udp_port_to_probe != -1) {
      if (state->probed == -1) {
          // declare dead + broadcast
          logg(LEVEL_INFO, "found %d-%d is dead", state->current_tcp_port_to_probe, state->current_udp_port_to_probe);

          int idx_peer = idx_of(state, state->current_tcp_port_to_probe, state->current_udp_port_to_probe);
          remove_peer(state, idx_peer);
          add_broadcast_to_list(state, state->current_tcp_port_to_probe, state->current_udp_port_to_probe, 0);
      } else {
          logg(LEVEL_DBG, "found %d-%d is alive", state->current_tcp_port_to_probe, state->current_udp_port_to_probe);
      }
  }

  pthread_mutex_unlock(&state->lock);
}
