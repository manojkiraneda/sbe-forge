#include "sbe/printf.h"

#include <stdarg.h>
#include <stddef.h>

/*
 * PPE42 output buffer address derived from the shared memory map:
 * This is the shared output address used by the legacy llvm-sbe hello app:
 *   0xFFF84000 + (0x400 * 16) = 0xFFF88000
 *
 * Total buffer size = 0x400 * 16 = 0x4000 (16 KiB).
 *
 * Each printf call writes at the current write offset, then advances it
 * to the next 8-byte (d-word) aligned offset so the next call starts on
 * a fresh aligned slot.
 */
#define OUTPUT_BUF_ADDR  0xFFF88000U
#define OUTPUT_BUF_SIZE  (0x400U * 16U)
#define DWORD_ALIGN      8U

struct output_buffer {
    volatile char *data;
    unsigned int size;
    unsigned int length;
};

/* Persistent byte offset into the output buffer. */
static unsigned int offset = 0U;

static void append_char(struct output_buffer *output, char value)
{
    if (output->length + 1U < output->size)
        output->data[output->length] = value;
    ++output->length;
}

static void append_string(struct output_buffer *output, const char *value)
{
    if (value == NULL)
        value = "(null)";

    while (*value != '\0')
        append_char(output, *value++);
}

static void append_unsigned(struct output_buffer *output, unsigned int value,
                            unsigned int base, int uppercase)
{
    const char *digits = uppercase ? "0123456789ABCDEF" : "0123456789abcdef";
    char reversed[sizeof(value) * 8U];
    unsigned int count = 0U;

    do {
        reversed[count++] = digits[value % base];
        value /= base;
    } while (value != 0U);

    while (count != 0U)
        append_char(output, reversed[--count]);
}

static void append_signed(struct output_buffer *output, int value)
{
    unsigned int magnitude = (unsigned int)value;

    if (value < 0) {
        append_char(output, '-');
        magnitude = 0U - magnitude;
    }

    append_unsigned(output, magnitude, 10U, 0);
}

int printf(const char *format, ...)
{
    volatile char *buffer = (volatile char *)OUTPUT_BUF_ADDR;
    struct output_buffer output = {
        buffer + offset,
        OUTPUT_BUF_SIZE - offset,
        0U,
    };
    va_list arguments;
    unsigned int bytes_used;

    va_start(arguments, format);
    while (*format != '\0') {
        char conversion;

        if (*format != '%') {
            append_char(&output, *format++);
            continue;
        }

        conversion = *++format;
        if (conversion == '\0') {
            append_char(&output, '%');
            break;
        }

        ++format;
        switch (conversion) {
        case '%':
            append_char(&output, '%');
            break;
        case 'c':
            append_char(&output, (char)va_arg(arguments, int));
            break;
        case 'd':
        case 'i':
            append_signed(&output, va_arg(arguments, int));
            break;
        case 's':
            append_string(&output, va_arg(arguments, const char *));
            break;
        case 'u':
            append_unsigned(&output, va_arg(arguments, unsigned int), 10U, 0);
            break;
        case 'x':
            append_unsigned(&output, va_arg(arguments, unsigned int), 16U, 0);
            break;
        case 'X':
            append_unsigned(&output, va_arg(arguments, unsigned int), 16U, 1);
            break;
        default:
            append_char(&output, '%');
            append_char(&output, conversion);
            break;
        }
    }
    va_end(arguments);

    /* Always terminate within the portion of the shared buffer still free. */
    output.data[output.length < output.size ? output.length : output.size - 1U] = '\0';

    bytes_used = output.length < output.size ? output.length + 1U : output.size;
    offset += bytes_used;
    offset = (offset + (DWORD_ALIGN - 1U)) & ~(DWORD_ALIGN - 1U);
    if (offset >= OUTPUT_BUF_SIZE)
        offset = 0U;

    return (int)output.length;
}
