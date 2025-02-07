import asyncio
from collections import deque
from bleak import BleakClient, BleakScanner
import numpy as np
from enum import IntEnum
import threading

from ina226_if import INA226_ll

UART_TX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
TARGET_DEVICE_NAME = 'esp32_ina226_uart'

def start_async_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def uart_ble(rxbuf: deque, txbuf: deque, targetDeviceName):

    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()

    # Look for the device with the matching name
    target_device = None
    for device in devices:
        if device.name == targetDeviceName:
            target_device = device
            break

    if target_device is None:
        print(f"Device with name '{targetDeviceName}' not found.")
        return

    print(f"Found device: {target_device.name}, Address: {target_device.address}")
    print("Connecting...")

    async with BleakClient(target_device.address) as client:
        print(f"Connected to {target_device.address}")

        def notification_handler(sender, data):
            rxbuf.extend(data)

        await client.start_notify(UART_RX_UUID, notification_handler)

        try:
            while True:
                await asyncio.sleep(0.01)
                if len(txbuf):
                    await client.write_gatt_char(UART_TX_UUID, txbuf)
                    txbuf.clear()

        except KeyboardInterrupt:
            print("Keyboard interrupt received, stopping notifications...")
        finally:
            await client.stop_notify(UART_RX_UUID)
            print("Disconnected.")

class INA226_Bt(INA226_ll):
    byteorder = 'little'
    MaxPktLen = 2048

    def __init__(self):
        self.rxbuf = deque(maxlen=self.MaxPktLen)
        self.txbuf = deque(maxlen=self.MaxPktLen)

        self.async_loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=start_async_loop, args=(self.async_loop,), daemon=True)
        self.thread.start()

        self.future = asyncio.run_coroutine_threadsafe(uart_ble(self.rxbuf, self.txbuf, TARGET_DEVICE_NAME), self.async_loop)

    def sendBytes(self, bytes):
        self.txbuf.extend(bytes)

    def recvBytes(self, nr_bytes):
        while len(self.rxbuf) < nr_bytes:
            pass
        data = bytes([self.rxbuf.popleft() for _ in range(nr_bytes)])
        return data