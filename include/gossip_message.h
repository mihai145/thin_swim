#ifndef GOSSIP_MESSAGE_H
#define GOSSIP_MESSAGE_H

#define CAPACITY 100

#define GOSSIP_UPDATE 0
#define PROBE 1
#define REQUEST_PROBE 2
#define ACK_PROBE 3
#define NOT_A_PEER 4

struct gossip_message
{
    int message_type;
    int cnt_updates;
    int tcp_ports[CAPACITY], udp_ports[CAPACITY], statuses[CAPACITY];

    // lamport time as for this message
    int node_name_tcp, node_name_udp, node_time;

    // if message type is REQUEST_PROBE
    int target_udp;
};

#endif
