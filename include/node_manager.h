#ifndef NODE_MANAGER_H
#define NODE_MANAGER_H


extern struct node_state state;

void init_state(int tcp_port, int udp_port);

void join_network(int tcp_gateway, __attribute__((unused)) int udp_gateway);

void *tcp_port_listener(__attribute__((unused)) void *params);

void *udp_port_listener(__attribute__((unused)) void *params);

void *prober(__attribute__((unused)) void *params);

void *gossiper(__attribute__((unused)) void *params);

#endif
