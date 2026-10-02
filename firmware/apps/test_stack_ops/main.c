/* Check compiler-generated PPE42 stack frame instructions in this function's
 * disassembly. It calls another function and uses the result afterward, so
 * the call cannot be converted into a tail call. The inline assembly clobber
 * makes LLVM preserve R30, allowing us to check its stack instruction policy.
 */
__attribute__((noinline, used))
unsigned ppe42_stack_outer(unsigned value);

__attribute__((noinline, used))
unsigned ppe42_stack_inner(unsigned value)
{
    return value + 1;
}

unsigned ppe42_stack_outer(unsigned value)
{
    __asm__ volatile("" ::: "r30");
    unsigned result = ppe42_stack_inner(value);
    return result + 7;
}

__attribute__((noinline, used))
unsigned ppe42_stack_plain(unsigned value)
{
    unsigned result = ppe42_stack_inner(value);
    return result + 8;
}

static volatile unsigned probe_input = 7;

int main(void)
{
    volatile unsigned *const output = (volatile unsigned *)0xFFF88000u;
    unsigned value = probe_input;
    output[0] = ppe42_stack_outer(value);
    output[1] = ppe42_stack_plain(value);
    for (;;)
    {
    }
}
