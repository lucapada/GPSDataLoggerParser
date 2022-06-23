from serial import Serial
from serial.serialutil import SerialException

class SerialParser(Serial):

    def __init__(self, mainWindow, port, baudRate):
        self.mainWindow = mainWindow
        try:
            super().__init__(port=port, baudrate=baudRate)
        except SerialException:
            self.mainWindow.printLog(f"[SERIAL ERROR] Cannot initialize serial port \"{self.port}\"")

        if self.isOpen():
            self.mainWindow.printLog(f"[SERIAL] Connection Opened")
        else:
            self.error_n_die()

    # Generic error handler
    def error_n_die(self):
        self.mainWindow.printLog(f"[SERIAL ERROR] Cannot access port \"{self.port}\". Either device is disconnected or port error")
        self.close()
