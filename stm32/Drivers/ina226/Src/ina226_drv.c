
#include "string.h"
#include "ina226_drv.h"
#include "ina226_log.h"


enum INA226_Regs {
    ConfigReg          = 0x00,
    ShuntVoltageReg    = 0x1,
    BusVoltageReg      = 0x2,
    PowerReg           = 0x3,
    CurrentReg         = 0x4,
    CalibrationReg     = 0x5,
    MaskEnableReg      = 0x6,
    AlertLimitReg      = 0x7,
    ManIdReg           = 0xfe,
    DieIdReg           = 0xff,
};

enum AVG_Setting {
    NrAverages_1 = 0b000,
    NrAverages_4 = 0b001,
    NrAverages_16 = 0b010,
    NrAverages_64 = 0b011,
    NrAverages_128 = 0b100,
    NrAverages_256 = 0b101,
    NrAverages_512 = 0b110,
    NrAverages_1024 = 0b111,
};

enum VBUSCT_Setting {
    ConversionTime_140us = 0b000,
    ConversionTime_204us = 0b001,
    ConversionTime_332us = 0b010,
    ConversionTime_588us = 0b011,
    ConversionTime_1100us = 0b100,
    ConversionTime_2116us = 0b101,
    ConversionTime_4156us = 0b110,
    ConversionTime_8244us = 0b111,
};

enum MODE_Setting {
    PowerDown               = 0b000,
    ShuntVoltageTriggered   = 0b001,
    BusVoltageTriggered     = 0b010,
    ShuntAndBusTriggered    = 0b011,
    ShutDown                = 0b100,
    ShuntVoltageCont        = 0b101,
    BusVoltageCont          = 0b110,
    ShuntAndBusVoltageCont  = 0b111,
};

enum OpCodes {
    OpCodeRead = 0xfff0,
    OpCodeWrite = 0xfff1
};

extern int __I2C_readReg16 (uint8_t addr, uint16_t reg_addr, uint16_t *data);
extern int __I2C_writeReg16 (uint8_t addr, uint16_t reg_addr, uint16_t data);
extern int __sendUartData (void *buffer, uint16_t size);
extern int __recvUartData (void *buffer, uint16_t size);
extern void __waitUartReady();

void ina226_init (ina226_t *drv, uint8_t address) {
    drv->i2c_address = address;
}

static uint16_t ina226_sample_buffer[2] [1024];
static uint8_t ina226_sample_buffer_idx = 0;

static uint16_t Config_reg;
static uint8_t MODE_val;

void ina226_tick(ina226_t *drv) {
    uint16_t rword;
    uint8_t ack = 0xff;

    __recvUartData(&rword, 2);

    switch (rword) {
        case OpCodeRead: {
            uint16_t addr;
            uint16_t reg;

            __sendUartData(&ack, 1);
            __recvUartData(&addr, 2);
            __I2C_readReg16(drv->i2c_address, addr, &reg);
            __sendUartData(&reg, 2);
            break;
        }
        case OpCodeWrite: {
            uint16_t addr;
            uint16_t reg;
            __sendUartData(&ack, 1);
            __recvUartData(&addr, 2);
            __sendUartData(&ack, 1);
            __recvUartData(&reg, 2);
            __I2C_writeReg16(drv->i2c_address, addr, reg);

            if (addr == ConfigReg) {
                Config_reg = reg;
                MODE_val = reg & 0b111;
            }
            break;
        }
        default: {
            uint16_t pkt_length = rword;
            uint8_t triggered = (MODE_val & 0b100) == 0 && MODE_val != 0;
            for (int i = 0; i < pkt_length; i += 2) {
                uint16_t current_raw;
                uint16_t vbus_raw;

                if (triggered) {
                    uint8_t conv_ready = 0;
                    uint16_t reg;
                    __I2C_writeReg16(drv->i2c_address, ConfigReg, Config_reg);
                    while (! conv_ready) {
                        __I2C_readReg16(drv->i2c_address, MaskEnableReg, &reg);
                        conv_ready = reg & (1 << 3);
                    }
                    __I2C_readReg16(drv->i2c_address, CurrentReg, &current_raw);
                    __I2C_readReg16(drv->i2c_address, BusVoltageReg, &vbus_raw);

                } else {
                    __I2C_readReg16(drv->i2c_address, CurrentReg, &current_raw);
                    __I2C_readReg16(drv->i2c_address, BusVoltageReg, &vbus_raw);
                }

                ina226_sample_buffer[ina226_sample_buffer_idx][i] = current_raw;
                ina226_sample_buffer[ina226_sample_buffer_idx][i+1] = vbus_raw;
            }

            __waitUartReady();
            __sendUartData(ina226_sample_buffer[ina226_sample_buffer_idx], pkt_length * sizeof(uint16_t));
            ina226_sample_buffer_idx ^= 1;
            break;
        }
    }
}