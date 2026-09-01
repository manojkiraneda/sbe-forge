#include "sbe/printf.h"

int main(void)
{
    printf("1 + 2 = %d", 1 + 2);
    printf("4 * 10 = %d", 4 * 10);
    printf("20 - 7 = %d", 20 - 7);
    printf("(3 + 4) * 5 = %d", (3 + 4) * 5);

    while (1) {
        /* Infinite loop. */
    }

    return 0;
}
