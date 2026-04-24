from functools import reduce
from typing import Optional

import control
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from scipy.signal import lti, tf2zpk


# Wavelength Conversion Methods
class ConversionTabBase(QWidget):
    def to_lti(self) -> lti:
        ...


class ConversionZPTFTab(ConversionTabBase):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setLayout(QVBoxLayout())

        equation = QSvgWidget(
            ":/equations/resources/equations/wavelength_conversion_zp.svg"
        )
        equation.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)

        self.__zp_row_layout = QHBoxLayout()

        self.__zp_row_layout.addWidget(QLabel("Zeros:"))
        self.__zeros_line_edit = QLineEdit("[]")
        self.__zp_row_layout.addWidget(self.__zeros_line_edit)

        self.__zp_row_layout.addWidget(QLabel("Poles:"))
        self.__poles_line_edit = QLineEdit("[-1000]")
        self.__zp_row_layout.addWidget(self.__poles_line_edit)

        layout: QVBoxLayout = self.layout()  # type: ignore
        layout.addWidget(equation)
        layout.addLayout(self.__zp_row_layout)

    def to_lti(self):
        print(" --- LTI TF ---")
        print("Zeroes:")
        print(np.array(eval(self.__zeros_line_edit.text())))
        print("Poles:")
        print(np.array(eval(self.__poles_line_edit.text())))
        print(control.dcgain(control.tf(np.array(eval(self.__zeros_line_edit.text())), np.array(eval(self.__poles_line_edit.text())))))
        return lti(
            zeros := np.array(eval(self.__zeros_line_edit.text())),
            poles := np.array(eval(self.__poles_line_edit.text())),
            1 / control.dcgain(control.zpk(zeros, poles, 1)),
        )  
    
    @property
    def zs_line_edit(self):
        return self.__zeros_line_edit
    
    @property
    def ps_line_edit(self):
        return self.__poles_line_edit


class ConversionNumDenTFTab(ConversionTabBase):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setLayout(QVBoxLayout())

        equation = QSvgWidget(
            ":/equations/resources/equations/wavelength_conversion_NumDenom.svg"
        )
        equation.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)

        self.__NumDemon_row_layout = QHBoxLayout()

        self.__NumDemon_row_layout.addWidget(QLabel("Numerator:"))
        self.__Num_line_edit = QLineEdit("[1]")
        self.__NumDemon_row_layout.addWidget(self.__Num_line_edit)

        self.__NumDemon_row_layout.addWidget(QLabel("Denominator:"))
        self.__Denom_line_edit = QLineEdit("[1]")
        self.__NumDemon_row_layout.addWidget(self.__Denom_line_edit)

        layout: QVBoxLayout = self.layout()  # type: ignore
        layout.addWidget(equation)
        layout.addLayout(self.__NumDemon_row_layout)

    def to_lti(self):
        print(" --- LTI TF ---")
        print("Numerator:")
        print(np.array(eval(self.__Num_line_edit.text())))
        print("Denominator:")
        print(np.array(eval(self.__Denom_line_edit.text())))
        print(control.dcgain(control.tf(np.array(eval(self.__Num_line_edit.text())), np.array(eval(self.__Denom_line_edit.text())))))
        Numerator   = np.array(eval(self.__Num_line_edit.text()))
        Denominator = np.array(eval(self.__Denom_line_edit.text()))
        #return lti(
        #    Numerator := np.array(eval(self.__Num_line_edit.text())),
        #    Denominator := np.array(eval(self.__Denom_line_edit.text())),
        #    1 / control.dcgain(control.tf(Numerator, Denominator)),
        #)
        z, p, _k = tf2zpk(Numerator, Denominator)
        return lti(
            z,
            p,
            1 / control.dcgain(control.zpk(z, p, 1)),
        )
    
    @property
    def num_line_edit(self):
        return self.__Num_line_edit
    
    @property
    def denom_line_edit(self):
        return self.__Denom_line_edit
    
class ConversionRCTFTab(ConversionTabBase):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setLayout(QHBoxLayout())

        equation = QSvgWidget(
            ":/equations/resources/equations/wavelength_conversion_rc.svg"
        )
        equation.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.layout().addWidget(equation)

        parameter_layout = QVBoxLayout()

        label_r = QLabel("R Array:")
        label_r.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        parameter_layout.addWidget(label_r)
        self.__rs_line_edit = QLineEdit("[0.95, 10, 0, 0]")
        parameter_layout.addWidget(self.__rs_line_edit)

        label_c = QLabel("C Array:")
        label_c.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        parameter_layout.addWidget(label_c)
        self.__cs_line_edit = QLineEdit("[20e-6, 200e-3, 1, 1]")
        parameter_layout.addWidget(self.__cs_line_edit)

        label_gain = QLabel("Gain:")
        label_gain.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        parameter_layout.addWidget(label_gain)
        self.__gain_double_spinbox = QDoubleSpinBox()
        self.__gain_double_spinbox.setDecimals(4)
        self.__gain_double_spinbox.setSingleStep(1)
        self.__gain_double_spinbox.setRange(
            np.iinfo(np.int32).min, np.iinfo(np.int32).max
        )
        self.__gain_double_spinbox.setValue(1)
        parameter_layout.addWidget(self.__gain_double_spinbox)

        self.layout().addLayout(parameter_layout)  # type: ignore

    def to_lti(self):
        Rs = np.array(eval(self.__rs_line_edit.text()))
        Cs = np.array(eval(self.__cs_line_edit.text()))

        if len(Rs) != len(Cs):
            raise ValueError("The length of R and C must be the same")

        num, den = reduce(  # polynomial fraction addition
            # TF for each RC layer: R/(RC*s + 1)
            lambda acc, c_r: [
                np.polymul(acc[0], np.poly1d([c_r[0] * c_r[1], 1]))
                + np.polymul(acc[1], np.poly1d([c_r[1]])),
                np.polymul(acc[1], np.poly1d([c_r[0] * c_r[1], 1])),
            ],
            zip(Cs, Rs),
            [np.poly1d(0), np.poly1d(1)],
        )
        z, p, _k = tf2zpk(num, den)
        return lti(
            z,
            p,
            self.__gain_double_spinbox.value() / control.dcgain(control.zpk(z, p, 1)),
        )

    @property
    def rs_line_edit(self):
        return self.__rs_line_edit

    @property
    def cs_line_edit(self):
        return self.__cs_line_edit

    @property
    def gain_double_spinbox(self):
        return self.__gain_double_spinbox
