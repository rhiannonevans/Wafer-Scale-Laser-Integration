from tqdm import tqdm


class tqdm_qt(tqdm):
    """
    hack tqdm to send a qt signal, instead of printing to stderr
    """

    def __init__(self, *args, qt_signal=None, **kwargs):
        self.__qt_signal = qt_signal
        super().__init__(*args, **kwargs)

    def display(self, msg: str | None = None, pos: int | None = None) -> None:
        if self.__qt_signal:
            self.__qt_signal.emit(self.format_dict)
        # super().display(msg, pos) # ban the original display to stderr
