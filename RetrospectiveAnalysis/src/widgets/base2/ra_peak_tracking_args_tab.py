from abc import abstractmethod
from collections.abc import Callable
from typing import Any, List

import numpy as np
from numpy.typing import NDArray
from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.lib import cosine_distance, euclidean_distance

# stackwidget and combobox for choosing between cosine similarity or euclidean distance

class RaPeakTrackingArgsWidget(QTabWidget):
    def __init__(self, parent=None):
        super(RaPeakTrackingArgsWidget, self).__init__(parent=parent)
        self.fsr_args_settings = RaPeakTrackingFSRSettings()
        self.addTab(self.fsr_args_settings, "FSR Settings")

        self.algo_args = RaPeakTrackingAlgoArgs()
        self.addTab(self.algo_args, "Peak Tracking Algorithm")

class RaPeakTrackingFSRSettings(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setWindowTitle("Peak Tracking (Beta)")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)  # type: ignore
        # variables
        self.default_fsr_val = 10
        self.expected_fsr = self.default_fsr_val

    def init_ui(self):
        # Create a QVBoxLayout for the main layout
        group_boxes_layout = QVBoxLayout()

        # First row: QSpinBox
        self.traces_num_value = QSpinBox(self)
        self.traces_num_value.setRange(1, 100)  # Set the range as needed
        self.traces_num_value.setValue(10)  # Set the default value

        first_groupbox = QGroupBox("Trace sweep threshold", self)
        first_layout = QHBoxLayout(first_groupbox)
        group_boxes_layout.addWidget(first_groupbox)

        first_layout.addWidget(QLabel("Minimum trace length"))
        first_layout.addWidget(self.traces_num_value)

        second_groupbox = QGroupBox("Accpetable shift between each sweep", self)
        second_layout = QGridLayout(second_groupbox)

        # Second row: 3 QLineEdits
        self.percentage_fsr_line = QLineEdit(self)
        self.percentage_fsr_line.setText("0.3")
        
        self.validator = QDoubleValidator()
        self.percentage_fsr_line.setValidator(self.validator)

        second_layout.addWidget(QLabel("Acceptable shift between each sweep FSR"), 1, 0)
        second_layout.addWidget(self.percentage_fsr_line, 1, 1)
        second_layout.addWidget(QLabel("* FSR"), 1, 2)
        group_boxes_layout.addWidget(second_groupbox)
    
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(group_boxes_layout)
        main_layout.addSpacerItem(QSpacerItem(0,0,QSizePolicy.Minimum, QSizePolicy.Expanding)) # type: ignore
    
    @property
    def percentage_fsr(self):
        return float(self.percentage_fsr_line.text())
    
    @property
    def traces_num(self):
        return int(self.traces_num_value.value())

class RaPeakTrackingAlgoArgs(QGroupBox):
    def __init__(self, parent=None):
        super(RaPeakTrackingAlgoArgs, self).__init__(parent=parent)

        self.setLayout(layout0 := QVBoxLayout())
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)  # type: ignore

        # combo box
        self.peakTrackingComboBox = QComboBox()
        self.peakTrackingComboBox.addItem("Cosine Similarity")
        self.peakTrackingComboBox.addItem("Euclidean Distance")

        # stacked widget
        self.layout1 = QHBoxLayout()
        self.peakTrackingStackedWidget = QStackedWidget(self)
        self.peakTrackingStackedWidget.setMinimumWidth(150)

        self.layout2 = QVBoxLayout()
        self.xWeightCheckBox = QCheckBox()
        self.x0WeightCheckBox = QCheckBox()
        self.y0WeightCheckBox = QCheckBox()
        self.gammaWeightCheckBox = QCheckBox()
        self.aWeightCheckBox = QCheckBox()
        self.weightCheckBoxes = [
            self.xWeightCheckBox,
            self.x0WeightCheckBox,
            self.y0WeightCheckBox,
            self.gammaWeightCheckBox,
            self.aWeightCheckBox,
        ]
        label = QLabel("Apply all\n channels:")
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.layout2.addWidget(label, alignment=QtCore.Qt.AlignRight)  # type: ignore
        for i in self.weightCheckBoxes:
            i.setChecked(True)
            self.layout2.addWidget(i, alignment=QtCore.Qt.AlignRight)
        self.layout2.setSpacing(0)
        self.layout1.addLayout(self.layout2)
        self.layout1.addWidget(self.peakTrackingStackedWidget)

        # add pages to stacked widget
        self.cosine_page = RaPeakTrackingArgsTab(CosineDistanceTab)
        self.euclidean_page = RaPeakTrackingArgsTab(EuclideanDistanceTab)

        self.peakTrackingStackedWidget.addWidget(self.cosine_page)
        self.peakTrackingStackedWidget.addWidget(self.euclidean_page)

        self.peakTrackingComboBox.currentIndexChanged.connect(
            lambda index: self.peakTrackingStackedWidget.setCurrentIndex(index)
        )
        layout0.addWidget(self.peakTrackingComboBox)
        layout0.addLayout(self.layout1)

    def export_weights(self):
        current_widget: RaPeakTrackingArgsTab = self.peakTrackingStackedWidget.currentWidget()  # type: ignore
        json_dump = {}
        json_dump["algorithm"] = self.peakTrackingComboBox.currentText()
        json_dump["peak tracking weights"] = [i.parameters for i in current_widget.tabs]

        return json_dump


