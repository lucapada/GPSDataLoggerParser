from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

class Observable(ABC):
    @abstractmethod
    def attach(self, observer: Observer) -> None:
        pass

    @abstractmethod
    def detach(self, observer: Observer) -> None:
        pass

    @abstractmethod
    def notify(self) -> None:
        pass

class Reporter(Observable):
    _msg: str = None
    _observers: List[Observer] = []

    def attach(self, observer: Observer) -> None:
        self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        self._observers.remove(observer)

    def notify(self) -> None:
        for observer in self._observers:
            observer.update(self)

    def printLog(self, msg) -> None:
        self._msg = msg
        self.notify()

class Observer(ABC):
    @abstractmethod
    def update(self, obs: Observable) -> None:
        pass
