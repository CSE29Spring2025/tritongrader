#include <stdlib.h>
#include <stdio.h>

int main() {
    int *ch = malloc(4);
    while ((*ch = getchar()) != EOF) {
        putchar(*ch);
    }
    return 0;
}
