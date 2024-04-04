#include <stdio.h>
#include "log.h"


int main() {
    init_logger(8080, 12001);

    logg(LEVEL_INFO, "%d + %d = %d is %s", 10, 20, 30, "correct");
    logg(LEVEL_DBG, "This node is having trouble...");
    logg(LEVEL_FATAL, "%s in %d seconds...", "Shutting down", 10);
    logg(LEVEL_PEERS, "My peers are awesome");

    puts("This is a plain puts");
    printf("This is a plain printf with integer %d and string %s\n", -10, "Hello!");

    logg(LEVEL_INFO, "Test done!");

    return 0;
}
