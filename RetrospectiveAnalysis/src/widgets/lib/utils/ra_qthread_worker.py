from typing import Any, Callable

from PySide6.QtCore import QThread


class RaQThreadWorker(QThread):
    def __init__(self, f: Callable[[], Any], *args, **kwargs):
        super().__init__()
        self.__f = f
        self.__args = args
        self.__kwargs = kwargs
        self.__error = None

    def run(self):
        try:
            self.__ret = self.__f(*self.__args, **self.__kwargs)

        except Exception as e:
            print(e)
            self.__error = e

    @property
    def result(self):
        return self.__ret

    @property
    def error(self):
        return self.__error
