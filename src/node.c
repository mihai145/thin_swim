#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <pthread.h>

#include "log.h"
#include "state.h"
#include "node_manager.h"


// STATE
extern struct node_state state;

// SIGNAL HANDLER
void sigint_handler(__attribute__((unused)) int signum)
{
    logg(LEVEL_FATAL, "Received SIGINT, stopping...");
    exit(0);
}

// --ports <TCP> <UDP>
void parse_ports(int argc, char **argv) {
    if (argc < 4 || strcmp(argv[1], "--ports") != 0) {
        puts("Failed to configure ports");
        puts("Usage for starting a network: ./node --ports <TCP> <UDP> --seed <TCP1> <UDP1> --seed <TCP2> <UDP2> ...");
        puts("Usage for joining a network: ./node --ports <TCP> <UDP> --join <TCP> <UDP>");
        exit(1);
    }

    int tcp_port = atoi(argv[2]);
    int udp_port = atoi(argv[3]);

    init_logger(tcp_port, udp_port);
    init_state(tcp_port, udp_port);
}

// To join a network: --join <TCP> <UDP>
// To start a network: --seed <TCP1> <UDP1> --seed <TCP2> <UDP2> ...
void parse_command(int argc, char **argv) {
    // node started in join mode
    if (strcmp(argv[4], "--join") == 0) {
        logg(LEVEL_INFO, "join network via node with TCP=%s UDP=%s", argv[5], argv[6]);
        join_network(atoi(argv[5]), atoi(argv[6]));
        return;
    }

    // node starts a network
    start_network(argc, argv);
}

int main(int argc, char **argv) {
    signal(SIGINT, sigint_handler);

    // retrieve own identity
    parse_ports(argc, argv);

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
        char *peers_repr = print_peers(&state);
        logg(LEVEL_INFO, "peers: %s", peers_repr);
        free(peers_repr);

        sleep(10);
    }

    return 0;
}
