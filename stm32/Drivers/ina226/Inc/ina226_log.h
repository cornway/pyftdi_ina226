#ifndef __INA_226_H__
#define __INA_226_H__

void _ina226_log (const char *format, ...);

#define ina226_log(fmt, ...) _ina226_log(fmt"\r\n", ##__VA_ARGS__)

#endif /*__INA_226_H__*/