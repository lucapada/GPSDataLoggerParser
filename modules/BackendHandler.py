from . import ThreadWithReturn
from . import SerialParser
from . import Logger

class Handler(object):

    def __init__(self, mainWindow, port: str, baudrate = 9600, gnss: dict = {}, filePath: str = "."):
        self.baudrate = baudrate
        self.connection = SerialParser.SerialParser(mainWindow, port, self.baudrate)
        self.logger = Logger.Logger(mainWindow, self.connection, gnss, filePath)
        self.thread = ThreadWithReturn.ThreadWithReturn(target=self.logger.logData)

    def isActive(self):
        return self.logger.serial.isOpen()

    def handleData(self):
        self.thread.start()

    def join(self):
        self.connection.close()
        self.thread.join()
