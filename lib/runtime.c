#include <stdlib.h>
#include <stdio.h>
#include <string.h>

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

int readInt() {
    int x;
    scanf("%d", &x);
    return x;
}

char* readString() {
    char* line = NULL;
    size_t len = 0;
    size_t read;
    if ((read = getline(&line, &len, stdin)) != -1) {
        char* cleanedLine = (char*) malloc(len + 1);
        for (int i = 0; i < strlen(line); i++) {
            cleanedLine[i] = line[i];
        }
        cleanedLine[len - 1] = '\0';
        return cleanedLine;
    } else {
        error();
    }
}

char* concat(char* s1, char* s2) {
    int len1 = strlen(s1);
    int len2 = strlen(s2);
    int total_len = len1 + len2 + 1;
    char* t = (char*)malloc(total_len);
    strcpy(t, s1);
    strcat(t, s2);
    return t;
}