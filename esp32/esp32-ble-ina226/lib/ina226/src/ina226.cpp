#include <HardwareSerial.h>

#include "ina226.hpp"

RingBuffer<char, 2048> ringRxBuffer;

#define INA226_DEFAULT_ADDRESS 0x40

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
    OpCodeWrite = 0xfff1,
    OpCodeSetAddress = 0xfff2,
    OpCodeGetBufferLen = 0xfff3
};

Ina226::Ina226 () :
    m_sampleBufferidx(0),
    m_i2cAddress(INA226_DEFAULT_ADDRESS) {}

uint16_t Ina226::popWord () {
    uint8_t c[2];
    uint16_t ret;
    for (int i = 0; i < 2; i++) {
        c[i] = m_ringRxBuffer.pop();
    }
    ret = c[1] << 8 | c[0];
    return ret;
}

void Ina226::pushRxBuf (uint8_t c) {
    while (false == m_ringRxBuffer.push(c)) {}
}

void Ina226::ack() {
    uint8_t ack = 0xff;
    m_btSend(&ack, 1);
}

void Ina226::loop () {
    uint16_t op;

    op = popWord();

    switch (op) {
        case OpCodeRead: {
            ack();
            uint16_t addr = popWord();
            uint16_t value = m_i2cRead(m_i2cAddress, addr);
            m_btSend(&value, 2);
            break;
        }
        case OpCodeWrite: {
            ack();
            uint16_t addr = popWord();
            ack();
            uint16_t value = popWord();
            m_i2cWrite(m_i2cAddress, addr, value);

            if (addr == ConfigReg) {
                m_configReg = value;
                m_modeValue = value & 0b111;
            }

            break;
        }
        case OpCodeSetAddress: {
            ack();
            m_i2cAddress = m_ringRxBuffer.pop();
            break;
        }
        case OpCodeGetBufferLen: {
            uint16_t data = INA226_MAX_SAMPLEBUF_LEN;
            ack();
            m_btSend(&data, sizeof(data));
            break;
        }
        default: {
            uint16_t pkt_length = op;
            uint8_t triggered = (m_modeValue & 0b100) == 0 && m_modeValue != 0;
            for (int i = 0; i < pkt_length; i += 2) {
                uint16_t current_raw;
                uint16_t vbus_raw;

                if (triggered) {
                    uint8_t conv_ready = 0;
                    uint16_t reg;
                    m_i2cWrite(m_i2cAddress, ConfigReg, m_configReg);
                    while (! conv_ready) {
                        reg = m_i2cRead(m_i2cAddress, MaskEnableReg);
                        conv_ready = reg & (1 << 3);
                    }
                    current_raw = m_i2cRead(m_i2cAddress, CurrentReg);
                    vbus_raw = m_i2cRead(m_i2cAddress, BusVoltageReg);

                } else {
                    current_raw = m_i2cRead(m_i2cAddress, CurrentReg);
                    vbus_raw = m_i2cRead(m_i2cAddress, BusVoltageReg);
                }


                m_sampleBuffer[m_sampleBufferidx][i] = current_raw;
                m_sampleBuffer[m_sampleBufferidx][i+1] = vbus_raw;
            }

            m_btSend((uint8_t *)m_sampleBuffer[m_sampleBufferidx], pkt_length * sizeof(uint16_t));
            m_sampleBufferidx ^= 1;
        }
    }
}