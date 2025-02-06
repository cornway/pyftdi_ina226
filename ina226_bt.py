import asyncio
import functools
from collections import deque
from bleak import BleakClient, BleakScanner

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
                await asyncio.sleep(0.001)
                if len(txbuf):
                    await client.write_gatt_char(UART_TX_UUID, txbuf)
                    txbuf.clear()

        except KeyboardInterrupt:
            print("Keyboard interrupt received, stopping notifications...")
        finally:
            await client.stop_notify(UART_RX_UUID)
            print("Disconnected.")


import numpy as np
from enum import IntEnum

from ina226_regs import *
from ina226_if import INA226_If

import threading

class OpCodes(IntEnum):
    ReadReg = 0xfff0
    WriteReg = 0xfff1

class INA226_Bt(INA226_If):
    byteorder = 'little'
    MaxPktLen = 2048

    def __init__(self):
        self.current_buf = deque(maxlen=self.MaxPktLen//2)
        self.vbus_buf = deque(maxlen=self.MaxPktLen//2)
        self.nr_packets = 0
        self.pkt_req_sent = False

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

    def checkAck(self):
        ack = self.recvBytes(1)
        ack = int.from_bytes(bytes=ack, byteorder=self.byteorder)
        assert ack == 0xff

    def readReg16(self, addr: int):
        header = OpCodes.ReadReg.to_bytes(2, byteorder=self.byteorder)
        addr = addr.to_bytes(2, byteorder=self.byteorder)

        self.sendBytes(header)
        self.checkAck()
        self.sendBytes(addr)

        reg = self.recvBytes(2)
        reg = int.from_bytes(bytes=reg, byteorder=self.byteorder)
        return reg

    def writeReg16(self, addr: int, val: int):
        header = OpCodes.WriteReg.to_bytes(2, byteorder=self.byteorder)
        header = bytearray(header)
        addr = addr.to_bytes(2, byteorder=self.byteorder)
        val = val.to_bytes(2, byteorder=self.byteorder)


        self.sendBytes(header)
        self.checkAck()
        self.sendBytes(addr)
        self.checkAck()
        self.sendBytes(val)

    def readCurrent(self):
        if len(self.current_buf) == 0:
            self.read_packet()

        raw = self.current_buf.popleft()
        return raw

    def readVbus(self):
        if len(self.vbus_buf) == 0:
            self.read_packet()

        raw = self.vbus_buf.popleft()
        return raw

    def read_packet(self):
        pkt_length = 128

        if not self.pkt_req_sent:
            wdata = pkt_length.to_bytes(2, byteorder='little')
            self.sendBytes(wdata)
            self.pkt_req_sent = True

        pkt = self.recvBytes(pkt_length * 2)
        self.pkt_req_sent = False
        pkt = np.frombuffer(pkt, dtype=np.uint16)

        if (len(self.current_buf) or len(self.vbus_buf)):
            print('Packets were not empty !')

        self.current_buf.clear()
        self.vbus_buf.clear()

        self.current_buf.extend( pkt[::2] )
        self.vbus_buf.extend( pkt[1::2] )

        print(f'Packet {self.nr_packets}')
        self.nr_packets += 1

        if not self.pkt_req_sent:
            wdata = pkt_length.to_bytes(2, byteorder='little')
            self.sendBytes(wdata)
            self.pkt_req_sent = True
