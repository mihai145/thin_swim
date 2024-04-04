#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <stdarg.h>
#include <string.h>

#include "log.h"


int log_tcp_port, log_udp_port;
FILE* f;

void init_logger(int tcp_port_, int udp_port_) {
    log_tcp_port = tcp_port_;
    log_udp_port = udp_port_;

    char log_filename[20];
    sprintf(log_filename, "%d_%d.log", tcp_port_, udp_port_);
    f = fopen(log_filename, "a");
}

void cleanup_logger() {
    fclose(f);
}

void set_color(const char* level, char* log, char* msg) {
    if (strcmp(level, LEVEL_INFO) == 0) {
        sprintf(log, COLORED_LOG_FORMAT, COLOR_INFO, msg, COLOR_RESET);
    } else if (strcmp(level, LEVEL_DBG) == 0) {
        sprintf(log, COLORED_LOG_FORMAT, COLOR_DBG, msg, COLOR_RESET);
    } else if (strcmp(level, LEVEL_FATAL) == 0) {
        sprintf(log, COLORED_LOG_FORMAT, COLOR_FATAL, msg, COLOR_RESET);
    } else if (strcmp(level, LEVEL_PEERS) == 0) {
        sprintf(log, COLORED_LOG_FORMAT, COLOR_PEERS, msg, COLOR_RESET);
    }
}

void unset_color() {
    printf("\033[0m");
}

void logg(const char* level, const char* fmt, ...) {
#ifdef LOGS_SUCCINT
    if (strcmp(level, LEVEL_DBG) == 0) {
        return;
    }
#endif

#ifdef STRESS_TEST
    if (strcmp(level, LEVEL_PEERS) != 0) {
        return;
    }
#endif

    // get current time
    struct timespec tp;
    clock_gettime(CLOCK_MONOTONIC, &tp);

    char *p = NULL;
    va_list ap;
    va_start(ap, fmt);

    // Calculate size for message
    int n = vsnprintf(p, 0, fmt, ap);
    va_end(ap);

    // Write message
    p = (char*)malloc(n + 1);
    va_start(ap, fmt);
    vsnprintf(p, n+1, fmt, ap);
    va_end(ap);

    // Calculate size for preffix
    char *prefix = NULL;
    int m = snprintf(prefix, 0, PREFIX_FORMAT, level, tp.tv_sec, tp.tv_nsec, log_tcp_port, log_udp_port);

    // Write preffix
    prefix = (char*)malloc(m + n + 1);
    snprintf(prefix, m+1, PREFIX_FORMAT, level, tp.tv_sec, tp.tv_nsec, log_tcp_port, log_udp_port);

    // Concatenate message to prefix
    strcat(prefix, p);

    char *log = malloc(m + n + 1 + 2 * 6);

    set_color(level, log, prefix);
    puts(log);
    fputs(log, f);
    fputs("\n", f);

    free(p);
    free(prefix);
    free(log);
}
