from . import ThreadWithReturn
from . import SerialParser
from . import Logger

class Handler(object):

    def __init__(self, mainWindow, port: str, baudrate = 9600, gnss: dict = {}, filePath: str = ".", weekChanges: bool = False):
        self.baudrate = baudrate
        self.connection = SerialParser.SerialParser(mainWindow, port, self.baudrate)
        self.logger = Logger.Logger(mainWindow, self.connection, filePath, gnss, weekChanges)
        self.thread = ThreadWithReturn.ThreadWithReturn(target=self.logger.logData)

    def isActive(self):
        return self.logger.serial.isOpen()

    def handleData(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()

    def join(self):
        self.connection.close()
        self.thread.join()
