#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <pthread.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "util.h"
#include "state.h"
#include "join_message.h"
#include "gossip_message.h"

#define GRACE_PERIOD 3
#define GOSSIP_PERIOD 1
#define PROBE_PERIOD 1

int tcp_port = -1, udp_port = -1;
struct node_state state;

int lamport_time = 0;

void sigint_handler(__attribute__((unused)) int signum)
{
    if (is_logger_inited()) {
        logg(LEVEL_FATAL, "Received SIGINT, stopping...");
    } else {
        printf("Node %d - %d: Received SIGINT, stopping...\n", tcp_port, udp_port);
    }
    exit(0);
}

void *tcp_port_listener(__attribute__((unused)) void *params) {
    int fd_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (fd_socket < 0) {
        logg(LEVEL_FATAL, "Failed to create TCP port");
        exit(1);
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(tcp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(fd_socket, (const struct sockaddr*) &server_addr, sizeof(server_addr)) < 0) {
        logg(LEVEL_FATAL, "Failed to bind socket to desired port");
        exit(1);
    }

    if (listen(fd_socket, 50) < 0) {
        logg(LEVEL_FATAL, "Failed to start listening to desired port");
        exit(1);
    } else {
        logg(LEVEL_INFO, "Listening on TCP port %d", tcp_port);
    }

    while (1) {
        struct sockaddr_in client_addr;
        memset(&client_addr, 0, sizeof(client_addr));
        socklen_t client_socklen = sizeof(client_addr);
        int client_socket = accept(fd_socket, (struct sockaddr*)&client_addr, &client_socklen);
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
        if (recv(client_socket, &recv_msg, sizeof(recv_msg), 0) < 0) {
            logg(LEVEL_DBG, "Could not receive join request. Resuming listening...");
            continue;
        }
        logg(LEVEL_DBG, "Received join request from %d-%d", recv_msg.tcp_port, recv_msg.udp_port);

        // reply with join reply
        struct join_reply snd_msg;
        memset(&snd_msg, 0, sizeof(snd_msg));

        snd_msg.num_peers = state.num_peers + 1;
        memcpy(snd_msg.tcp_ports, state.tcp_ports, sizeof(int) * state.num_peers);
        memcpy(snd_msg.udp_ports, state.udp_ports, sizeof(int) * state.num_peers);
        snd_msg.tcp_ports[state.num_peers] = tcp_port;
        snd_msg.udp_ports[state.num_peers] = udp_port;

        if (send(client_socket, &snd_msg, sizeof(snd_msg), 0) < 0) {
            logg(LEVEL_DBG, "Error occured while sending join reply. Resume listening...");
            continue;
        } else
            logg(LEVEL_DBG, "Sent join reply successfully");

        close(client_socket);
        if (append_member(&state, recv_msg.tcp_port, recv_msg.udp_port) == -1) {
            logg(LEVEL_FATAL, "State capacity reached, failed to append member");
            exit(1);
        }

        append_broadcast(&state, recv_msg.tcp_port, recv_msg.udp_port, 1);
    }

    return NULL;
}

void *udp_port_listener(__attribute__((unused)) void *params) {
    int fd_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_socket < 0) {
        logg(LEVEL_FATAL, "Failed to create UDP socket");
        exit(1);
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(udp_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(fd_socket, (const struct sockaddr*) &server_addr, sizeof(server_addr)) < 0) {
        logg(LEVEL_FATAL, "Failed to bind UDP socket");
        exit(1);
    }

    while (1) {
        struct gossip_message recv_msg;
        memset(&recv_msg, 0, sizeof(recv_msg));

        if (recv(fd_socket, &recv_msg, sizeof(recv_msg), 0) < 0) {
            logg(LEVEL_DBG, "Error occured while receiving UDP message. Resuming listening...");
            continue;
        }

        if (recv_msg.message_type == GOSSIP_UPDATE) {
            logg(LEVEL_DBG, "Received %d changes via gossip", recv_msg.cnt_updates);
            process_updates(&state, &recv_msg);
        }
        if (recv_msg.message_type == PROBE) {
            logg(LEVEL_DBG, "Probed by %d. Sending reply...", recv_msg.node_name_udp);
            reply_probe(&state, recv_msg.node_name_udp);
        }
        if (recv_msg.message_type == ACK_PROBE) {
            // check ack
            check_ack(&state, recv_msg.node_name_udp);
        }
    }

    return NULL;
}

void *prober(__attribute__((unused)) void *params) {
    sleep(GRACE_PERIOD);

    logg(LEVEL_INFO, "Started probing...");

    while (1) {
        // printf("Node %d-%d: probing...\n", tcp_port, udp_port);
        probe_next(&state);
        sleep(PROBE_PERIOD);
        check_probed(&state);
    }

    return NULL;
}

void *gossiper(__attribute__((unused)) void *params) {
    sleep(GRACE_PERIOD);

    logg(LEVEL_INFO, "Started gossiping...");

    while (1) {
        // printf("Node %d-%d: gossiping...\n", tcp_port, udp_port);
        gossip_changes(&state, tcp_port, lamport_time);
        sleep(GOSSIP_PERIOD);
    }

    return NULL;
}

void join_network(int tcp_gateway, __attribute__((unused)) int udp_gateway) {
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(tcp_gateway);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    int fd_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (fd_socket < 0) {
        logg(LEVEL_FATAL, "Failed to create TCP socket");
        exit(1);
    }
    if (connect(fd_socket, (const struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        logg(LEVEL_FATAL, "Error connecting to server TCP gateway socket");
        exit(1);
    }

    // send join request
    struct join_request snd_msg;
    memset(&snd_msg, 0, sizeof(snd_msg));
    snd_msg.tcp_port = tcp_port;
    snd_msg.udp_port = udp_port;

    if (send(fd_socket, &snd_msg, sizeof(snd_msg), 0) < 0) {
        logg(LEVEL_FATAL, "Error occured while sending TCP message");
        exit(1);
    }

    // wait for join reply
    struct join_reply recv_msg;
    memset(&recv_msg, 0, sizeof(recv_msg));
    if (recv(fd_socket, &recv_msg, sizeof(recv_msg), 0) < 0) {
        logg(LEVEL_FATAL, "Did not receive join reply");
        exit(1);
    }

    logg(LEVEL_INFO, "Received join reply, discovered network with %d peers", recv_msg.num_peers);

    close(fd_socket);
    populate_peers(&state, recv_msg.num_peers, recv_msg.tcp_ports, recv_msg.udp_ports);
}

void parse_ports(int argc, char **argv) {
    if (argc < 4 || strcmp(argv[1], "--ports") != 0) {
        puts("Failed to configure ports");
        puts("Usage for starting a network: ./node --ports <TCP> <UDP> --seed <TCP1> <UDP1> --seed <TCP2> <UDP2> ...");
        puts("Usage for joining a network: ./node --ports <TCP> <UDP> --join <TCP> <UDP>");
        exit(1);
    }

    tcp_port = atoi(argv[2]);
    udp_port = atoi(argv[3]);

    init_logger(tcp_port, udp_port);
}

void parse_command(int argc, char **argv) {
    // node started in join mode
    if (strcmp(argv[4], "--join") == 0) {
        logg(LEVEL_INFO, "join network via node with TCP=%s UDP=%s", argv[5], argv[6]);
        join_network(atoi(argv[5]), atoi(argv[6]));
        return;
    }

    // node started in network mode
    int num_seeds = (argc - 4) / 3;
    int *tcp_ports = malloc(num_seeds * sizeof(int));
    int *udp_ports = malloc(num_seeds * sizeof(int));

    for (int i = 0; i < num_seeds; i++) {
        tcp_ports[i] = atoi(argv[4 + 3*i + 1]);
        udp_ports[i] = atoi(argv[4 + 3*i + 2]);
    }

    populate_peers(&state, num_seeds, tcp_ports, udp_ports);
    free(tcp_ports);
    free(udp_ports);

    for (int i = 0; i < state.num_peers; i++) {
        logg(LEVEL_DBG, "%dth seed has TCP=%d, UDP=%d", i+1, state.tcp_ports[i], state.udp_ports[i]);
    }
}

int main(int argc, char **argv) {
    signal(SIGINT, sigint_handler);

    // retrieve own identity
    parse_ports(argc, argv);
    state.own_tcp_port = tcp_port;
    state.own_udp_port = udp_port;

    // start a new network or join an existing network
    parse_command(argc, argv);

    // start tcp and udp listener threads
    pthread_t tcp_listener_thread, udp_listener_thread;
    if (pthread_create(&tcp_listener_thread, NULL, tcp_port_listener, NULL) != 0) {
        logg(LEVEL_FATAL, "Failed to create TCP listener thread. Exiting...");
        exit(1);
    }
    if (pthread_create(&udp_listener_thread, NULL, udp_port_listener, NULL) != 0) {
        logg(LEVEL_FATAL, "Failed to create UDP listener thread. Exiting...");
        exit(1);
    }

    // start probing thread
    pthread_t prober_thread;
    if (pthread_create(&prober_thread, NULL, prober, NULL) != 0) {
        logg(LEVEL_FATAL, "Failed to create prober thread. Exiting...");
        exit(1);
    }

    // start gossiper thread
    pthread_t gossiper_thread;
    if (pthread_create(&gossiper_thread, NULL, gossiper, NULL) != 0) {
        logg(LEVEL_FATAL, "Failed to create gossiper thread. Exiting...");
        exit(1);
    }

    // node running...
    while (1) {
        // printf("Node %d-%d: Alive...\n", tcp_port, udp_port);
        char *peers_repr = print_peers(&state);
        logg(LEVEL_INFO, "peers: %s", peers_repr);
        free(peers_repr);

        sleep(10);
    }

    return 0;
}
