#include <stdlib.h>
#include <stdio.h>

int main() {
    int *ch = malloc(4);
    while ((*ch = getchar()) != EOF) {
        putchar(*ch);
    }
    free(ch);
    return 0;
}
