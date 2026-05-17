from abc import ABC, abstractmethod
from dataclasses import dataclass


class Animal(ABC):
    @abstractmethod
    def speak(self) -> str:
        ...


@dataclass
class Dog(Animal):
    name: str

    def speak(self) -> str:
        return f"{self.name}: woof"


@dataclass
class GhostCat(Animal):
    name: str

    def speak(self) -> str:
        return "..."


def unused_factory():
    return Dog("rex")
