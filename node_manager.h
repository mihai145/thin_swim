#ifndef NODE_MANAGER_H
#define NODE_MANAGER_H

void *tcp_port_listener(__attribute__((unused)) void *params);

void *udp_port_listener(__attribute__((unused)) void *params);

void *prober(__attribute__((unused)) void *params);

void *gossiper(__attribute__((unused)) void *params);

void join_network(int tcp_gateway, __attribute__((unused)) int udp_gateway);

#endif
