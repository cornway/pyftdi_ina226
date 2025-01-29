#!/usr/bin/env python3

from pyftdi.ftdi import Ftdi
from pyftdi.i2c import I2cController, I2cNackError
from argparse import ArgumentParser, FileType
from time import sleep

from ina226 import INA226

from plot import RealTimePlotParams, RealTimePlot


ftdi_device = "ftdi://ftdi:232h:3:10/1"

def generator(ina226: INA226):
    while True:
        current = ina226.readCurrent()
        vbus = ina226.readVbus()
        power = current * vbus

        yield [power * 1000, vbus * 1000, current * 1000]

def main():
    argparser = ArgumentParser()
    argparser.add_argument('device', nargs='?', default='ftdi:///?',
                            help='serial port device name')

    argparser.add_argument('-addr', default=0x40,
                            help='i2c slave address', type=lambda x: int(x,0))

    args = argparser.parse_args()

    Ftdi.show_devices()

    i2c = I2cController()

    i2c.set_retry_count(1)
    i2c.force_clock_mode(False)
    i2c.configure(args.device)


    port = i2c.get_port(args.addr)

    ina226 = INA226(port)

    interval = ina226.setup()
    ina226.calibrate(maxCurrent=1, Rshunt=0.1)
    interval *= 2

    print(f'{interval=}')

    winsize_sec = 20
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

    plot = RealTimePlot(plotParams, winsize, interval, generator(ina226))
    plot.run()

if __name__ == '__main__':
    main()