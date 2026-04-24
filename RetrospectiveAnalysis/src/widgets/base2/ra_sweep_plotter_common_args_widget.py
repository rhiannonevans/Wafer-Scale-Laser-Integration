from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QPushButton,
    QTabWidget,
    QHBoxLayout,
    QDoubleSpinBox,
    QSpinBox,
    QLabel,
    QGridLayout,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QSizePolicy,
)
from PySide6 import QtCore
from functools import partial


# TAB WIDGET for peak finding settings
class PeakFindingSettingsTabWidget(QWidget):
    apply_val = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(PeakFindingSettingsTabWidget, self).__init__(parent=parent)
        self.initUI()

        self.checkboxes = [
            self.r2CheckBox,
            self.n100dBmCheckBox,
            self.gaussianCheckBox,
            self.prominenceCheckBox,
        ]

        for index, i in enumerate(self.checkboxes):
            i.toggled.connect(partial(self.checkbox_toggled, index=index))

        self.reset.clicked.connect(self.slot_reset)
        self.resetAll.clicked.connect(self.slot_reset_all)

    def initUI(self):
        self.layout1 = QVBoxLayout()
        self.setLayout(self.layout1)
        self.resize(350, 250)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)  # type: ignore
        self.setWindowTitle("Peak Finding Settings")

        self.tabWidget = QTabWidget()

        self.configStatus = QGroupBox()
        # self.configStatus.setStyleSheet("QGroupBox { margin-top: 23px; }")
        self.boxLayout = QVBoxLayout()
        self.configStatus.setLayout(self.boxLayout)

        self.r2CheckBox = QCheckBox()
        self.n100dBmCheckBox = QCheckBox()
        self.gaussianCheckBox = QCheckBox()
        self.prominenceCheckBox = QCheckBox()

        self.r2CheckBox.setChecked(True)
        self.n100dBmCheckBox.setChecked(True)
        self.gaussianCheckBox.setChecked(True)
        self.prominenceCheckBox.setChecked(True)

        label = QLabel("Apply all\n channels:", alignment=QtCore.Qt.AlignRight)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.boxLayout.addWidget(label)
        self.boxLayout.addWidget(self.r2CheckBox, alignment=QtCore.Qt.AlignRight)
        self.boxLayout.addWidget(self.n100dBmCheckBox, alignment=QtCore.Qt.AlignRight)
        self.boxLayout.addWidget(self.gaussianCheckBox, alignment=QtCore.Qt.AlignRight)
        self.boxLayout.addWidget(
            self.prominenceCheckBox, alignment=QtCore.Qt.AlignRight
        )

        self.layout0 = QHBoxLayout()
        self.layout0.addWidget(self.configStatus)
        self.layout0.addWidget(self.tabWidget)
        self.layout0.setStretch(1, 2)

        self.apply = QPushButton("Apply")
        self.reset = QPushButton("Reset")
        self.resetAll = QPushButton("Reset all channels")

        self.layout1.addLayout(self.layout0)
        self.layout1.addWidget(self.apply)
        self.layout1.addWidget(self.reset)
        self.layout1.addWidget(self.resetAll)

    def add_tab(self):
        index = self.tabWidget.count()
        self.tabWidget.addTab(PeakFindingSettings(self), str(index + 1))

    @property
    def r2_threshold(self):  # list of r2 threshold from each tab
        return [self.tabWidget.widget(i).r2_threshold for i in range(self.tabWidget.count())]  # type: ignore

    @property
    def n100dBm_tolerance(self):  # list of n100dBm tolerance from each tab
        return [self.tabWidget.widget(i).n100dBm_tolerance for i in range(self.tabWidget.count())]  # type: ignore

    @property
    def gaussian_filter(self):  # list of gaussian filter from each tab
        return [self.tabWidget.widget(i).gaussian_filter for i in range(self.tabWidget.count())]  # type: ignore

    @property
    def prominence_scalar(self):  # list of prominence scalar from each tab
        return [self.tabWidget.widget(i).prominence_scalar for i in range(self.tabWidget.count())]  # type: ignore

    def checkbox_toggled(self, state, index):
        tab_ind = self.tabWidget.currentIndex()

        if state:
            for i in range(self.tabWidget.count()):
                tab: PeakFindingSettings = self.tabWidget.widget(i)  # type: ignore
                if index == 0:
                    tab.r2_threshold = self.r2_threshold[tab_ind]
                if index == 1:
                    tab.n100dBm_tolerance = self.n100dBm_tolerance[tab_ind]
                if index == 2:
                    tab.gaussian_filter = self.gaussian_filter[tab_ind]
                if index == 3:
                    tab.prominence_scalar = self.prominence_scalar[tab_ind]

    def slot_value_changed(self, value, index):
        states = [i.isChecked() for i in self.checkboxes]

        if states[index]:
            for i in range(self.tabWidget.count()):
                tab: PeakFindingSettings = self.tabWidget.widget(i)  # type: ignore
                if index == 0:
                    tab.r2_threshold = value
                if index == 1:
                    tab.n100dBm_tolerance = value
                if index == 2:
                    tab.gaussian_filter = value
                if index == 3:
                    tab.prominence_scalar = value

    def slot_reset(self):
        index = self.tabWidget.currentIndex()
        tab: PeakFindingSettings = self.tabWidget.widget(index)  # type: ignore
        tab.r2_threshold = 0.7
        tab.n100dBm_tolerance = 20
        tab.gaussian_filter = 8
        tab.prominence_scalar = 0.1

        self.apply.click()

    def slot_reset_all(self):
        for i in range(self.tabWidget.count()):
            tab: PeakFindingSettings = self.tabWidget.widget(i)  # type: ignore
            tab.r2_threshold = 0.7
            tab.n100dBm_tolerance = 20
            tab.gaussian_filter = 8
            tab.prominence_scalar = 0.1

        self.apply.click()


