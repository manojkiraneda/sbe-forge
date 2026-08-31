#include "sbe/format.h"

#include <assert.h>
#include <limits.h>
#include <stdarg.h>
#include <string.h>

static int call_vsnprintf(char *buffer, size_t size, const char *format, ...)
{
    va_list arguments;
    int length;

    va_start(arguments, format);
    length = sbe_vsnprintf(buffer, size, format, arguments);
    va_end(arguments);
    return length;
}

int main(void)
{
    char buffer[128];
    char truncated[8];

    assert(sbe_snprintf(buffer, sizeof(buffer), "Hello %s", "world") == 11);
    assert(strcmp(buffer, "Hello world") == 0);

    assert(sbe_snprintf(buffer, sizeof(buffer), "%d %i %u", -42, INT_MIN,
                        4294967295U) == 26);
    assert(strcmp(buffer, "-42 -2147483648 4294967295") == 0);

    assert(sbe_snprintf(buffer, sizeof(buffer), "%x %X", 0x1a2bU, 0x1a2bU) == 9);
    assert(strcmp(buffer, "1a2b 1A2B") == 0);

    assert(sbe_snprintf(buffer, sizeof(buffer), "%c %% %s", 'A', NULL) == 10);
    assert(strcmp(buffer, "A % (null)") == 0);

    assert(sbe_snprintf(truncated, sizeof(truncated), "number=%d", 12345) == 12);
    assert(strcmp(truncated, "number=") == 0);

    assert(sbe_snprintf(NULL, 0, "%s:%u", "size", 17U) == 7);

    assert(call_vsnprintf(buffer, sizeof(buffer), "%d/%s", 7, "seven") == 7);
    assert(strcmp(buffer, "7/seven") == 0);

    assert(sbe_snprintf(buffer, sizeof(buffer), "unknown=%q") == 10);
    assert(strcmp(buffer, "unknown=%q") == 0);

    return 0;
}
