from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class RaProgressBar(QWidget):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setLayout(QHBoxLayout())

        self.__left_label = QLabel()
        self.__progress_bar = QProgressBar()
        self.__right_label = QLabel()

        self.layout().addWidget(self.__left_label)
        self.layout().addWidget(self.__progress_bar)
        self.layout().addWidget(self.__right_label)

    def reset(self):
        self.__progress_bar.reset()
        self.__left_label.setText("")
        self.__right_label.setText("")

    @property
    def text_left(self):
        return self.__left_label.text()

    @text_left.setter
    def text_left(self, text: str):
        self.__left_label.setText(text)

    @property
    def text_right(self):
        return self.__right_label.text()

    @text_right.setter
    def text_right(self, text: str):
        self.__right_label.setText(text)

    @property
    def value(self):
        return self.__progress_bar.value()

    @value.setter
    def value(self, value: int):
        self.__progress_bar.setValue(value)

    @property
    def maximum(self):
        return self.__progress_bar.maximum()

    @maximum.setter
    def maximum(self, maximum: int):
        self.__progress_bar.setMaximum(maximum)
