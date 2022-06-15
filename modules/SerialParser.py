from serial import Serial
from serial.serialutil import SerialException
import time

from modules import Reporter

class SerialParser(Serial):

    def __init__(self, *args, **kwargs):

        # --------------------------------------------
        self._reporter = Reporter()
        # --------------------------------------------

        try:
            super().__init__(*args, **kwargs)
        except SerialException:
            self._reporter.printLog(f"[ERROR] Cannot initialize serial port {self.port}")

        if self.isOpen():
            self.printParserMessage(f"Connection Opened")
        else:
            self.error_n_die()


    # Generic error handler
    def error_n_die(self):
        self.printParserMessage("Cannot access port. Either device is disconnected or port error")
        self.close()

    def printParserMessage(self, msg:str):
        self._reporter.printLog(f"[SERIAL] {self.port}: {msg}")
