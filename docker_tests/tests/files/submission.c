#include <stdio.h>

int main() {
    char const * filenames[] = {
        "/autograder/results/results.json",
        "/autograder/source/setup.sh",
        "/autograder/run_autograder",
    };
    for (int i = 0; i < 3; ++i) {
        FILE *file = fopen(filenames[i], "r");
        if (file != NULL) {
            fprintf(stderr, "Did not expect to be able to open %s!\n", filenames[i]);
            fclose(file);
            return 1;
        } else {
            printf("Nice! Failed to open %s\n", filenames[i]);
        }
        file = fopen(filenames[i], "w");
        if (file != NULL) {
            fprintf(stderr, "Did not expect to be able to open %s!\n", filenames[i]);
            fclose(file);
            return 1;
        }
    }
    return 0;
}
