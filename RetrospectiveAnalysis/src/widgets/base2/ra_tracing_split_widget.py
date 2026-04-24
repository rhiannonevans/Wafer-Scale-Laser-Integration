import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PeakTracingSplitWidget(QWidget):
    def __init__(self, qt_signal=None):
        super().__init__()
        self.initUI()
        self.setWindowFlags(Qt.WindowStaysOnTopHint) # type: ignore

    def initUI(self):
        layout = QVBoxLayout(self)

        sweep_layout = QHBoxLayout()
        self.sweep_spinbox = QSpinBox()
        self.sweep_spinbox.setMaximum(5000)
        self.add_sweep_button = QPushButton("Add")
        sweep_layout.addWidget(QLabel("Sweep Number to Split:"))
        sweep_layout.addWidget(self.sweep_spinbox)
        sweep_layout.addWidget(self.add_sweep_button)

        layout.addLayout(sweep_layout)

        self.reset_button = QPushButton("Reset")
        layout.addWidget(self.reset_button)
        layout.setAlignment(self.reset_button, Qt.AlignCenter) # type: ignore

        self.setLayout(layout)

    @property
    def sweep(self):
        return self.sweep_spinbox.value()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = PeakTracingSplitWidget()
    ex.show()
    sys.exit(app.exec())