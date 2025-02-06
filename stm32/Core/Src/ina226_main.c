
#include "stdint.h"
#include "main.h"
#include "ina226_log.h"
#include "ina226_drv.h"

extern UART_HandleTypeDef huart3;
extern I2C_HandleTypeDef hi2c1;

void set_led (uint32_t value) {
    if (value) {
        HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_SET);
    } else {
        HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);
    }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart) {
    //set_led(0);
}

int __I2C_readReg16 (uint8_t addr, uint16_t reg_addr, uint16_t *data) {

    uint8_t txdata[1];
    uint8_t rxdata[2];

    txdata[0] = reg_addr;
    HAL_I2C_Master_Transmit(&hi2c1, addr, txdata, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, addr|1, rxdata, 2, 100);
    *data = (rxdata[0] << 8) | rxdata[1];
    return 0;
}

int __I2C_writeReg16 (uint8_t addr, uint16_t reg_addr, uint16_t data) {

    uint8_t pdata[3];

    pdata[0] = reg_addr;
    pdata[1] = data >> 8;
    pdata[2] = data & 0xff;
    HAL_I2C_Master_Transmit(&hi2c1, addr, pdata, 3, 100);
    return 0;
}

void __waitUartReady() {
    while (huart3.gState != HAL_UART_STATE_READY) {}
}

int __sendUartData (void *buffer, uint16_t size) {
    while (HAL_BUSY == HAL_UART_Transmit_DMA(&huart3, (const uint8_t *)buffer, size)) {
    }
    return 0;
}

int __recvUartData (void *buffer, uint16_t size) {
    if (HAL_OK == HAL_UART_Receive(&huart3, buffer, size, HAL_MAX_DELAY)) {
        return 0;
    }
    return -1;
}

static ina226_t ina226_drv;

void ina_226_main (void) {

    HAL_Delay(10);

    ina226_init(&ina226_drv, 0x40 << 1);

    while (1) {
        ina226_tick(&ina226_drv);
    }

}
