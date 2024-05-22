#include "time_utils.h"
#include "log.h"

int main()
{
    logg(LEVEL_INFO, "Sleeping for 5 seconds");
    sleep_(5);

    logg(LEVEL_INFO, "Sleeping for 2.5 seconds");
    sleep_(2.5);

    logg(LEVEL_INFO, "Sleeping for 1.25 seconds");
    sleep_(1.25);

    logg(LEVEL_INFO, "Sleeping for 0.625 seconds");
    sleep_(0.625);

    return 0;
}
