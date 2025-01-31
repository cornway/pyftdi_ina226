

import time
from ina226_regs import *
from ina226_if import INA226_If

class INA226:
    endianess: str = 'big'
    ina226_if: INA226_If = None

    map_conv_time = {
        VBUSCT_Setting.ConversionTime_140us: 0.140,
        VBUSCT_Setting.ConversionTime_204us:0.204,
        VBUSCT_Setting.ConversionTime_332us:0.332,
        VBUSCT_Setting.ConversionTime_588us:0.588,
        VBUSCT_Setting.ConversionTime_1100us:1.1,
        VBUSCT_Setting.ConversionTime_2116us:2.116,
        VBUSCT_Setting.ConversionTime_4156us:4.156,
        VBUSCT_Setting.ConversionTime_8244us:8.244
    }

    map_avg = {
        AVG_Setting.NrAverages_1:1,
        AVG_Setting.NrAverages_4:4,
        AVG_Setting.NrAverages_16:16,
        AVG_Setting.NrAverages_64:64,
        AVG_Setting.NrAverages_128:128,
        AVG_Setting.NrAverages_256:256,
        AVG_Setting.NrAverages_512:512,
        AVG_Setting.NrAverages_1024:1024
    }

    def __init__(self, ina226_if: INA226_If):
        self.ina226_if = ina226_if

        ManId = self.ina226_if.readReg16(INA226_Regs.ManId)
        DieId = self.ina226_if.readReg16(INA226_Regs.DieId)

        assert ManId == 0x5449, f'ManId doesn\'t match : {hex(ManId)}, expected : {hex(0x5449)}'
        assert DieId == 0x2260, f'DieId doesn\'t match : {hex(DieId)}, expected : {hex(0x2260)}'

        print('Init OK')


    def setup(self):
        VBUSCT_setting = VBUSCT_Setting.ConversionTime_1100us
        VSHCT_setting = VSHCT_Setting.ConversionTime_1100us
        MODE_setting = MODE_Setting.ShuntAndBusTriggered
        AVG_setting = AVG_Setting.NrAverages_64

        reg_val = MODE_setting | (VSHCT_setting << 3) | (VBUSCT_setting << 6) | (AVG_setting << 9)

        self.ina226_if.writeReg16(INA226_Regs.Config, reg_val)
        got = self.ina226_if.readReg16(INA226_Regs.Config)

        assert (got & reg_val) == reg_val, f'Write config failed: got {hex(got & reg_val)} != exp {hex(reg_val)}'

        print('Setup OK')

        interval = self.map_conv_time[VSHCT_setting] * self.map_avg[AVG_setting]
        interval /= 1000

        return interval

    def calibrate(self, maxCurrent, Rshunt):
        currentLSB = maxCurrent / (2**15)
        cal = 0.00512 / (currentLSB * Rshunt)
        cal = int(cal)

        self.currentLSB = currentLSB

        self.ina226_if.writeReg16(INA226_Regs.Calibration, cal)

    def readCurrent(self):
        raw =  self.ina226_if.readCurrent()
        return float(raw) * self.currentLSB

    def readVbus(self):
        raw = self.ina226_if.readVbus()
        vbus = raw * 1.25
        return vbus / 1000

    def calibrateInterval(self):
        nr_iter = 20
        start_time = time.time()
        for _ in range (nr_iter):
            _ = self.ina226_if.readReg16(INA226_Regs.Current)
        diff_time = (time.time() - start_time) / nr_iter
        diff_time *= 1000
        diff_time += 2

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
