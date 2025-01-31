from pyftdi.i2c import I2cPort

from ina226_if import INA226_If
from ina226_regs import *

class INA226_I2C_If(INA226_If):
    port: I2cPort = None

    def __init__(self, port: I2cPort):
        self.port = port

    def __readReg(self, addr, nrBytes = 2):
        self.port.write([addr])
        bytes = self.port.read(nrBytes)
        return bytes

    def readReg16(self, addr: int):
        return int.from_bytes(self.__readReg(addr, nrBytes=2), self.endianess)

    def __writeReg(self, addr, val):
        buf = [addr]
        if type(val) is list:
            buf.extend(val)
        else:
            buf.append(val)
        self.port.write(buf)

    def writeReg16(self, addr: int, val: int):
        buf = []
        buf.append((val >> 8) & 0xff)
        buf.append((val >> 0) & 0xff)

        self.__writeReg(addr, buf)

    def readCurrent(self):
        raw = self.readReg16(INA226_Regs.Current)
        return raw

    def readVbus(self):
        raw = self.readReg16(INA226_Regs.BusVoltage)
        return raw