class RaPeakTrackingDistanceTabBase(QWidget):
    @abstractmethod
    def to_distance_func(self) -> Callable[[NDArray, NDArray], float]:
        ...

    @property
    def parameters(self) -> List[float]:
        ...

    @parameters.setter
    def parameters(self, alvues: List[float]):
        ...


class CosineDistanceTab(RaPeakTrackingDistanceTabBase):
    def __init__(self, parent=None):
        super(CosineDistanceTab, self).__init__(parent=parent)

        self.setLayout(layout0 := QVBoxLayout())

        layout0.addWidget(QLabel("Weights"))
        self.weight1 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore
        self.weight2 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore
        self.weight3 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore
        self.weight4 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore
        self.weight5 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore

        parent_widget: RaPeakTrackingArgsTab = self.parentWidget()  # type: ignore
        self.weights = [
            self.weight1,
            self.weight2,
            self.weight3,
            self.weight4,
            self.weight5,
        ]

        self.weights_name = ["x", "x0", "y0", "gamma", "a"]

        for index, (name, weight) in enumerate(zip(self.weights_name, self.weights)):
            layout = QHBoxLayout()
            label = QLabel(f"{name}:")
            label.setMinimumWidth(50)
            layout.addWidget(label)
            layout.addWidget(weight, stretch=2)
            layout0.addLayout(layout)
            weight.valueChanged.connect(parent_widget.slot_value_changed)

    @property
    def parameters(self):
        return [i.value() for i in self.weights]

    @parameters.setter
    def parameters(self, values_index: tuple[List[float], int]):
        values = values_index[0]
        index = values_index[1]
        self.weights[index].setValue(values[index])

    def to_distance_func(self) -> Callable[[NDArray, NDArray], float]:
        weights = np.diag(self.parameters)

        return lambda a, b: cosine_distance(
            np.matmul(weights, a), np.matmul(weights, b)
        )


class EuclideanDistanceTab(RaPeakTrackingDistanceTabBase):
    def __init__(self, parent=None):
        super(EuclideanDistanceTab, self).__init__(parent=parent)

        self.layout0 = QVBoxLayout()
        self.setLayout(self.layout0)
        self.layout0.addWidget(QLabel("Weights"))

        self.weight1 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore
        self.weight2 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore
        self.weight3 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore
        self.weight4 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore
        self.weight5 = QDoubleSpinBox(value=1, singleStep=0.01, parent=self)  # type: ignore

        parent_widget: RaPeakTrackingArgsTab = self.parentWidget()  # type: ignore

        self.weights = [
            self.weight1,
            self.weight2,
            self.weight3,
            self.weight4,
            self.weight5,
        ]

        self.weights_name = ["x", "x0", "y0", "gamma", "a"]

        for index, (name, weight) in enumerate(zip(self.weights_name, self.weights)):
            layout = QHBoxLayout()
            label = QLabel(f"{name}:")
            label.setMinimumWidth(50)
            layout.addWidget(label)
            layout.addWidget(weight, stretch=2)
            self.layout0.addLayout(layout)
            weight.valueChanged.connect(parent_widget.slot_value_changed)

    @property
    def parameters(self):
        return [i.value() for i in self.weights]

    @parameters.setter
    def parameters(self, values_index: tuple[List[float], int]):
        values = values_index[0]
        index = values_index[1]
        self.weights[index].setValue(values[index])

    def to_distance_func(self) -> Callable[[NDArray, NDArray], float]:
        weights = np.diag(self.parameters)

        return lambda a, b: euclidean_distance(
            np.matmul(weights, a), np.matmul(weights, b)
        )


class RaPeakTrackingArgsTab(QTabWidget):
    def __init__(self, distance_class: Callable[[Any], RaPeakTrackingDistanceTabBase]):
        super().__init__()
        self.distance_class = distance_class

    def add_tab(self, channel_num):
        if self.count() != channel_num:
            self.clear()
            for i in range(channel_num):
                widget = self.distance_class(self)
                self.addTab(widget, str(self.count() + 1))

    @property
    def tabs(self) -> list[RaPeakTrackingDistanceTabBase]:
        return [self.widget(i) for i in range(self.count())]  # type: ignore

    def slot_value_changed(self, value):
        parent_widget: RaPeakTrackingArgsWidget = self.parentWidget().parentWidget()  # type: ignore

        sender: RaPeakTrackingDistanceTabBase = self.sender().parentWidget()  # type: ignore

        for index, i in enumerate(parent_widget.weightCheckBoxes):
            if i.isChecked():
                for tab in self.tabs:
                    tab.parameters = (sender.parameters, index)
