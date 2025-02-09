from collections import deque
import numpy as np
from enum import IntEnum

from ina226_regs import *
from ina226_if import INA226_If, INA226_ll

class OpCodes(IntEnum):
    ReadReg = 0xfff0
    WriteReg = 0xfff1
    Seti2cAddress = 0xfff2
    GetBufferLen = 0xfff3

class INA226_Remote(INA226_If):
    byteorder = 'little'
    MaxPktLen = 2048

    def __init__(self, i2c_address, nr_samples, ina226_ll: INA226_ll):
        self.ll = ina226_ll

        self._seti2cAddress(i2c_address)
        self.MaxPktLen = self._getMaxPktLen()
        self.nrSamples = self.MaxPktLen if nr_samples > self.MaxPktLen else nr_samples

        print(f'max packet length = {self.MaxPktLen}')

        self.current_buf = deque(maxlen=self.MaxPktLen//2)
        self.vbus_buf = deque(maxlen=self.MaxPktLen//2)
        self.nr_packets = 0
        self.pkt_req_sent = False

    def checkAck(self):
        ack = self.ll.recvBytes(1)
        ack = int.from_bytes(bytes=ack, byteorder=self.byteorder)
        assert ack == 0xff

    def _seti2cAddress(self, address):
        header = OpCodes.Seti2cAddress.to_bytes(2, byteorder=self.byteorder)
        self.ll.sendBytes(header)
        self.checkAck()
        bytes = int.to_bytes(address, 1, byteorder=self.byteorder)
        self.ll.sendBytes(bytes)

    def _getMaxPktLen(self):
        header = OpCodes.GetBufferLen.to_bytes(2, byteorder=self.byteorder)
        self.ll.sendBytes(header)
        self.checkAck()
        bytes = self.ll.recvBytes(2)
        return int.from_bytes(bytes, byteorder=self.byteorder)

    def readReg16(self, addr: int):
        header = OpCodes.ReadReg.to_bytes(2, byteorder=self.byteorder)
        addr = addr.to_bytes(2, byteorder=self.byteorder)

        self.ll.sendBytes(header)
        self.checkAck()
        self.ll.sendBytes(addr)

        reg = self.ll.recvBytes(2)
        reg = int.from_bytes(bytes=reg, byteorder=self.byteorder)
        return reg

    def writeReg16(self, addr: int, val: int):
        header = OpCodes.WriteReg.to_bytes(2, byteorder=self.byteorder)
        header = bytearray(header)
        addr = addr.to_bytes(2, byteorder=self.byteorder)
        val = val.to_bytes(2, byteorder=self.byteorder)


        self.ll.sendBytes(header)
        self.checkAck()
        self.ll.sendBytes(addr)
        self.checkAck()
        self.ll.sendBytes(val)

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
        pkt_length = self.nrSamples

        if not self.pkt_req_sent:
            wdata = pkt_length.to_bytes(2, byteorder='little')
            self.ll.sendBytes(wdata)
            self.pkt_req_sent = True

        pkt = self.ll.recvBytes(pkt_length * 2)
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
            self.ll.sendBytes(wdata)
            self.pkt_req_sent = True

    def terminate(self):
        self.ll.terminate()