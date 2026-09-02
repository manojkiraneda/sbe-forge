#include <stdint.h>

#include "sbe/printf.h"

union words64 {
    uint64_t value;
    struct {
        uint32_t high;
        uint32_t low;
    } words;
};

static volatile uint32_t dividend32 = UINT32_C(0xfedcba98);
static volatile uint32_t divisor32 = UINT32_C(0x12345);
static volatile union words64 dividend64 = {
    .value = UINT64_C(0xfedcba9876543210),
};
static volatile union words64 divisor64 = {
    .value = UINT64_C(0x0000000000012345),
};

static volatile uint32_t quotient32;
static volatile uint32_t remainder32;
static volatile union words64 quotient64, remainder64;

int main(void)
{
    quotient32 = dividend32 / divisor32;
    remainder32 = dividend32 % divisor32;
    quotient64.value = dividend64.value / divisor64.value;
    remainder64.value = dividend64.value % divisor64.value;

    printf("32-bit udiv: quotient=0x%x remainder=0x%x\n",
           quotient32, remainder32);
    printf("64-bit udiv quotient: high=0x%x low=0x%x\n",
           quotient64.words.high, quotient64.words.low);
    printf("64-bit udiv remainder: high=0x%x low=0x%x",
           remainder64.words.high, remainder64.words.low);

    for (;;) {
        /* Bare-metal firmware has no environment to return to. */
    }
}
