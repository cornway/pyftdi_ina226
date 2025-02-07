#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Wire.h>
#include <HardwareSerial.h>
#include "ring.hpp"
#include "ina226.hpp"

#define SERVICE_UUID        "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_RX   "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_TX   "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
#define DEVICE_NAME         "esp32_ina226_uart"

BLECharacteristic *pTxCharacteristic;
bool deviceConnected = false;
Ina226 *ina226;

class MyServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { deviceConnected = true; Serial.println("connected"); }
    void onDisconnect(BLEServer* pServer) { deviceConnected = false; Serial.println("disconnected"); }
};

class MyCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        auto receivedData = pCharacteristic->getValue();
        if (receivedData.length() > 0) {
            const uint8_t *buf = (const uint8_t *)receivedData.c_str();
            for (int i = 0; i < receivedData.length(); i++) {
                ina226->pushRxBuf(buf[i]);
            }
        }
    }
};

void _btSend (void *buf, size_t size) {
    pTxCharacteristic->setValue((uint8_t *)buf, size);
    pTxCharacteristic->notify();
}

uint16_t _i2cRead (uint8_t devAddr, uint16_t index) {
    uint16_t value;
    Wire.beginTransmission(devAddr);
    Wire.write(index);
    Wire.endTransmission(false);

    Wire.requestFrom(devAddr, (uint8_t)2);
    if (Wire.available() < 2) {
        Serial.println("Error: Not enough data received");
        return 0;
    }

    value = (Wire.read() << 8) | Wire.read();
    return value;
}

bool _i2cWrite (uint8_t devAddr, uint16_t index, uint16_t value) {
    Wire.beginTransmission(devAddr);
    Wire.write(index);
    Wire.write(value >> 8);
    Wire.write(value & 0xFF);
    if (Wire.endTransmission() != 0) {
        Serial.println("Error: Transmission failed");
        return false;
    }
    return true;
}

void setup() {

    ina226 = new Ina226();
    ina226->registerCallbacks(_btSend, _i2cRead, _i2cWrite);

    Wire.begin();
    Wire.setClock(400000);
    Serial.begin(115200);
    BLEDevice::init(DEVICE_NAME);

    BLEServer *pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    BLEService *pService = pServer->createService(SERVICE_UUID);

    pTxCharacteristic = pService->createCharacteristic(
                        CHARACTERISTIC_TX, BLECharacteristic::PROPERTY_NOTIFY);
    pTxCharacteristic->addDescriptor(new BLE2902());

    BLECharacteristic *pRxCharacteristic = pService->createCharacteristic(
                        CHARACTERISTIC_RX, BLECharacteristic::PROPERTY_WRITE);
    pRxCharacteristic->setCallbacks(new MyCallbacks());

    pService->start();
    pServer->getAdvertising()->start();
    Serial.println("BLE UART Ready");
}

void loop() {
    if (deviceConnected) {
        ina226->loop();
    }
}
