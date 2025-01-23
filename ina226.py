
from pyftdi.i2c import I2cPort

from dataclasses import dataclass

@dataclass
class INA226_REgs:
    Config: int = 0x00
    ShuntVoltage: int = 0x1
    BusVoltage: int = 0x2
    Power: int = 0x3
    Current: int = 0x4
    Calibration: int = 0x5
    MaskEnable: int = 0x6
    AlertLimit: int = 0x7
    ManId: int = 0xfe
    DieId: int = 0xff

@dataclass
class AVG_Setting:
    NrAverages_1: int = 0b000
    NrAverages_4: int = 0b001
    NrAverages_16: int = 0b010
    NrAverages_64: int = 0b011
    NrAverages_128: int = 0b100
    NrAverages_256: int = 0b101
    NrAverages_512: int = 0b110
    NrAverages_1024: int = 0b111

@dataclass
class VBUSCT_Setting:
    ConversionTime_140us: int = 0b000
    ConversionTime_204us: int = 0b001
    ConversionTime_332us: int = 0b010
    ConversionTime_588us: int = 0b011
    ConversionTime_1100us: int = 0b100
    ConversionTime_2116us: int = 0b101
    ConversionTime_4156us: int = 0b110
    ConversionTime_8244us: int = 0b111

@dataclass
class VSHCT_Setting:
    ConversionTime_140us: int = 0b000
    ConversionTime_204us: int = 0b001
    ConversionTime_332us: int = 0b010
    ConversionTime_588us: int = 0b011
    ConversionTime_1100us: int = 0b100
    ConversionTime_2116us: int = 0b101
    ConversionTime_4156us: int = 0b110
    ConversionTime_8244us: int = 0b111

@dataclass
class MODE_Setting:
    PowerDown: int = 0b000
    ShuntVoltageTriggered: int = 0b001
    BusVoltageTriggered: int = 0b010
    ShuntAndBusTriggered: int = 0b011
    ShutDown: int = 0b100
    ShuntVoltageCont: int = 0b101
    BusVoltageCont: int = 0b110
    ShuntAndBusVoltageCont: int = 0b111


class INA226:
    port: I2cPort = None
    endianess: str = 'big'
    def __init__(self, port: I2cPort):
        self.port = port

        ManId = self.__readReg16(INA226_REgs.ManId)
        DieId = self.__readReg16(INA226_REgs.DieId)

        assert ManId == 0x5449, f'ManId doesn\'t match : {hex(ManId)}, expected : {hex(0x5449)}'
        assert DieId == 0x2260, f'DieId doesn\'t match : {hex(DieId)}, expected : {hex(0x2260)}'


    def __readReg(self, addr, nrBytes = 2):
        self.port.write([addr])
        bytes = self.port.read(nrBytes)
        return bytes

    def __readReg16(self, addr):
        return int.from_bytes(self.__readReg(addr, nrBytes=2), self.endianess)

    def __writeReg(self, addr, val):
        buf = [addr]
        if type(val) is list:
            buf.extend(val)
        else:
            buf.append(val)
        self.port.write(buf)

    def __writeReg16(self, addr, val):
        buf = []
        buf.append((val >> 8) & 0xff)
        buf.append((val >> 0) & 0xff)

        self.__writeReg(addr, buf)

    def setupCurrent(self):
        AVG_setting = AVG_Setting.NrAverages_64
        VBUSCT_setting = VBUSCT_Setting.ConversionTime_1100us
        VSHCT_setting = VSHCT_Setting.ConversionTime_1100us
        MODE_setting = MODE_Setting.ShuntVoltageCont

        reg_val = MODE_setting | (VSHCT_setting << 3) | (VBUSCT_setting << 6) | (AVG_setting << 9)

        self.__writeReg16(INA226_REgs.Config, reg_val)
        got = self.__readReg16(INA226_REgs.Config)

        assert (got & reg_val) == reg_val, f'Write config red failed: got {hex(got & reg_val)} != exp {hex(reg_val)}'

    def calibrate(self, maxCurrent, Rshunt):
        currentLSB = maxCurrent / (2**15)
        cal = 0.00512 / (currentLSB * Rshunt)
        cal = int(cal)

        self.currentLSB = currentLSB

        self.__writeReg16(INA226_REgs.Calibration, cal)

    def readCurrent(self):

        raw = self.__readReg16(INA226_REgs.Current)
        current = raw * self.currentLSB

        return current