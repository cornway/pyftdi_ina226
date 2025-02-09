import asyncio
from collections import deque
from bleak import BleakClient, BleakScanner
import numpy as np
from enum import IntEnum
import threading

from ina226_if import INA226_ll

UART_TX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class INA226_Bt(INA226_ll):
    byteorder = 'little'
    MaxPktLen = 2048

    def __init__(self, targetDeviceName):
        self.rxbuf = deque(maxlen=self.MaxPktLen)
        self.txbuf = deque(maxlen=self.MaxPktLen)

        self.async_loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.start_async_loop, args=(self.async_loop,), daemon=True)
        self.thread.start()

        self.future = asyncio.run_coroutine_threadsafe(self.ble_gatt_loop(targetDeviceName), self.async_loop)

        self._terminate = False
        self._terminated = False

    def start_async_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def ble_scan(self, targetDeviceName):
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
            return None

        print(f"Found device: {target_device.name}, Address: {target_device.address}")

        return target_device

    async def ble_gatt_loop(self, targetDeviceName):

        target_device = await self.ble_scan(targetDeviceName)

        if not target_device:
            return

        print("Connecting...")

        async with BleakClient(target_device.address) as client:
            print(f"Connected to {target_device.address}")

            def notification_handler(sender, data):
                self.rxbuf.extend(data)

            await client.start_notify(UART_RX_UUID, notification_handler)

            try:
                while not self._terminate:
                    await asyncio.sleep(0.01)
                    _txbuf = bytes([self.txbuf.popleft() for _ in range(len(self.txbuf))])
                    if len(_txbuf):
                        await client.write_gatt_char(UART_TX_UUID, _txbuf)
            except KeyboardInterrupt:
                print('*** KeyboardInterrupt ***')
                pass

            await client.stop_notify(UART_RX_UUID)
            await client.disconnect()
            print("Disconnected.")
            self._terminated = True


    def sendBytes(self, bytes):
        self.txbuf.extend(bytes)

    def recvBytes(self, nr_bytes):
        while len(self.rxbuf) < nr_bytes:
            pass
        data = bytes([self.rxbuf.popleft() for _ in range(nr_bytes)])
        return data

    def terminate(self):
        self._terminate = True
        while self._terminated == False:
            pass
        print('Terminated')