from __future__ import annotations
from abc import ABC, abstractmethod

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

class Observer(ABC):
    @abstractmethod
    def update(self, observable: Observable, msg: str) -> None:
        pass
