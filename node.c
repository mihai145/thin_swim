#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <pthread.h>

#include "util.h"
#include "state.h"
#include "node_manager.h"

int tcp_port = -1, udp_port = -1;
int lamport_time = 0;
struct node_state state;

void sigint_handler(__attribute__((unused)) int signum)
{
    if (is_logger_inited()) {
        logg(LEVEL_FATAL, "Received SIGINT, stopping...");
    } else {
        printf("Node %d - %d: Received SIGINT, stopping...\n", tcp_port, udp_port);
    }
    exit(0);
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
