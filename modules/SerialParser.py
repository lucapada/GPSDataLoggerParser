from typing import List

from serial import Serial
from serial.serialutil import SerialException
import time

from modules import Reporter
from modules.Reporter import Observer


class SerialParser(Serial, Observer):

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except SerialException:
            self.notifyMessage(f"[ERROR] Cannot initialize serial port {self.port}")

        if self.isOpen():
            self.notifyMessage(f"Connection Opened")
        else:
            self.error_n_die()

    # Generic error handler
    def error_n_die(self):
        self.notifyMessage("Cannot access port. Either device is disconnected or port error")
        self.close()

    # Handler is Observer of Logger. So implements Observable
    _observers: List[Observer] = []
    _messaggio: str = ""

    def attach(self, observer: Observer) -> None:
        self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        self._observers.remove(observer)

    def notify(self) -> None:
        for observer in self._observers:
            observer.update(self)

    def setMessage(self, msg: str):
        self._messaggio = msg

    def notifyMessage(self, msg: str):
        self.setMessage(f"[SERIAL] {self.port}: {msg}")
        self.notify()
