#!/usr/bin/env python3

from pyftdi.ftdi import Ftdi
from pyftdi.i2c import I2cController, I2cNackError
from argparse import ArgumentParser, FileType
from time import sleep

from ina226 import INA226, INA226_REgs

ftdi_device = "ftdi://ftdi:232h:3:10/1"

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

    ina226.setupCurrent()
    ina226.calibrate(maxCurrent=0.1, Rshunt=0.1)

    while True:
        current = ina226.readCurrent()

        print(f'current: {current * 1000} mA')
        sleep(0.2)

    #id = port.exchange(0x00, 2)

    #print(f'{id=}')

if __name__ == '__main__':
    main()