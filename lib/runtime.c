#include <stdlib.h>
#include <stdio.h>

void printInt(int x) {
    printf("%d\n", x);
}

void printString(char *str) {
    printf("%s\n", str);
}

void error() {
    puts("runtime error");
    exit(1);
}
