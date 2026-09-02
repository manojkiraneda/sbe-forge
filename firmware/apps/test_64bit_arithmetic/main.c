#include <stdint.h>

#include "sbe/printf.h"

/* Volatile operands prevent the arithmetic from being constant-folded. */
static volatile uint64_t lhs = UINT64_C(0x12345678fffffff0);
static volatile uint64_t rhs = UINT64_C(0x0000000000000035);
static volatile uint32_t mixed_lhs = UINT32_C(0xfffffff0);
static volatile uint32_t overflow32_lhs = UINT32_C(0xfffffff0);
static volatile uint32_t overflow32_rhs = UINT32_C(0x00000020);
static volatile uint64_t overflow64_lhs = UINT64_C(0xfffffffffffffff0);
static volatile uint64_t overflow64_rhs = UINT64_C(0x0000000000000020);
static volatile uint32_t multiplication32_overflow;

static volatile union result_words {
    uint64_t value;
    struct {
        uint32_t high;
        uint32_t low;
    } words;
} addition, mixed_addition, subtraction, multiplication64_overflow;

int main(void)
{
    addition.value = lhs + rhs;
    mixed_addition.value = mixed_lhs + rhs;
    subtraction.value = lhs - rhs;
    /* Unsigned overflow is defined modulo 2^N: both results end in fffffe00. */
    multiplication32_overflow = overflow32_lhs * overflow32_rhs;
    multiplication64_overflow.value = overflow64_lhs * overflow64_rhs;

    printf("64-bit add: high=0x%x low=0x%x\n",
           addition.words.high, addition.words.low);
    printf("32-bit + 64-bit add: high=0x%x low=0x%x\n",
           mixed_addition.words.high, mixed_addition.words.low);
    printf("64-bit sub: high=0x%x low=0x%x\n",
           subtraction.words.high, subtraction.words.low);
    printf("32-bit overflowing mul: result=0x%x\n",
           multiplication32_overflow);
    printf("64-bit overflowing mul: high=0x%x low=0x%x",
           multiplication64_overflow.words.high,
           multiplication64_overflow.words.low);

    for (;;) {
        /* Bare-metal firmware has no environment to return to. */
    }
}
