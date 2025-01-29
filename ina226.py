

from dataclasses import dataclass
import time

from pyftdi.i2c import I2cPort

@dataclass
class INA226_Regs:
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

        ManId = self.__readReg16(INA226_Regs.ManId)
        DieId = self.__readReg16(INA226_Regs.DieId)

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

    def setup(self):

        convTime, AVG_setting, interval = self.calibrateInterval()

        VBUSCT_setting = convTime
        VSHCT_setting = convTime
        MODE_setting = MODE_Setting.ShuntAndBusVoltageCont

        reg_val = MODE_setting | (VSHCT_setting << 3) | (VBUSCT_setting << 6) | (AVG_setting << 9)

        self.__writeReg16(INA226_Regs.Config, reg_val)
        got = self.__readReg16(INA226_Regs.Config)

        assert (got & reg_val) == reg_val, f'Write config failed: got {hex(got & reg_val)} != exp {hex(reg_val)}'

        return interval

    def calibrate(self, maxCurrent, Rshunt):
        currentLSB = maxCurrent / (2**15)
        cal = 0.00512 / (currentLSB * Rshunt)
        cal = int(cal)

        self.currentLSB = currentLSB

        self.__writeReg16(INA226_Regs.Calibration, cal)

    def readCurrent(self):
        raw = self.__readReg16(INA226_Regs.Current)
        current = raw * self.currentLSB
        return current

    def readVbus(self):
        raw = self.__readReg16(INA226_Regs.BusVoltage)
        vbus = raw * 1.25
        return vbus / 1000

    def calibrateInterval(self):
        nr_iter = 20
        start_time = time.time()
        for _ in range (nr_iter):
            _ = self.__readReg16(INA226_Regs.Current)
        diff_time = (time.time() - start_time) / nr_iter
        diff_time *= 1000
        diff_time += 2

        map_conv_time = [
            (VBUSCT_Setting.ConversionTime_140us, 0.140),
            (VBUSCT_Setting.ConversionTime_204us, 0.204),
            (VBUSCT_Setting.ConversionTime_332us, 0.332),
            (VBUSCT_Setting.ConversionTime_588us, 0.588),
            (VBUSCT_Setting.ConversionTime_1100us, 1.1),
            (VBUSCT_Setting.ConversionTime_2116us, 2.116),
            (VBUSCT_Setting.ConversionTime_4156us, 4.156),
            (VBUSCT_Setting.ConversionTime_8244us, 8.244)
        ]

        map_avg = [
            (AVG_Setting.NrAverages_1, 1),
            (AVG_Setting.NrAverages_4, 4),
            (AVG_Setting.NrAverages_16, 16),
            (AVG_Setting.NrAverages_64, 64),
            (AVG_Setting.NrAverages_128, 128),
            (AVG_Setting.NrAverages_256, 256),
            (AVG_Setting.NrAverages_512, 512),
            (AVG_Setting.NrAverages_1024, 1024)
        ]

        min_diff = float('inf')
        best_pair = (None, None)

        for conv_time_setting, conv_time in map_conv_time:
            for avg_setting, avg in map_avg:
                product = conv_time * avg
                diff = abs(diff_time - product)

                if diff < min_diff:
                    min_diff = diff
                    best_pair = (conv_time_setting, avg_setting)

        conv_time_setting, avg_setting = best_pair
        return conv_time_setting, avg_setting, diff_time/1000