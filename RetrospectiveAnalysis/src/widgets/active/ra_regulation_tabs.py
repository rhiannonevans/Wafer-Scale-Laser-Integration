from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from ...core.active_tools import ConverterConfig


# Input Regulation Methods
class RegulationTabBase(QWidget):
    def to_regulate_function(self) -> Callable[[float], float]:
        ...


class RegulationPhaseShifterTab(RegulationTabBase):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setLayout(QVBoxLayout())

        first_row_layout = QHBoxLayout()
        parameter_layout = QVBoxLayout()

        self.__fsr_double_spinbox = QDoubleSpinBox()
        self.__fsr_double_spinbox.setMaximum(1e4)
        self.__fsr_double_spinbox.setMinimum(0)
        self.__fsr_double_spinbox.setDecimals(6)
        self.__fsr_double_spinbox.setValue(0.085)
        self.__fsr_double_spinbox.setPrefix("FSR: ")
        self.__fsr_double_spinbox.setSuffix(" (nm)")
        self.__fsr_double_spinbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        parameter_layout.addWidget(self.__fsr_double_spinbox)

        self.__p_fsr_double_spinbox = QDoubleSpinBox()
        self.__p_fsr_double_spinbox.setMaximum(1e5)
        self.__p_fsr_double_spinbox.setMinimum(0)
        self.__p_fsr_double_spinbox.setDecimals(6)
        self.__p_fsr_double_spinbox.setValue(22)
        self.__p_fsr_double_spinbox.setPrefix("P_FSR: ")
        self.__p_fsr_double_spinbox.setSuffix(" (mW)")
        self.__p_fsr_double_spinbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        parameter_layout.addWidget(self.__p_fsr_double_spinbox)

        self.__v_offset_double_spinbox = QDoubleSpinBox()
        self.__v_offset_double_spinbox.setMaximum(1e4)
        self.__v_offset_double_spinbox.setMinimum(-1e4)
        self.__v_offset_double_spinbox.setDecimals(6)
        self.__v_offset_double_spinbox.setValue(0)
        self.__v_offset_double_spinbox.setPrefix("V_offset: ")
        self.__v_offset_double_spinbox.setSuffix(" (V)")
        self.__v_offset_double_spinbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        parameter_layout.addWidget(self.__v_offset_double_spinbox)

        self.__r_double_spinbox = QDoubleSpinBox()
        self.__r_double_spinbox.setValue(40)
        self.__r_double_spinbox.setMaximum(1e6)
        self.__r_double_spinbox.setMinimum(0)
        self.__r_double_spinbox.setDecimals(6)
        self.__r_double_spinbox.setPrefix("R: ")
        self.__r_double_spinbox.setSuffix(" (Ohm)")
        self.__r_double_spinbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        parameter_layout.addWidget(self.__r_double_spinbox)

        equation = QSvgWidget(
            ":/equations/resources/equations/regulation_phase_shifter.svg"
        )
        equation.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)

        first_row_layout.addWidget(equation)
        first_row_layout.addLayout(parameter_layout)
        self.layout().addLayout(first_row_layout)  # type: ignore
        self.layout().addSpacerItem(  # type: ignore
            QSpacerItem(
                0, 0, QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
        )

    def to_regulate_function(self) -> Callable[[float], float]:
        return ConverterConfig.ConvertMethod2(
            fsr=self.__fsr_double_spinbox.value(),
            p_fsr=self.__p_fsr_double_spinbox.value(),
            r_heater=self.__r_double_spinbox.value(),
            v_offset=self.__v_offset_double_spinbox.value(),
        )

    @property
    def fsr_double_spinbox(self):
        return self.__fsr_double_spinbox

    @property
    def p_fsr_double_spinbox(self):
        return self.__p_fsr_double_spinbox

    @property
    def v_offset_double_spinbox(self):
        return self.__v_offset_double_spinbox

    @property
    def r_double_spinbox(self):
        return self.__r_double_spinbox


class RegulationPolynomialTab(RegulationTabBase):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setLayout(QVBoxLayout())

        parameter_layout = QHBoxLayout()

        label_ai = QLabel("Ai Array:")
        label_ai.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        parameter_layout.addWidget(label_ai)
        self.__a_array_line_edit = QLineEdit("[]")
        parameter_layout.addWidget(self.__a_array_line_edit)

        label_xi = QLabel("Xi Array:")
        label_xi.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        parameter_layout.addWidget(label_xi)
        self.__x_array_line_edit = QLineEdit("[]")
        parameter_layout.addWidget(self.__x_array_line_edit)

        equation = QSvgWidget(
            ":/equations/resources/equations/regulation_polynomial.svg"
        )
        equation.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)

        self.layout().addWidget(equation)  # type: ignore
        self.layout().addLayout(parameter_layout)  # type: ignore
        self.layout().addSpacerItem(  # type: ignore
            QSpacerItem(
                0, 0, QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
        )

    def to_regulate_function(self) -> Callable[[float], float]:
        return ConverterConfig.ConvertMethod1(
            list(eval(self.__a_array_line_edit.text())),
            list(eval(self.__x_array_line_edit.text())),
        )

    @property
    def a_array_line_edit(self):
        return self.__a_array_line_edit

    @property
    def x_array_line_edit(self):
        return self.__x_array_line_edit
