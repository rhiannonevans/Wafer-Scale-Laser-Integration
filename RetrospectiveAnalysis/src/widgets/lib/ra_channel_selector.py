from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QVBoxLayout,
    QWidget,
)


class RaChannelSelector(QWidget):
    def __init__(self, *args, max_col=4, prefix="Channel", **kwargs):
        super().__init__(*args, **kwargs)

        self.__max_col = max_col
        self.__prefix = prefix

        self.__select_all_checkbox = QCheckBox("Select All")
        self.__select_all_checkbox.setTristate(True)
        self.__select_all_checkbox.stateChanged.connect(
            self.__slot_on_select_all_changed
        )

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.__select_all_checkbox)
        self.__grid_layout = QGridLayout()
        self.layout().addLayout(self.__grid_layout)  # type: ignore

    @property
    def max_col(self):
        """max_col: the maximum number of columns in the checkbox grid layout"""
        return self.__max_col

    @max_col.setter
    def max_col(self, value: int):
        self.__max_col = value
        self.__re_layout()

    @property
    def prefix(self):
        """prefix: the prefix of each checkbox"""
        return self.__prefix

    @prefix.setter
    def prefix(self, text: str):
        self.__prefix = text
        self.__re_layout()

    @property
    def selections(self) -> list[bool]:
        return [
            self.__grid_layout.itemAt(i).widget().isChecked()  # type: ignore
            for i in range(self.__grid_layout.count())
        ]

    @selections.setter
    def selections(self, value: list[bool]):
        for i in reversed(range(self.__grid_layout.count())):
            widget = self.__grid_layout.itemAt(i).widget()
            self.__grid_layout.removeWidget(widget)
            widget.deleteLater()
        for i, b in enumerate(value):
            check_box = QCheckBox(f"{self.__prefix} {i+1}")
            check_box.setChecked(b)
            check_box.stateChanged.connect(self.__slot_on_selection_changed)
            self.__grid_layout.addWidget(
                check_box, i // self.__max_col, i % self.__max_col
            )

        self.__select_all_checkbox.blockSignals(True)
        if all(value):
            self.__select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        elif not any(value):
            self.__select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.__select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self.__select_all_checkbox.blockSignals(False)

    def __iter__(self):
        yield from self.selections

    def __re_layout(self):
        self.selections = self.selections

    def __slot_on_select_all_changed(self, state: int):
        self.__select_all_checkbox.blockSignals(True)
        match state:
            case Qt.CheckState.Checked.value:
                self.selections = [True] * len(self.selections)
            case Qt.CheckState.Unchecked.value:
                self.selections = [False] * len(self.selections)
            case Qt.CheckState.PartiallyChecked.value:
                pass
        self.__select_all_checkbox.blockSignals(False)

    def __slot_on_selection_changed(self):
        self.__select_all_checkbox.blockSignals(True)
        if all(self.selections):
            self.__select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        elif not any(self.selections):
            self.__select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.__select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self.__select_all_checkbox.blockSignals(False)
