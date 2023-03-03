from serial import Serial
from serial.serialutil import SerialException

class SerialParser(Serial):
    """
    Classe che gestisce l'interazione con la porta seriale COM.
    """
    def __init__(self, mainWindow, port, baudRate, timeout):
        """
        Costruttore della classe.
        :param mainWindow: finestra della GUI
        :param port: porta a cui connettersi
        :param baudRate: baudrate con cui connettersi
        """
        self.mainWindow = mainWindow
        try:
            super().__init__(port=port, baudrate=baudRate, timeout=timeout)
        except SerialException:
            self.mainWindow.printLog(f"[SERIAL ERROR] Cannot initialize serial port \"{self.port}\"")

        if self.isOpen():
            self.mainWindow.printLog(f"[SERIAL] Connection Opened")
        else:
            self.error_n_die()

    # Generic error handler
    def error_n_die(self):
        """
        Stampa a video eventuali errori dovuti a chiusure improvvise della porta.
        :return:
        """
        self.mainWindow.printLog(f"[SERIAL ERROR] Cannot access port \"{self.port}\". Either device is disconnected or port error")
        self.close()

    def reconnect(self):
        """
        Effettua la riconnessione al dispositivo reinizializzando l'oggetto.
        :return:
        """
        result = False
        try:
            super().__init__(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            result = True
        except SerialException:
            result = False

        if self.isOpen() and result is True:
            return True
        else:
            return False
