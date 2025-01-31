from dataclasses import dataclass

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
