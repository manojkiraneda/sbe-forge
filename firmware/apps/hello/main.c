#include "sbe/printf.h"

#define TEST_REGISTER ((volatile unsigned long long *)0x50009u)

int main(void)
{
    printf("Hello world");
    *TEST_REGISTER |= 1ULL;
    while (1)
    {
        // Infinite loop
    }
    return 0;
}
