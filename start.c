// Used to set up a network (forks seed nodes)
// Usage: start --seed <TCP1> <UDP1> --seed <TCP2> <UDP2> ...

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <signal.h>

pid_t *seed_pids;
void sigint_handler(__attribute__((unused)) int signum)
{
    puts("STARTER: Received SIGINT, propagating to all children...");

    for (int i = 0; i < (int)(sizeof(*seed_pids) / sizeof(pid_t)); i++)
    {
        kill(seed_pids[i], SIGINT);
    }

    puts("STARTER: Done propagating singal. Stopping...");
    exit(0);
}

int main(int argc, char **argv)
{
    signal(SIGINT, sigint_handler);

    if ((argc - 1) % 3 != 0)
    {
        puts("Failed to configure network");
        puts("Usage: ./start --seed <TCP1> <UDP1> --seed <TCP2> <UDP2> ...");
        exit(1);
    }

    int cnt_seeds = (argc - 1) / 3;
    printf("STARTER: Setting up %d seeds\n", cnt_seeds);

    seed_pids = (pid_t *)malloc(cnt_seeds * sizeof(pid_t));

    for (int i = 0; i < cnt_seeds; i++)
    {
        seed_pids[i] = fork();
        if (seed_pids[i] < 0)
        {
            printf("Falied to fork seed %d...\n", i);
        }
        else if (seed_pids[i] == 0)
        {
            char **args = malloc((1 + 3 * cnt_seeds + 1) * sizeof(char *));
            args[0] = strdup("node");
            args[1] = strdup("--ports");
            args[2] = strdup(argv[1 + 3 * i + 1]);
            args[3] = strdup(argv[1 + 3 * i + 2]);

            int ptr_args = 3;
            for (int j = 0; j < cnt_seeds; j++)
            {
                if (j != i)
                {
                    args[++ptr_args] = strdup("--seed");
                    args[++ptr_args] = strdup(argv[1 + 3 * j + 1]);
                    args[++ptr_args] = strdup(argv[1 + 3 * j + 2]);
                }
            }
            args[1 + 3 * cnt_seeds] = NULL;

            if (execv("node", args) == -1)
            {
                printf("FORKED: Failed to execv node %d...\n", i);
                exit(1);
            }
        }
    }

    while (1)
    {
        puts("STARTER: Alive...");
        sleep(10);
    }

    return 0;
}
