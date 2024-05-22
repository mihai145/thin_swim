#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <time.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "log.h"
#include "state.h"
#include "gossip_message.h"
#include "constants.h"

void populate_peers(struct node_state *state, int num_peers, int *tcp_ports, int *udp_ports)
{
    state->capacity = CAPACITY;
    state->num_peers = num_peers;

    if (state->tcp_ports != NULL)
        free(state->tcp_ports);
    if (state->udp_ports != NULL)
        free(state->udp_ports);
    state->tcp_ports = (int *)malloc(sizeof(int) * state->capacity);
    state->udp_ports = (int *)malloc(sizeof(int) * state->capacity);

    memcpy(state->tcp_ports, tcp_ports, sizeof(int) * num_peers);
    memcpy(state->udp_ports, udp_ports, sizeof(int) * num_peers);

    // get current time
    struct timespec tp;
    clock_gettime(CLOCK_MONOTONIC, &tp);

    long long ns = tp.tv_sec * 1000000000ll + tp.tv_nsec;
    state->grace_period_until = ns + GRACE_PERIOD * 1000000000ll;
}

int append_member(struct node_state *state, int tcp_port, int udp_port)
{
    pthread_mutex_lock(&state->lock);
    if (state->num_peers + 1 > state->capacity)
    {
        pthread_mutex_unlock(&state->lock);
        return -1;
    }

    state->tcp_ports[state->num_peers] = tcp_port;
    state->udp_ports[state->num_peers] = udp_port;
    state->num_peers++;

    pthread_mutex_unlock(&state->lock);
    return 0;
}

char *print_peers(struct node_state *state)
{
    pthread_mutex_lock(&state->lock);
    char *peer_string = malloc(50 + state->num_peers * 15);
    memset(peer_string, 0, 50 + state->num_peers * 15);

    sprintf(peer_string, "%d peers: ", state->num_peers);
    for (int i = 0; i < state->num_peers; i++)
    {
        char peer_repr[13], sep = ' ';
        if (i < state->num_peers - 1)
            sep = ',';
        sprintf(peer_repr, "%d-%d%c ", state->tcp_ports[i], state->udp_ports[i], sep);
        strcat(peer_string, peer_repr);
    }

    pthread_mutex_unlock(&state->lock);
    return peer_string;
}

int get_gossip_rounds(struct node_state *state)
{
    if (state->num_peers == 0)
        return 1;
    return 2 * (int)log(state->num_peers);
}

void add_broadcast_to_list(struct node_state *state, int tcp_port, int udp_port, int status)
{
    struct broadcast b;
    b.tcp_port = tcp_port;
    b.udp_port = udp_port;
    b.status = status;
    b.remaining_rounds = get_gossip_rounds(state);

    if (state->cnt_broadcast >= state->broadcast_list_capacity)
    { // extend broadcast list capacity
        state->broadcast_list_capacity *= 2;
        state->broadcast_list = (struct broadcast *)realloc(state->broadcast_list, sizeof(struct broadcast) * state->broadcast_list_capacity);
    }

    state->broadcast_list[state->cnt_broadcast] = b;
    state->cnt_broadcast++;
}

void append_broadcast(struct node_state *state, int tcp_port, int udp_port, int status)
{
    pthread_mutex_lock(&state->lock);

    add_broadcast_to_list(state, tcp_port, udp_port, status);

    pthread_mutex_unlock(&state->lock);
}

void tidy_broadcast_list(struct node_state *state)
{
    struct broadcast *tidied_list = (struct broadcast *)malloc(sizeof(struct broadcast) * state->cnt_broadcast);

    int rem_broadcasts = 0;
    for (int i = 0; i < state->cnt_broadcast; i++)
    {
        if (state->broadcast_list[i].remaining_rounds > 0)
        {
            tidied_list[rem_broadcasts] = state->broadcast_list[i];
            rem_broadcasts++;
        }
    }

    state->cnt_broadcast = rem_broadcasts;
    for (int i = 0; i < rem_broadcasts; i++)
    {
        state->broadcast_list[i] = tidied_list[i];
    }
    free(tidied_list);
}

