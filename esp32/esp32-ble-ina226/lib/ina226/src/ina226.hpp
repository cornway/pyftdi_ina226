#pragma once

#include "stdint.h"
#include "ring.hpp"

#define INA226_MAX_RX_PKTLEN (2048)
#define INA226_MAX_SAMPLEBUF_LEN (2048)

typedef void (*btSendCallback_t) (void *buf, size_t size);
typedef uint16_t (*i2cReadCallback_t) (uint8_t devAddr, uint16_t index);
typedef bool (*i2cWriteCallback_t) (uint8_t devAddr, uint16_t index, uint16_t value);

class Ina226 {
public:
    Ina226(size_t maxSamplesPerBatch);

    void registerCallbacks(btSendCallback_t btSend,
                            i2cReadCallback_t i2cRead,
                            i2cWriteCallback_t i2cWrite) {
        m_btSend = btSend;
        m_i2cRead = i2cRead;
        m_i2cWrite = i2cWrite;
    }

    void pushRxBuf(uint8_t c);

    void loop ();

private:
    uint16_t popWord();
    void ack();

    void i2cWrite(uint16_t index, uint16_t value);
    uint16_t i2cRead(uint16_t index);
    void sendBuffer(void *buf, size_t size);

    RingBuffer<char, INA226_MAX_RX_PKTLEN> m_ringRxBuffer;

    btSendCallback_t m_btSend;
    i2cReadCallback_t m_i2cRead;
    i2cWriteCallback_t m_i2cWrite;

    uint16_t m_sampleBuffer[2] [INA226_MAX_SAMPLEBUF_LEN];
    uint8_t m_sampleBufferidx;

    uint16_t m_configReg;
    uint8_t m_modeValue;

    uint8_t m_i2cAddress;

    size_t m_maxSamplesPerBatch;
};