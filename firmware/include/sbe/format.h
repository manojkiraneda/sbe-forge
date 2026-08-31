#ifndef SBE_FORMAT_H
#define SBE_FORMAT_H

#include <stdarg.h>
#include <stddef.h>

int sbe_vsnprintf(char *buffer, size_t size, const char *format, va_list arguments);
int sbe_snprintf(char *buffer, size_t size, const char *format, ...);

#endif
