#include "sbe/printf.h"

#include <assert.h>
#include <string.h>

#define OUTPUT_BUF_SIZE 0x4000U

char sbe_test_output_buffer[OUTPUT_BUF_SIZE];

int main(void)
{
    char *buffer = sbe_test_output_buffer;

    assert(printf("Hello world") == 11);
    assert(strcmp(buffer, "Hello world") == 0);

    assert(printf("1 + 2 = %d", 1 + 2) == 9);
    assert(strcmp(buffer + 16, "1 + 2 = 3") == 0);

    assert(printf("%d %i %u", -42, (-2147483647 - 1), 4294967295U) == 26);
    assert(strcmp(buffer + 32, "-42 -2147483648 4294967295") == 0);

    assert(printf("%x %X %c %% %s", 0x1a2bU, 0x1a2bU, 'A', NULL) == 20);
    assert(strcmp(buffer + 64, "1a2b 1A2B A % (null)") == 0);

    return 0;
}
