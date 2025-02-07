#!/usr/bin/env python3

from pyftdi.ftdi import Ftdi
from pyftdi.i2c import I2cController, I2cNackError
from argparse import ArgumentParser, FileType

from ina226 import INA226
from ina226_i2c import INA226_I2C_If
from ina226_uart import INA226_Uart
from ina226_bt import INA226_Bt
from ina226_remote import INA226_Remote

from plot import RealTimePlotParams, RealTimePlot
import time

ftdi_device = "ftdi://ftdi:232h:3:10/1"

def generator(ina226: INA226, interval):
    while True:
        current = ina226.readCurrent()
        vbus = ina226.readVbus()
        power = current * vbus
        time.sleep(0.01)

        yield [power * 1000, vbus * 1000, current * 1000]

def main():
    argparser = ArgumentParser()
    argparser.add_argument('device', nargs='?', default=None,
                            help='serial port device name')

    argparser.add_argument('-addr', default=0x40,
                            help='i2c slave address', type=lambda x: int(x,0))

    args = argparser.parse_args()

    Ftdi.show_devices()


    if (args.device is not None):
        i2c = I2cController()

        i2c.set_retry_count(1)
        i2c.force_clock_mode(False)
        i2c.configure(args.device)


        port = i2c.get_port(args.addr)
        ina_if = INA226_I2C_If(port)

    else:
        #ina_if = INA226_Serial("/dev/ttyUSB0", 115200)
        ina_ll = INA226_Bt()
        ina_if = INA226_Remote(ina_ll)

    ina226 = INA226(ina_if)

    interval = ina226.setup()
    ina226.calibrate(maxCurrent=0.100, Rshunt=1)

    print(f'interval = {interval}')

    winsize_sec = 5
    winsize = int(winsize_sec / interval)

    plotParams = []
    plotParams.append( RealTimePlotParams(
            xlabel='Time S',
            ylabel="Power, mW",
            title=""
        )
    )

    plotParams.append( RealTimePlotParams(
            xlabel='Time S',
            ylabel="Voltage, mV",
            title=""
        )
    )

    plotParams.append( RealTimePlotParams(
            xlabel='Time S',
            ylabel="Current, mA",
            title=""
        )
    )

    plot = RealTimePlot(plotParams, winsize, interval, generator(ina226, interval))
    plot.run()

if __name__ == '__main__':
    main()