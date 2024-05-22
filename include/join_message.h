#ifndef JOIN_MESSAGE_H
#define JOIN_MESSAGE_H

#define CAPACITY 100

struct join_request
{
    int tcp_port, udp_port;
};

struct join_reply
{
    int num_peers;

    int tcp_ports[CAPACITY];
    int udp_ports[CAPACITY];
};

#endif
