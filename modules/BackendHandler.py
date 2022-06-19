from . import ThreadWithReturn
from . import SerialParser
from . import Logger
from .Reporter import Observer


class Handler(object):

    def __init__(self, port: str, baudrate = 9600, gnss: dict = {}, filePath: str = "."):
        self.baudrate = baudrate
        self.connection = SerialParser.SerialParser(port=port, baudrate=self.baudrate)
        self.logger = Logger.Logger(self.connection, gnss, filePath)
        self.thread = ThreadWithReturn.ThreadWithReturn(target=self.logger.logData)

    def isActive(self):
        return self.logger.serial.isOpen()

    def appendObserver(self, observer: Observer):
        self.logger.attach(observer)
        self.connection.attach(observer)

    def handleData(self):
        self.thread.start()

    def join(self):
        self.connection.close()
        self.thread.join()
