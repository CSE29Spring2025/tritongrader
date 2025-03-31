#include <stdio.h>
#include <unistd.h>

int main() {
    if (getuid() == 0 || geteuid() == 0) {
        fprintf(stderr, "Failed: Submission executed as root!\n");
        return 1;
    }
    printf("Passed: Program executed as UID %u\n", getuid());
}