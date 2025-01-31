
#include <stdio.h>
#include <stdarg.h>

#include "main.h"

#include "ina226_drv.h"

extern int __sendUartData (void *buffer, uint16_t size);

void _ina226_log (const char *format, ...) {
    char buffer[512];
    uint16_t size;
    va_list args;
    va_start(args, format);
    size = vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);

    __sendUartData(buffer, size);
}