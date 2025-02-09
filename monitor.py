#!/usr/bin/env python3

from pyftdi.ftdi import Ftdi
from pyftdi.i2c import I2cController, I2cNackError
from argparse import ArgumentParser, FileType
from plot import RealTimePlotParams, RealTimePlot
import time

from ina226 import INA226
from ina226_i2c import INA226_I2C_If
from ina226_uart import INA226_Uart
from ina226_bt import INA226_Bt
from ina226_remote import INA226_Remote

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
    argparser.add_argument('--serial', nargs='?', default=None,
                            help='serial port device name')

    argparser.add_argument('--ble', nargs='?', default='esp32_ina226_uart',
                            help='ble device name')

    argparser.add_argument('--i2c_addr', nargs='?', default=0x40,
                            help='i2c slave address', type=lambda x: int(x,0))

    argparser.add_argument('--nr_samples', nargs='?', default=128,
                            help='Number of samples to read per batch (remote only)', type=lambda x: int(x,0))

    args = argparser.parse_args()

    serial = args.serial
    ble = args.ble
    i2c_addr = args.i2c_addr
    nr_samples = args.nr_samples

    if serial and ble:
        raise Exception('Can\'t use both serial and ble same time')

    if serial or ble:
        if serial:
            ina_ll = INA226_Uart(serial, 115200)
        else:
            ina_ll = INA226_Bt(ble)

        try:
            ina_if = INA226_Remote(i2c_addr, nr_samples, ina_ll)
        except KeyboardInterrupt:
            print('*** KeyboardInterrupt ***')
            ina_ll.terminate()
            exit(1)

    else:
        Ftdi.show_devices()
        i2c = I2cController()

        i2c.set_retry_count(1)
        i2c.force_clock_mode(False)
        i2c.configure(i2c_addr)

        port = i2c.get_port(args.addr)
        ina_if = INA226_I2C_If(port)

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

    def terminate_callback(event):
        ina226.terminate()

    plot = RealTimePlot(plotParams, winsize, interval, generator(ina226, interval), terminate_callback)
    plot.run()

if __name__ == '__main__':
    main()