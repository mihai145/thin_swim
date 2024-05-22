#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "node_manager.h"
#include "state.h"
#include "log.h"
#include "time_utils.h"
#include "constants.h"

#include "join_message.h"
#include "gossip_message.h"

struct node_state state;

void init_state(int tcp_port, int udp_port)
{
    if (pthread_mutex_init(&state.lock, NULL) != 0)
    {
        logg(LEVEL_FATAL, "Failed to init state lock");
        exit(1);
    }

    state.own_tcp_port = tcp_port;
    state.own_udp_port = udp_port;
    state.lamport_time = 0;

    state.cnt_broadcast = 0;
    state.broadcast_list_capacity = 1;
    state.broadcast_list = malloc(sizeof(struct broadcast));
    state.tcp_ports_to_probe = NULL;
    state.udp_ports_to_probe = NULL;
    state.current_tcp_port_to_probe = -1;
    state.current_udp_port_to_probe = -1;
    state.probed = -1;
    state.cnt_probing = 0;
    state.cnt_request_probes = 0;
    state.udp_ports_requested_to_probe = malloc(CAPACITY * sizeof(int));
    state.udp_ports_requestors = malloc(CAPACITY * sizeof(int));
    state.probe_request_ns = malloc(CAPACITY * sizeof(long long));
}

void reset_state()
{
    pthread_mutex_lock(&state.lock);
    state.cnt_broadcast = 0;
    state.broadcast_list_capacity = 1;

    if (state.tcp_ports_to_probe != NULL)
    {
        free(state.tcp_ports_to_probe);
        state.tcp_ports_to_probe = NULL;
    }
    if (state.udp_ports_to_probe != NULL)
    {
        free(state.udp_ports_to_probe);
        state.udp_ports_to_probe = NULL;
    }

    state.current_tcp_port_to_probe = -1;
    state.current_udp_port_to_probe = -1;
    state.probed = -1;
    state.cnt_probing = 0;
    state.cnt_request_probes = 0;

    free(state.udp_ports_requested_to_probe);
    free(state.udp_ports_requestors);
    free(state.probe_request_ns);
    state.udp_ports_requested_to_probe = malloc(CAPACITY * sizeof(int));
    state.udp_ports_requestors = malloc(CAPACITY * sizeof(int));
    state.probe_request_ns = malloc(CAPACITY * sizeof(long long));

    if (state.num_peers == 0)
    {
        logg(LEVEL_FATAL, "No peer to connect to");
    }

    sleep_(GRACE_PERIOD);

    int rand_peer = rand() % state.num_peers;
    logg(LEVEL_INFO, "Rejoining via %d-%d", state.tcp_ports[rand_peer], state.udp_ports[rand_peer]);
    join_network(state.tcp_ports[rand_peer], state.udp_ports[rand_peer]);

    pthread_mutex_unlock(&state.lock);
}

