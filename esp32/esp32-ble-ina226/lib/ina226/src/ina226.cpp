#include <HardwareSerial.h>

#include "ring.hpp"
#include "ina226.hpp"

RingBuffer<char, 2048> ringRxBuffer;

#define INA226_ADDRESS 0x40

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

template <typename T, size_t Size>
static uint16_t popWord (RingBuffer<T, Size> &ring) {
    uint8_t c[2];
    uint16_t ret;
    for (int i = 0; i < 2; i++) {
        c[i] = ring.pop();
    }
    ret = c[1] << 8 | c[0];
    return ret;
}

extern "C" void _btSend (const void *buf, size_t size);
extern "C" uint16_t _i2cRead (uint8_t devAddr, uint16_t index);
extern "C" bool _i2cWrite (uint8_t devAddr, uint16_t index, uint16_t value);

static uint16_t ina226_sample_buffer[2] [1024];
static uint8_t ina226_sample_buffer_idx = 0;

static uint16_t Config_reg;
static uint8_t MODE_val;

void Ina226::loop () {
    uint16_t op;
    uint8_t ack = 0xff;

    op = popWord(ringRxBuffer);

    char str[128];
    sprintf(str, "loop: %x", op);
    Serial.println(str);

    switch (op) {
        case OpCodeRead: {
            _btSend(&ack, 1);
            uint16_t addr = popWord(ringRxBuffer);
            uint16_t value = _i2cRead(INA226_ADDRESS, addr);
            _btSend(&value, 2);
            break;
        }
        case OpCodeWrite: {
            _btSend(&ack, 1);
            uint16_t addr = popWord(ringRxBuffer);
            _btSend(&ack, 1);
            uint16_t value = popWord(ringRxBuffer);
            _i2cWrite(INA226_ADDRESS, addr, value);

            if (addr == ConfigReg) {
                Config_reg = value;
                MODE_val = value & 0b111;
            }

            break;
        }
        default: {
            uint16_t pkt_length = op;
            uint8_t triggered = (MODE_val & 0b100) == 0 && MODE_val != 0;
            for (int i = 0; i < pkt_length; i += 2) {
                uint16_t current_raw;
                uint16_t vbus_raw;

                if (triggered) {
                    uint8_t conv_ready = 0;
                    uint16_t reg;
                    _i2cWrite(INA226_ADDRESS, ConfigReg, Config_reg);
                    while (! conv_ready) {
                        reg = _i2cRead(INA226_ADDRESS, MaskEnableReg);
                        conv_ready = reg & (1 << 3);
                    }
                    current_raw = _i2cRead(INA226_ADDRESS, CurrentReg);
                    vbus_raw = _i2cRead(INA226_ADDRESS, BusVoltageReg);

                } else {
                    current_raw = _i2cRead(INA226_ADDRESS, CurrentReg);
                    vbus_raw = _i2cRead(INA226_ADDRESS, BusVoltageReg);
                }


                ina226_sample_buffer[ina226_sample_buffer_idx][i] = current_raw;
                ina226_sample_buffer[ina226_sample_buffer_idx][i+1] = vbus_raw;
            }

            _btSend((uint8_t *)ina226_sample_buffer[ina226_sample_buffer_idx], pkt_length * sizeof(uint16_t));
            ina226_sample_buffer_idx ^= 1;
        }
    }
}