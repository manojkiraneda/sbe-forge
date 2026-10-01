/* Check compiler-generated PPE42 stack frame instructions in this function's
 * disassembly. It calls another function and uses the result afterward, so
 * the call cannot be converted into a tail call. It has no local stack slots.
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
    unsigned result = ppe42_stack_inner(value);
    return result + 7;
}

static volatile unsigned probe_input = 7;

int main(void)
{
    volatile unsigned *const output = (volatile unsigned *)0xFFF88000u;
    *output = ppe42_stack_outer(probe_input);
    for (;;)
    {
    }
}
