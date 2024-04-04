#include <time.h>
#include <errno.h>
#include "time_utils.h"


void sleep_(double s) {
    time_t seconds = (int)s;
    long nano_seconds = (long)((s - (int)s) * 1e9);

    if (seconds < 0) seconds = 0;
    if (nano_seconds < 0) nano_seconds = 0;

    struct timespec req;
    req.tv_sec = seconds;
    req.tv_nsec = nano_seconds;

    int ret = 0;
    do {
        ret = nanosleep(&req, &req);
    } while (ret == -1 && errno == EINTR);
}