# INDIVIDUAL peak finding tab layout
class PeakFindingSettings(QWidget):
    def __init__(self, parent=None):
        super(PeakFindingSettings, self).__init__(parent=parent)

        self.widget_layout = QGridLayout()
        self.setLayout(self.widget_layout)
        self.r2ThresholdDoubleSpinBox = QDoubleSpinBox(
            maximum=1.00, singleStep=0.01, value=0.70, decimals=2  # type: ignore
        )
        self.n100dBmToleranceSpinBox = QSpinBox(maximum=999999999, value=20)  # type: ignore
        self.gaussianFilterSpinBox = QDoubleSpinBox(maximum=99, singleStep=0.01, value=8, minimum=0.0001)  # type: ignore
        self.promineceScalarSpinBox = QDoubleSpinBox(maximum=99, singleStep=0.01, value=0.10)  # type: ignore
        self.spinBoxes = [
            self.r2ThresholdDoubleSpinBox,
            self.n100dBmToleranceSpinBox,
            self.gaussianFilterSpinBox,
            self.promineceScalarSpinBox,
        ]

        self.widget_layout.addWidget(QLabel("R2 Threshold:"), 0, 0)
        self.widget_layout.addWidget(self.r2ThresholdDoubleSpinBox, 0, 1)
        self.widget_layout.addWidget(QLabel("100dBm Threshold:"), 1, 0)
        self.widget_layout.addWidget(self.n100dBmToleranceSpinBox, 1, 1)
        self.widget_layout.addWidget(QLabel("Gaussian Filter:"), 2, 0)
        self.widget_layout.addWidget(self.gaussianFilterSpinBox, 2, 1)
        self.widget_layout.addWidget(QLabel("Prominence Scalar:"), 3, 0)
        self.widget_layout.addWidget(self.promineceScalarSpinBox, 3, 1)
        self.widget_layout.setColumnStretch(1, 2)

        for index, i in enumerate(self.spinBoxes):
            parent_widget: PeakFindingSettingsTabWidget = self.parentWidget()  # type: ignore
            i.valueChanged.connect(
                partial(parent_widget.slot_value_changed, index=index)
            )

    @property
    def r2_threshold(self):
        return self.r2ThresholdDoubleSpinBox.value()

    @r2_threshold.setter
    def r2_threshold(self, value):
        self.r2ThresholdDoubleSpinBox.setValue(value)

    @property
    def n100dBm_tolerance(self):
        return self.n100dBmToleranceSpinBox.value()

    @n100dBm_tolerance.setter
    def n100dBm_tolerance(self, value):
        self.n100dBmToleranceSpinBox.setValue(value)

    @property
    def gaussian_filter(self):
        return self.gaussianFilterSpinBox.value()

    @gaussian_filter.setter
    def gaussian_filter(self, value):
        self.gaussianFilterSpinBox.setValue(value)

    @property
    def prominence_scalar(self):
        return self.promineceScalarSpinBox.value()

    @prominence_scalar.setter
    def prominence_scalar(self, value):
        self.promineceScalarSpinBox.setValue(value)


