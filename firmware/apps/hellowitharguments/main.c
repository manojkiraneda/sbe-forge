#include "sbe/printf.h"

#define TEST_REGISTER ((volatile unsigned long long *)0x50009u)

int main(void)
{
    printf("1 + 2 = %d", 1 + 2);
    printf("4 * 10 = %d", 4 * 10);
    printf("20 - 7 = %d", 20 - 7);
    printf("(3 + 4) * 5 = %d", (3 + 4) * 5);

    *TEST_REGISTER |= 1ULL;
    while (1) {
        /* Infinite loop. */
    }

    return 0;
}