void send_gossip_message_to(int udp_port, struct gossip_message *gossip)
{
    int fd_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_socket < 0)
    {
        logg(LEVEL_DBG, "Failed to open UDP socket");
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(udp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (sendto(fd_socket, gossip, sizeof(*gossip), 0, (const struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        logg(LEVEL_DBG, "Failed to reach send UDP message to %d", udp_port);
    }
}

void swap(int *a, int *b)
{
    int temp = *a;
    *a = *b;
    *b = temp;
}

// Fisher Yates algorithm for random shuffling an array in linear time
int *fisher_yates_(int *a, int nr)
{
    int *b = (int *)malloc(nr * sizeof(int));
    memcpy(b, a, nr * sizeof(int));

    for (int i = nr - 1; i >= 0; i--)
    {
        int rand_idx = rand() % (i + 1);
        swap(&b[i], &b[rand_idx]);
    }
    return b;
}

void shuffle_ports_to_probe(struct node_state *state)
{
    // clear data structure
    state->cnt_probing = state->num_peers;
    if (state->tcp_ports_to_probe != NULL)
        free(state->tcp_ports_to_probe);
    if (state->udp_ports_to_probe != NULL)
        free(state->udp_ports_to_probe);

    state->tcp_ports_to_probe = (int *)malloc(sizeof(int) * state->cnt_probing);
    state->udp_ports_to_probe = (int *)malloc(sizeof(int) * state->cnt_probing);

    // shuffle indices
    int *idx = (int *)malloc(sizeof(int) * state->cnt_probing);
    for (int i = 0; i < state->cnt_probing; i++)
        idx[i] = i;
    int *shuffle_idx = fisher_yates_(idx, state->cnt_probing);
    free(idx);

    for (int i = 0; i < state->cnt_probing; i++)
    {
        state->tcp_ports_to_probe[i] = state->tcp_ports[shuffle_idx[i]];
        state->udp_ports_to_probe[i] = state->udp_ports[shuffle_idx[i]];
    }
    free(shuffle_idx);
}

int *get_random_peers(struct node_state *state, int requested_peers, int *cnt_peers)
{
    int *k = malloc(requested_peers * sizeof(int));
    *cnt_peers = 0;

    int *rand = fisher_yates_(state->udp_ports, state->num_peers);
    for (int i = 0; i < state->num_peers && i < requested_peers; i++)
    {
        k[i] = rand[i];
        *cnt_peers = *cnt_peers + 1;
    }
    free(rand);

    return k;
}

int *get_random_peers_except(struct node_state *state, int requested_peers, int *cnt_peers, int exception)
{
    int *k = malloc(requested_peers * sizeof(int));
    *cnt_peers = 0;

    int *rand = fisher_yates_(state->udp_ports, state->num_peers);
    int ptr_k = 0;
    for (int i = 0; i < state->num_peers && *cnt_peers < requested_peers; i++)
    {
        if (rand[i] != exception)
        {
            k[ptr_k++] = rand[i];
            *cnt_peers = *cnt_peers + 1;
        }
    }
    free(rand);

    return k;
}

void check_fy(int *a, int cnt)
{
    int ok = 1;
    for (int i = 0; i < cnt; i++)
    {
        if (a[i] < 0 || a[i] > 60000)
        {
            logg(LEVEL_FATAL, "Error occured during Fisher Yates");
            ok = 0;
        }
    }

    for (int i = 0; i < cnt; i++)
    {
        for (int j = i + 1; j < cnt; j++)
        {
            if (a[i] == a[j])
            {
                logg(LEVEL_FATAL, "Error occured during Fisher Yates");
                ok = 0;
            }
        }
    }

    if (ok)
        logg(LEVEL_DBG, "Fisher Yates ok");
}

void gossip_changes(struct node_state *state)
{
    pthread_mutex_lock(&state->lock);
    if (state->cnt_broadcast == 0)
    {
        pthread_mutex_unlock(&state->lock);
        return;
    }

    struct gossip_message gossip;

    gossip.message_type = GOSSIP_UPDATE;
    gossip.node_name_tcp = state->own_tcp_port;
    gossip.node_name_udp = state->own_udp_port;
    gossip.node_time = state->lamport_time;
    gossip.cnt_updates = state->cnt_broadcast;
    for (int i = 0; i < gossip.cnt_updates; i++)
    {
        gossip.tcp_ports[i] = state->broadcast_list[i].tcp_port;
        gossip.udp_ports[i] = state->broadcast_list[i].udp_port;
        gossip.statuses[i] = state->broadcast_list[i].status;
        state->broadcast_list[i].remaining_rounds--;
    }

    tidy_broadcast_list(state);

    // send message to (at most) fan_out random peers
    int cnt_random_peers;
    int *random_peers = get_random_peers(state, FAN_OUT, &cnt_random_peers);

#ifdef SAFE_MODE
    check_fy(random_peers, cnt_random_peers);
#endif

    for (int i = 0; i < cnt_random_peers; i++)
    {
        logg(LEVEL_DBG, "Gossiping %d changes to %d", gossip.cnt_updates, random_peers[i]);
        send_gossip_message_to(random_peers[i], &gossip);
    }
    free(random_peers);

    pthread_mutex_unlock(&state->lock);
}

int idx_of(struct node_state *state, int tcp_port, int udp_port)
{
    int idx_state = -1;
    for (int i = 0; i < state->num_peers; i++)
    {
        if (state->tcp_ports[i] == tcp_port && state->udp_ports[i] == udp_port)
        {
            idx_state = i;
            break;
        }
    }
    return idx_state;
}

void remove_peer(struct node_state *state, int idx_peer)
{
    int *tcp_ports = malloc(sizeof(int) * (state->num_peers - 1));
    int *udp_ports = malloc(sizeof(int) * (state->num_peers - 1));

    int ptr = 0;
    for (int i = 0; i < state->num_peers; i++)
    {
        if (i != idx_peer)
        {
            tcp_ports[ptr] = state->tcp_ports[i];
            udp_ports[ptr] = state->udp_ports[i];
            ptr++;
        }
    }

    state->num_peers--;
    for (int i = 0; i < ptr; i++)
    {
        state->tcp_ports[i] = tcp_ports[i];
        state->udp_ports[i] = udp_ports[i];
    }

    free(tcp_ports);
    free(udp_ports);
}

void add_peer(struct node_state *state, int tcp_port, int udp_port)
{
    state->tcp_ports[state->num_peers] = tcp_port;
    state->udp_ports[state->num_peers] = udp_port;
    state->num_peers++;
}

void fix_broadcast_list(struct node_state *state)
{
    int ptr_broadcast = 0;
    struct broadcast *fixed_list = (struct broadcast *)malloc(sizeof(struct broadcast) * state->cnt_broadcast);

    for (int i = 0; i < state->cnt_broadcast; i++)
    {
        if (state->broadcast_list[i].status == 0 && idx_of(state, state->broadcast_list[i].tcp_port, state->broadcast_list[i].udp_port) > 0)
        {
            continue;
        }
        if (state->broadcast_list[i].status == 1 && idx_of(state, state->broadcast_list[i].tcp_port, state->broadcast_list[i].udp_port) == -1)
        {
            continue;
        }

        fixed_list[ptr_broadcast++] = state->broadcast_list[i];
    }

    state->cnt_broadcast = ptr_broadcast;
    for (int i = 0; i < ptr_broadcast; i++)
    {
        state->broadcast_list[i] = fixed_list[i];
    }
    free(fixed_list);
}

void update_member(struct node_state *state, int tcp_port, int udp_port, int status)
{
    int append_to_broadcast = 0;
    int idx_peer = idx_of(state, tcp_port, udp_port);

    if (status == 0)
    {
        // node is declared removed
        // if it is in state (or is self), remove it and append to broadcast list
        if (idx_peer > 0)
        {
            remove_peer(state, idx_peer);
            append_to_broadcast = 1;
        }
    }
    else
    {
        // node is joining
        // if it is not in state, add it and append to broadcast list
        if (idx_peer == -1 && !(tcp_port == state->own_tcp_port && udp_port == state->own_udp_port))
        {
            add_peer(state, tcp_port, udp_port);
            append_to_broadcast = 1;
        }
    }

    if (append_to_broadcast)
    {
        add_broadcast_to_list(state, tcp_port, udp_port, status);
    }

    fix_broadcast_list(state);
}

void process_updates(struct node_state *state, struct gossip_message *gossip)
{
    pthread_mutex_lock(&state->lock);

    for (int i = 0; i < gossip->cnt_updates; i++)
    {
        update_member(state, gossip->tcp_ports[i], gossip->udp_ports[i], gossip->statuses[i]);
    }

    pthread_mutex_unlock(&state->lock);
}

void probe(struct node_state *state, int udp_port)
{
    struct gossip_message gossip;
    gossip.message_type = PROBE;
    gossip.node_name_tcp = state->own_tcp_port;
    gossip.node_name_udp = state->own_udp_port;

    logg(LEVEL_DBG, "Probing %d", udp_port);

    int fd_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_socket < 0)
    {
        logg(LEVEL_DBG, "Failed to open UDP socket");
        state->probed = 1; // asume probe ok
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(udp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (sendto(fd_socket, &gossip, sizeof(struct gossip_message), 0, (const struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        logg(LEVEL_DBG, "Failed to probe %d", udp_port);
        state->probed = 1; // asume probe ok
    }
}

void probe_next(struct node_state *state)
{
    pthread_mutex_lock(&state->lock);

    state->current_tcp_port_to_probe = -1;
    state->current_udp_port_to_probe = -1;
    state->probed = -1;
    if (state->cnt_probing == 0)
    {
        if (state->num_peers > 0)
            shuffle_ports_to_probe(state);
    }

    if (state->cnt_probing > 0)
    {
        state->cnt_probing--;
        state->current_tcp_port_to_probe = state->tcp_ports_to_probe[state->cnt_probing];
        state->current_udp_port_to_probe = state->udp_ports_to_probe[state->cnt_probing];

        probe(state, state->current_udp_port_to_probe);
    }

    pthread_mutex_unlock(&state->lock);
}

void reply_probe(struct node_state *state, int udp_port)
{
    // should be fine lock-free

    struct gossip_message gossip;
    gossip.message_type = ACK_PROBE;
    gossip.node_name_tcp = state->own_tcp_port;
    gossip.node_name_udp = state->own_udp_port;

    logg(LEVEL_DBG, "Ack probe to %d", udp_port);

    int fd_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_socket < 0)
    {
        logg(LEVEL_DBG, "Failed to open UDP socket");
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(udp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (sendto(fd_socket, &gossip, sizeof(struct gossip_message), 0, (const struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        logg(LEVEL_DBG, "Failed to ack probe to %d", udp_port);
    }
}

void check_ack(struct node_state *state, int udp_port)
{
    pthread_mutex_lock(&state->lock);

    if (state->current_udp_port_to_probe == udp_port)
        state->probed = 1;

    pthread_mutex_unlock(&state->lock);
}

void check_probed(struct node_state *state)
{
    pthread_mutex_lock(&state->lock);

    if (state->current_udp_port_to_probe != -1)
    {
        if (state->probed == -1)
        {
            // declare dead + broadcast
            logg(LEVEL_INFO, "found %d-%d is dead", state->current_tcp_port_to_probe, state->current_udp_port_to_probe);

            int idx_peer = idx_of(state, state->current_tcp_port_to_probe, state->current_udp_port_to_probe);
            if (idx_peer != -1)
            {
                remove_peer(state, idx_peer);
                add_broadcast_to_list(state, state->current_tcp_port_to_probe, state->current_udp_port_to_probe, 0);
            }
        }
        else
        {
            logg(LEVEL_DBG, "found %d-%d is alive", state->current_tcp_port_to_probe, state->current_udp_port_to_probe);
        }
    }

    pthread_mutex_unlock(&state->lock);
}

void request_probes_if_no_ack(struct node_state *state)
{
    // check if we are currently & unsuccesfully probing a node
    // if so, send request probe to FANOUT random peers

    pthread_mutex_lock(&state->lock);

    if (state->current_udp_port_to_probe != -1 && state->probed == -1)
    {
        struct gossip_message request;
        request.message_type = REQUEST_PROBE;
        request.target_udp = state->current_udp_port_to_probe;
        request.node_name_tcp = state->own_tcp_port;
        request.node_name_udp = state->own_udp_port;
        request.node_time = state->lamport_time;

        // send request probe to (at most) fan_out random peers
        if (state->num_peers > 0)
        {
            int cnt_random_peers;
            int *random_peers = get_random_peers_except(state, FAN_OUT, &cnt_random_peers, state->current_udp_port_to_probe);

#ifdef SAFE_MODE
            check_fy(random_peers, cnt_random_peers);
#endif

            for (int i = 0; i < cnt_random_peers; i++)
            {
                logg(LEVEL_DBG, "Sending request-probe to %d to check on %d", random_peers[i], state->current_udp_port_to_probe);
                send_gossip_message_to(random_peers[i], &request);
            }
            free(random_peers);
        }
    }

    pthread_mutex_unlock(&state->lock);
}

void append_request_probe(struct node_state *state, int target_udp, int requestor_udp)
{
    // append current request to list of probe requests

    pthread_mutex_lock(&state->lock);

    struct timespec tp;
    clock_gettime(CLOCK_MONOTONIC, &tp);
    long long ns = tp.tv_sec * (long long)1000000000 + tp.tv_nsec;

    if (state->cnt_request_probes >= CAPACITY)
    {
        logg(LEVEL_FATAL, "Could not append request probe, capacity reached");
        exit(1);
    }

    state->udp_ports_requested_to_probe[state->cnt_request_probes] = target_udp;
    state->udp_ports_requestors[state->cnt_request_probes] = requestor_udp;
    state->probe_request_ns[state->cnt_request_probes] = ns;
    state->cnt_request_probes++;

    probe(state, target_udp);

    pthread_mutex_unlock(&state->lock);
}

int not_expired(long long ns_request, long long ns_current)
{
    long double off_s = 3. * PROBE_PERIOD / 4.;
    long double off_ms = off_s * 1000000000;

    if (ns_request + off_ms >= ns_current)
        return 1;
    return 0;
}

void fulfil_request_probes(struct node_state *state, int udp_port)
{
    // send ack to all request probes for this udp_port who have not expired
    // delete answered & expired requests

    pthread_mutex_lock(&state->lock);

    struct timespec tspec;
    clock_gettime(CLOCK_MONOTONIC, &tspec);
    long long ns_current = tspec.tv_sec * (long long)1000000000 + tspec.tv_nsec;

    int rem_request_probes = 0;
    int *rem_udp_ports_requested_to_probe = malloc(CAPACITY * sizeof(int));
    int *rem_udp_ports_requestors = malloc(CAPACITY * sizeof(int));
    long long *rem_probe_request_ns = malloc(CAPACITY * sizeof(long long));

    for (int i = 0; i < state->cnt_request_probes; i++)
    {
        if (not_expired(state->probe_request_ns[i], ns_current))
        {
            if (state->udp_ports_requested_to_probe[i] != udp_port)
            {
                rem_udp_ports_requested_to_probe[rem_request_probes] = state->udp_ports_requested_to_probe[i];
                rem_udp_ports_requestors[rem_request_probes] = state->udp_ports_requestors[i];
                rem_probe_request_ns[rem_request_probes] = state->probe_request_ns[i];
                rem_request_probes++;
            }
            else
            {
                // send ack to requestser
                logg(LEVEL_INFO, "Acking %d that %d is alive", state->udp_ports_requestors[i], udp_port);

                struct gossip_message gossip;
                gossip.message_type = ACK_PROBE;
                gossip.node_name_udp = udp_port;

                send_gossip_message_to(state->udp_ports_requestors[i], &gossip);
            }
        }
    }

    int *tp = state->udp_ports_requested_to_probe;
    state->udp_ports_requested_to_probe = rem_udp_ports_requested_to_probe;

    int *tpr = state->udp_ports_requestors;
    state->udp_ports_requestors = rem_udp_ports_requestors;

    long long *ltp = state->probe_request_ns;
    state->probe_request_ns = rem_probe_request_ns;

    state->cnt_request_probes = rem_request_probes;

    free(tp);
    free(tpr);
    free(ltp);

    pthread_mutex_unlock(&state->lock);
}

int is_peer(struct node_state *state, int udp_port)
{
    pthread_mutex_lock(&state->lock);

    int peer = 0;
    for (int i = 0; i < state->num_peers; i++)
    {
        if (state->udp_ports[i] == udp_port)
        {
            peer = 1;
            break;
        }
    }

    pthread_mutex_unlock(&state->lock);

    return peer;
}

void reply_not_peer(struct node_state *state, int udp_port)
{
    pthread_mutex_lock(&state->lock);

    logg(LEVEL_INFO, "Sending %d NOT_A_PEER reply", udp_port);

    struct gossip_message gossip;
    gossip.message_type = NOT_A_PEER;
    gossip.node_name_tcp = state->own_tcp_port;
    gossip.node_name_udp = state->own_udp_port;

    send_gossip_message_to(udp_port, &gossip);

    pthread_mutex_unlock(&state->lock);
}

void remv_peer(struct node_state *state, int tcp_port, int udp_port)
{
    pthread_mutex_lock(&state->lock);
    int idx_peer = idx_of(state, tcp_port, udp_port);
    if (idx_peer > 0)
    {
        remove_peer(state, idx_peer);
    }
    pthread_mutex_unlock(&state->lock);
}

double get_remaining_grace_period(struct node_state *state)
{
    pthread_mutex_lock(&state->lock);

    // get current time
    struct timespec tp;
    clock_gettime(CLOCK_MONOTONIC, &tp);

    long long ns = tp.tv_sec * 1000000000 + tp.tv_nsec;
    long long diff = state->grace_period_until - ns;

    double to_sleep = 0.;
    if (diff > 0)
        to_sleep = 1. * diff / 1000000000.;

    pthread_mutex_unlock(&state->lock);

    return to_sleep;
}
