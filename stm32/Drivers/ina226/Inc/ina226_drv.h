#ifndef __INA_226_DRV_H__
#define __INA_226_DRV_H__

#include <stdint.h>

typedef struct {
    uint8_t i2c_address;
    float currentLSB;
} ina226_t;

void ina226_init (ina226_t *drv, uint8_t address);
void ina226_tick(ina226_t *drv);

#endif