void join_network(int tcp_gateway, __attribute__((unused)) int udp_gateway)
{
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(tcp_gateway);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    int fd_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (fd_socket < 0)
    {
        logg(LEVEL_FATAL, "Failed to create TCP socket");
        exit(1);
    }
    if (connect(fd_socket, (const struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        logg(LEVEL_FATAL, "Error connecting to server TCP gateway socket");
        exit(1);
    }

    // send join request
    struct join_request snd_msg;
    memset(&snd_msg, 0, sizeof(snd_msg));
    snd_msg.tcp_port = state.own_tcp_port;
    snd_msg.udp_port = state.own_udp_port;

    if (send(fd_socket, &snd_msg, sizeof(snd_msg), 0) < 0)
    {
        logg(LEVEL_FATAL, "Error occured while sending TCP message");
        exit(1);
    }

    // wait for join reply
    struct join_reply recv_msg;
    memset(&recv_msg, 0, sizeof(recv_msg));
    if (recv(fd_socket, &recv_msg, sizeof(recv_msg), 0) < 0)
    {
        logg(LEVEL_FATAL, "Did not receive join reply");
        exit(1);
    }

    logg(LEVEL_INFO, "Received join reply, discovered network with %d peers", recv_msg.num_peers);

    close(fd_socket);
    populate_peers(&state, recv_msg.num_peers, recv_msg.tcp_ports, recv_msg.udp_ports);
}

void start_network(int argc, char **argv)
{
    int num_seeds = (argc - 4) / 3;
    int *tcp_ports = malloc(num_seeds * sizeof(int));
    int *udp_ports = malloc(num_seeds * sizeof(int));

    for (int i = 0; i < num_seeds; i++)
    {
        tcp_ports[i] = atoi(argv[4 + 3 * i + 1]);
        udp_ports[i] = atoi(argv[4 + 3 * i + 2]);
    }

    populate_peers(&state, num_seeds, tcp_ports, udp_ports);
    free(tcp_ports);
    free(udp_ports);

    for (int i = 0; i < state.num_peers; i++)
    {
        logg(LEVEL_DBG, "%dth seed has TCP=%d, UDP=%d", i + 1, state.tcp_ports[i], state.udp_ports[i]);
    }
}

void *tcp_port_listener(__attribute__((unused)) void *params)
{
    int fd_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (fd_socket < 0)
    {
        logg(LEVEL_FATAL, "Failed to create TCP port");
        exit(1);
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(state.own_tcp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    int cnt_failures_left = 5;
    while (bind(fd_socket, (const struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        logg(LEVEL_FATAL, "Tried and failed to bind TCP socket to desired port %d. Retrying...", state.own_tcp_port);
        cnt_failures_left--;

        if (cnt_failures_left < 0)
            break;
        sleep_(0.1);
    }

    if (cnt_failures_left < 0)
    {
        logg(LEVEL_FATAL, "Failed to bind TCP socket to desired port %d.", state.own_tcp_port);
        exit(1);
    }

    if (listen(fd_socket, 50) < 0)
    {
        logg(LEVEL_FATAL, "Failed to start listening to desired port");
        exit(1);
    }
    else
    {
        logg(LEVEL_INFO, "Listening on TCP port %d", state.own_tcp_port);
    }

    while (1)
    {
        struct sockaddr_in client_addr;
        memset(&client_addr, 0, sizeof(client_addr));
        socklen_t client_socklen = sizeof(client_addr);
        int client_socket = accept(fd_socket, (struct sockaddr *)&client_addr, &client_socklen);
        if (client_socket < 0)
        {
            logg(LEVEL_DBG, "Failed to accept connection. Resume listening...");
            continue;
        }
        else
            logg(LEVEL_DBG, "Client connected on port %d", client_addr.sin_port);

        // wait for join request
        struct join_request recv_msg;
        memset(&recv_msg, 0, sizeof(recv_msg));
        if (recv(client_socket, &recv_msg, sizeof(recv_msg), 0) < 0)
        {
            logg(LEVEL_DBG, "Could not receive join request. Resuming listening...");
            continue;
        }
        logg(LEVEL_DBG, "Received join request from %d-%d", recv_msg.tcp_port, recv_msg.udp_port);

        // reply with join reply
        remv_peer(&state, recv_msg.tcp_port, recv_msg.udp_port); // remove node if previously among peers

        struct join_reply snd_msg;
        memset(&snd_msg, 0, sizeof(snd_msg));

        snd_msg.num_peers = state.num_peers + 1;
        memcpy(snd_msg.tcp_ports, state.tcp_ports, sizeof(int) * state.num_peers);
        memcpy(snd_msg.udp_ports, state.udp_ports, sizeof(int) * state.num_peers);
        snd_msg.tcp_ports[state.num_peers] = state.own_tcp_port;
        snd_msg.udp_ports[state.num_peers] = state.own_udp_port;

        if (send(client_socket, &snd_msg, sizeof(snd_msg), 0) < 0)
        {
            logg(LEVEL_DBG, "Error occured while sending join reply. Resume listening...");
            continue;
        }
        else
            logg(LEVEL_DBG, "Sent join reply successfully");

        close(client_socket);
        if (append_member(&state, recv_msg.tcp_port, recv_msg.udp_port) == -1)
        {
            logg(LEVEL_FATAL, "State capacity reached, failed to append member");
            exit(1);
        }

        append_broadcast(&state, recv_msg.tcp_port, recv_msg.udp_port, 1);
    }

    return NULL;
}

void *udp_port_listener(__attribute__((unused)) void *params)
{
    int fd_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_socket < 0)
    {
        logg(LEVEL_FATAL, "Failed to create UDP socket");
        exit(1);
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(state.own_udp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    int cnt_failures_left = 5;
    while (bind(fd_socket, (const struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        logg(LEVEL_FATAL, "Tried and failed to bind UDP socket to desired port %d. Retrying...", state.own_udp_port);
        cnt_failures_left--;

        if (cnt_failures_left < 0)
            break;
        sleep_(0.1);
    }

    if (cnt_failures_left < 0)
    {
        logg(LEVEL_FATAL, "Failed to bind UDP socket to desired port %d.", state.own_udp_port);
        exit(1);
    }
    while (1)
    {
        struct gossip_message recv_msg;
        memset(&recv_msg, 0, sizeof(recv_msg));

        if (recv(fd_socket, &recv_msg, sizeof(recv_msg), 0) < 0)
        {
            logg(LEVEL_DBG, "Error occured while receiving UDP message. Resuming listening...");
            continue;
        }

        // reply with NOT_A_PEER if the received message is not from a known peer
        if (!is_peer(&state, recv_msg.node_name_udp))
        {
            logg(LEVEL_DBG, "Received a message from %d who is not a peer", recv_msg.node_name_udp);
            reply_not_peer(&state, recv_msg.node_name_udp);
            continue;
        }

        if (recv_msg.message_type == GOSSIP_UPDATE)
        {
            logg(LEVEL_DBG, "Received %d changes via gossip", recv_msg.cnt_updates);
            process_updates(&state, &recv_msg);
        }
        if (recv_msg.message_type == PROBE)
        {
            logg(LEVEL_DBG, "Probed by %d. Sending reply...", recv_msg.node_name_udp);
            reply_probe(&state, recv_msg.node_name_udp);
        }
        if (recv_msg.message_type == ACK_PROBE)
        {
            check_ack(&state, recv_msg.node_name_udp);             // check ack
            fulfil_request_probes(&state, recv_msg.node_name_udp); // check if we could answer a REQUEST_PROBE
        }
        if (recv_msg.message_type == REQUEST_PROBE)
        {
            append_request_probe(&state, recv_msg.target_udp, recv_msg.node_name_udp);
        }
        if (recv_msg.message_type == NOT_A_PEER)
        {
            logg(LEVEL_INFO, "Received not a peer from %d-%d. Rejoining...", recv_msg.node_name_tcp, recv_msg.node_name_udp);
            reset_state();
        }
    }

    return NULL;
}

void *prober(__attribute__((unused)) void *params)
{
    logg(LEVEL_INFO, "Started probing...");

    while (1)
    {
        double to_sleep = get_remaining_grace_period(&state);
        if (to_sleep > 0)
            sleep_(to_sleep);

        probe_next(&state);
        sleep_(1. * PROBE_PERIOD / 4.);

        // if no ack in PROBE_PERIOD / 4, request random peers to probe
        request_probes_if_no_ack(&state);
        sleep_(3. * PROBE_PERIOD / 4.);

        check_probed(&state);
    }

    return NULL;
}

void *gossiper(__attribute__((unused)) void *params)
{
    logg(LEVEL_INFO, "Started gossiping...");

    while (1)
    {
        double to_sleep = get_remaining_grace_period(&state);
        if (to_sleep > 0)
            sleep_(to_sleep);

        gossip_changes(&state);
        sleep(GOSSIP_PERIOD);
    }

    return NULL;
}
