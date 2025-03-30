#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>

// Credit to GPT-4.5
int main() {
    int sock;
    struct sockaddr_in server;
    struct hostent *host;

    // Create socket
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == -1) {
        // Expected
        printf("Passed: Socket creation failed\n");
        return 0;
    }

    // Resolve hostname to IP address
    host = gethostbyname("google.com");
    if (host == NULL) {
        printf("Passed: google.com IP resolution failed\n");
        return 0;
    }

    server.sin_addr = *((struct in_addr *)host->h_addr);
    server.sin_family = AF_INET;
    server.sin_port = htons(80);

    // Connect to remote server
    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
        printf("Passed: Remote server connection failed\n");
        close(sock);
        return 0;
    }

    fprintf(stderr, "Failed: Connection to google.com succeeded\n");
    close(sock);
    return 1;
}