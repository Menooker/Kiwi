#include <unistd.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    setuid(0);
    execv(KIWI_INSTALL_PATH "/housekeeper.py", argv);
    perror("execv:");
    return 0;
}