class AnalyzerSettingsWidget(QGroupBox):
    def __init__(self, parent=None):
        super(AnalyzerSettingsWidget, self).__init__(parent=parent)
        self.initUI()

    def initUI(self):
        # set layout
        self.setTitle("File Settings")
        self.groupBoxLayout = QVBoxLayout(self)

        # group box
        self.analyzerLayout = QGridLayout()
        self.analyzerLayout.setColumnStretch(1, 2)
        self.groupBoxLayout.addLayout(self.analyzerLayout)

        # labels
        self.analyzerLayout.addWidget(QLabel("Timestamp File/Number"), 0, 0)
        self.analyzerLayout.addWidget(QLabel("Time Multiplier:"), 1, 0)
        self.analyzerLayout.addWidget(QLabel("Data File Pattern (RegEx):"), 2, 0)

        # line edits
        self.timestampComboBox = QComboBox()
        self.timestampComboBox.setEditable(True)
        self.timestampComboBox.addItem("0.25")
        self.timestampComboBox.setCurrentText("0.25")
        self.timeMultiplierLineEdit = QLineEdit("1/60")
        self.timeMultiplierUnitLineEdit = QLineEdit("min")
        self.dataFilePatternLineEdit = QLineEdit('r".*sweep_(\\d+)\\.mat"')
        
        self.dataFilePatternLineEdit.setToolTip(
        """.* match any sequence of characters e.g "sweep_1.mat" -> ".*"
        \\ turn special regEx characters into normal characters e.g. "sweep_1.mat" -> ".*\\.mat"
        \\d matches a digit (equal to [0-9]) e.g. "sweep_1.mat" -> ".*\\d\\.mat"
        + matches 1 or more repetitions of the preceding symbol. e.g. "sweep_1.mat" -> ".*\\d+\\.mat"
        () capture group/number use for sorting files e.g. "sweep_1.mat" -> ".*(\\d+)\\.mat"  """ 
        )
        self.timeLayout = QHBoxLayout()
        self.timeLayout.addWidget(self.timeMultiplierLineEdit)
        self.timeLayout.addWidget(self.timeMultiplierUnitLineEdit)

        # button
        self.loadFilesButton = QPushButton("Load .matlab Settings")
        self.analyzerLayout.addWidget(self.timestampComboBox, 0, 1)
        self.analyzerLayout.addLayout(self.timeLayout, 1, 1)
        self.analyzerLayout.addWidget(self.dataFilePatternLineEdit, 2, 1)

        self.buttonLayout = QVBoxLayout()
        self.buttonLayout.addWidget(self.loadFilesButton)
        self.groupBoxLayout.addLayout(self.buttonLayout)

    @property
    def timestamp(self):
        return self.timestampComboBox.currentText()

    @property
    def timeMultiplier(self):
        return self.timeMultiplierLineEdit.text()

    @property
    def timeMultiplierUnit(self):
        return self.timeMultiplierUnitLineEdit.text()

    @property
    def dataFilePattern(self):
        return self.dataFilePatternLineEdit.text()
