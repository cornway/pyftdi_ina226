

class INA226_ll:
    def __init__(self):
        raise NotImplemented()

    def sendBytes(self):
        raise NotImplemented()

    def recvBytes(self):
        raise NotImplemented()

    def terminate(self):
        raise NotImplemented()

class INA226_If:
    def __init__(self):
        raise NotImplemented()

    def readReg16(self, addr: int):
        raise NotImplemented()

    def writeReg16(self, addr: int, val: int):
        raise NotImplemented()

    def readCurrent(self):
        raise NotImplemented()

    def readVbus(self):
        raise NotImplemented()

    def terminate(self):
        raise NotImplemented()

