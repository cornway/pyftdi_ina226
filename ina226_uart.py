

import serial
import struct
from collections import deque
import numpy as np
from enum import IntEnum

from ina226_regs import *
from ina226_if import INA226_If

class OpCodes(IntEnum):
    ReadReg = 0xfff0
    WriteReg = 0xfff1

class INA226_Serial(INA226_If):
    byteorder = 'little'
    MaxPktLen = 2048

    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.serial = serial.Serial(self.port, self.baud, timeout=200000)
        self.current_buf = deque(maxlen=self.MaxPktLen//2)
        self.vbus_buf = deque(maxlen=self.MaxPktLen//2)
        self.nr_packets = 0
        self.pkt_req_sent = False

    def checkAck(self):
        ack = self.serial.read(1)
        ack = np.frombuffer(ack, np.uint8)
        assert ack == 0xff


    def readReg16(self, addr: int):
        header = OpCodes.ReadReg.to_bytes(2, byteorder=self.byteorder)
        addr = addr.to_bytes(2, byteorder=self.byteorder)

        self.serial.flush()
        self.serial.write(header)
        self.checkAck()
        self.serial.write(addr)

        reg = self.serial.read(2)
        reg = np.frombuffer(reg, dtype=np.uint16)
        return reg

    def writeReg16(self, addr: int, val: int):
        header = OpCodes.WriteReg.to_bytes(2, byteorder=self.byteorder)
        header = bytearray(header)
        addr = addr.to_bytes(2, byteorder=self.byteorder)
        val = val.to_bytes(2, byteorder=self.byteorder)


        self.serial.flush()
        self.serial.write(header)
        self.checkAck()
        self.serial.write(addr)
        self.checkAck()
        self.serial.write(val)

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
        self.serial.flush()
        pkt_length = 128

        if not self.pkt_req_sent:
            wdata = pkt_length.to_bytes(2, byteorder='little')
            self.serial.write(wdata)
            self.pkt_req_sent = True

        pkt = self.serial.read(pkt_length * 2)
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
            self.serial.write(wdata)
            self.pkt_req_sent = True
