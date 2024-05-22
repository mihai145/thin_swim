#ifndef LOG_H
#define LOG_H

#define LEVEL_FATAL "FATAL"
#define LEVEL_INFO " INFO"
#define LEVEL_DBG "DEBUG"
#define LEVEL_PEERS "PEERS"

#define COLOR_INFO "\033[0;36m"
#define COLOR_DBG "\033[0;33m"
#define COLOR_FATAL "\033[0;31m"
#define COLOR_RESET "\033[0m"
#define COLOR_PEERS "\033[0;35m"

#define PREFIX_FORMAT "[%s   %ld:%ld   Node %d-%d]: "
#define COLORED_LOG_FORMAT "%s%s%s"

void init_logger(int tcp_port_, int udp_port_);

void cleanup_logger();

void logg(const char *level, const char *fmt, ...);

#endif
