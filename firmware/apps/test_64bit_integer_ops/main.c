#include <stdint.h>

#include "sbe/printf.h"

/* Volatile inputs ensure that every operation is performed at run time. */
static volatile uint64_t value = UINT64_C(0x92345678fffffff0);
static volatile uint64_t mask = UINT64_C(0x0ff00ff0f0f0f0f0);
static volatile int64_t signed_value = -INT64_C(0x123456789abcdef);
static volatile uint32_t shift = 7;

static volatile union result_words {
    uint64_t value;
    struct {
        uint32_t high;
        uint32_t low;
    } words;
} negation, shift_left, logical_shift_right, arithmetic_shift_right,
    variable_shift_left, variable_shift_right, bitwise_and, bitwise_or,
    bitwise_xor, bitwise_not;

static void print_result(const char *operation,
                         const volatile union result_words *result)
{
    printf("64-bit %s: high=0x%x low=0x%x\n", operation,
           result->words.high, result->words.low);
}

int main(void)
{
    negation.value = (uint64_t)-signed_value;

    shift_left.value = value << 3;
    logical_shift_right.value = value >> 3;
    arithmetic_shift_right.value = (uint64_t)(signed_value >> 3);
    variable_shift_left.value = value << shift;
    variable_shift_right.value = value >> shift;

    bitwise_and.value = value & mask;
    bitwise_or.value = value | mask;
    bitwise_xor.value = value ^ mask;
    bitwise_not.value = ~value;

    print_result("neg", &negation);
    print_result("shl3", &shift_left);
    print_result("lshr3", &logical_shift_right);
    print_result("ashr3", &arithmetic_shift_right);
    print_result("shl-var", &variable_shift_left);
    print_result("lshr-var", &variable_shift_right);
    print_result("and", &bitwise_and);
    print_result("or", &bitwise_or);
    print_result("xor", &bitwise_xor);
    print_result("not", &bitwise_not);

    for (;;) {
        /* Bare-metal firmware has no environment to return to. */
    }
}
