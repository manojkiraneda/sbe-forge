#include "sbe/format.h"

struct output_buffer {
    char *data;
    size_t size;
    size_t length;
};

static void append_char(struct output_buffer *output, char value)
{
    if (output->size != 0 && output->length + 1 < output->size)
        output->data[output->length] = value;
    ++output->length;
}

static void append_string(struct output_buffer *output, const char *value)
{
    if (value == NULL)
        value = "(null)";

    while (*value != '\0') {
        append_char(output, *value);
        ++value;
    }
}

static void append_unsigned(struct output_buffer *output, unsigned int value,
                            unsigned int base, int uppercase)
{
    const char *digits = uppercase ? "0123456789ABCDEF" : "0123456789abcdef";
    char reversed[sizeof(value) * 8];
    size_t count = 0;

    do {
        reversed[count++] = digits[value % base];
        value /= base;
    } while (value != 0);

    while (count != 0)
        append_char(output, reversed[--count]);
}

static void append_signed(struct output_buffer *output, int value)
{
    unsigned int magnitude = (unsigned int)value;

    if (value < 0) {
        append_char(output, '-');
        magnitude = 0U - magnitude;
    }

    append_unsigned(output, magnitude, 10, 0);
}

int sbe_vsnprintf(char *buffer, size_t size, const char *format, va_list arguments)
{
    struct output_buffer output = {buffer, size, 0};

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
            append_unsigned(&output, va_arg(arguments, unsigned int), 10, 0);
            break;
        case 'x':
            append_unsigned(&output, va_arg(arguments, unsigned int), 16, 0);
            break;
        case 'X':
            append_unsigned(&output, va_arg(arguments, unsigned int), 16, 1);
            break;
        default:
            append_char(&output, '%');
            append_char(&output, conversion);
            break;
        }
    }

    if (output.size != 0)
        output.data[output.length < output.size ? output.length : output.size - 1] = '\0';

    return (int)output.length;
}

int sbe_snprintf(char *buffer, size_t size, const char *format, ...)
{
    va_list arguments;
    int length;

    va_start(arguments, format);
    length = sbe_vsnprintf(buffer, size, format, arguments);
    va_end(arguments);

    return length;
}
