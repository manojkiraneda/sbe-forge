#include <stdint.h>

#include "sbe/printf.h"

/* Volatile storage prevents the addition from being constant-folded. */
static volatile uint64_t lhs = UINT64_C(0x12345678fffffff0);
static volatile uint64_t rhs = UINT64_C(0x0000000000000035);
static volatile uint32_t mixed_lhs = UINT32_C(0xfffffff0);
static volatile union {
    uint64_t value;
    struct {
        uint32_t high;
        uint32_t low;
    } words;
} result, mixed_result;

int main(void)
{
    result.value = lhs + rhs;
    mixed_result.value = mixed_lhs + rhs;

    printf("64-bit add result: high=0x%x low=0x%x",
           result.words.high, result.words.low);
    printf("32-bit + 64-bit add: high=0x%x low=0x%x",
           mixed_result.words.high, mixed_result.words.low);

    for (;;) {
        /* Bare-metal firmware has no environment to return to. */
    }
}
