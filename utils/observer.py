from typing import Callable, TypeVar, Generic

T = TypeVar('T')

class Observer(Generic[T]):
    def __init__(self, *values: T):
        self.__values: tuple[T, ...] = values
        self.observers: list[Callable[[T, ...], None]] = []

    def set(self, **new_values: T):
        self.__values = new_values
        self.__notify(**new_values)

    def add_observer(self, observer: Callable[[T, ...], None]):
        self.observers.append(observer)

    def __notify(self, **new_values: T):
        for observer in self.observers:
            observer(**new_values)