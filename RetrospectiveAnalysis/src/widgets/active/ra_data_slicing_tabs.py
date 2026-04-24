import sys
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QComboBox,
    QStackedWidget,
    QLabel,
    QHBoxLayout,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
)
from functools import partial
from typing import Callable
from scipy.signal import find_peaks
from numpy.typing import NDArray
import numpy as np
from scipy.ndimage import gaussian_filter1d
from math import ceil
import logging

logger = logging.getLogger(__name__)

def data_slicing_fixed_datapoints(
    data, 
    num_of_points: int,
    offset=0, 
    n=1000, 
    start_range: float = 0.1,
    stop_range: float = 0.0
):

    if start_range + stop_range > 1:
        raise ValueError("start_range + end_range must be between 0.0 - 1.0")

    minima = [i for i in range(offset + int(n * start_range), num_of_points, n)]
    maxima = [i - int(n * stop_range) for i in range(offset + n, num_of_points, n)]

    return minima, maxima, n


def data_slicing_min_max(
        data,
        num_of_points: int,
    ):

    if len(data) == 0:
        logger.warning("CSV does not have ramp reference channel. Cannot slice data using min/max.")
        raise
    
    else:
        minima, _ = find_peaks(
                    gaussian_filter1d(-data, 1),
                    prominence=(np.max(data) - np.min(data)) * 0.9,
                )
        maxima, _ = find_peaks(
                    gaussian_filter1d(data, 1),
                    prominence=(np.max(data) - np.min(data)) * 0.9,
                )
        
        length_period = int(np.round(np.mean(np.concatenate((np.diff(minima), np.diff(maxima))))))

        return minima, maxima, length_period


def data_slicing_derivative(
    out, data, n: int = 0, start_range: float = 0, stop_range: float = 0
):
    
    out_dt = np.diff(data[0])
    out_dt_new = [x if x >= 0.5 else 0 for x in out_dt]
    maxima, _ = find_peaks(out_dt_new, distance=ceil(0.75 * n))

    length_period = int(np.round(np.mean(np.diff(maxima))))
    start_indices = [i + int(length_period * start_range) for i in maxima[:-1]]
    stop_indices = [i - int(length_period * (stop_range)) for i in maxima[1:]]

    for i, j in zip(start_indices, stop_indices):
        print(i, j)

    return start_indices, stop_indices

class RaActiveDataSlicingWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.initUI()
        self.combo_box.currentIndexChanged.connect(self.show_page)

    def initUI(self):
        self.setWindowTitle("Data Slicing Method")
        self.setLayout(layout0 := QVBoxLayout())

        self.combo_box = QComboBox()
        self.combo_box.addItem("Minimum/Maximum")
        self.combo_box.addItem("Fixed Datapoints")
        # self.combo_box.addItem("Derivative")
        self.combo_box.setCurrentIndex(0)
        layout0.addWidget(self.combo_box)

        self.data_slicing_stacked_widget = QStackedWidget()
        self.slice_min_max_tab = SlicingMinMaxTab()
        self.slice_fixed_datapoint_tab = SlicingFixedDatapointsTab()
        self.data_slicing_stacked_widget.addWidget(self.slice_min_max_tab)
        self.data_slicing_stacked_widget.addWidget(self.slice_fixed_datapoint_tab)
        
        layout0.addWidget(self.data_slicing_stacked_widget)
        layout0.addWidget(close_button := QPushButton("Close"), alignment=Qt.AlignRight)
        close_button.clicked.connect(self.slot_close)

    def show_page(self, index):
        self.data_slicing_stacked_widget.setCurrentIndex(index)

    def slot_close(self):
        self.close()
class DataSlicingTabBase(QWidget):
    def to_slicing_func(self) -> Callable:
        ...

    def generate_sawtooth(self) -> Callable:
        ...


class SlicingMinMaxTab(DataSlicingTabBase):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

    def initUI(self):
        self.setLayout(QVBoxLayout())

    def to_slicing_func(self):
        return data_slicing_min_max


class SlicingFixedDatapointsTab(DataSlicingTabBase):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.initUI()

    def initUI(self):
        self.setLayout(layout := QHBoxLayout())
        label1 = QLabel("Fixed Datapoint:")

        self.fixed_datapoint = QSpinBox(value=1000)  # type: ignore
        self.fixed_datapoint.setMaximum(1000000)
        self.fixed_datapoint.setMinimum(1)

        self.offset = QSpinBox(value=100)  # type: ignore
        self.offset.setMaximum(1000000)
        self.offset.setMinimum(1)

        self.exclude_start_spinbox = QDoubleSpinBox(value=0, minimum=0, maximum=1.0)  # type: ignore
        self.exclude_start_spinbox.setSingleStep(0.01)
        self.exclude_stop_spinbox = QDoubleSpinBox(value=0, minimum=0, maximum=1.0)  # type: ignore
        self.exclude_stop_spinbox.setSingleStep(0.01)


        layout.addWidget(label1)
        layout.addWidget(self.fixed_datapoint)
        layout.addWidget(QLabel("Offset:"))
        layout.addWidget(self.offset)
        layout.addWidget(QLabel("Exclude Start %"))

        layout.addWidget(self.exclude_start_spinbox)
        layout.addWidget(QLabel("Exclude End %"))
        layout.addWidget(self.exclude_stop_spinbox)

    def to_slicing_func(self):
        return partial(
            data_slicing_fixed_datapoints,
            offset=int(self.offset.value()),
            n=int(self.fixed_datapoint.value()),
            start_range=float(self.exclude_start_spinbox.value()),
            stop_range=float(self.exclude_stop_spinbox.value()),
        )



class SlicingDerivativeTab(DataSlicingTabBase):
    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.initUI()

    def initUI(self):
        self.setLayout(layout := QHBoxLayout())
        label1 = QLabel("Estimated Datapoint")
        label2 = QLabel("Offset")

        self.estimated_datapoint = QSpinBox(value=1000)  # type: ignore
        self.estimated_datapoint.setMaximum(1000000)
        self.estimated_datapoint.setMinimum(1)
        self.offset = QSpinBox(value=100)  # type: ignore
        self.offset.setMaximum(1000000)
        self.offset.setMinimum(1)

        self.exclude_start_spinbox = QDoubleSpinBox(value=0, minimum=0, maximum=1.0)  # type: ignore
        self.exclude_start_spinbox.setSingleStep(0.05)
        self.exclude_stop_spinbox = QDoubleSpinBox(value=0, minimum=0, maximum=1.0)  # type: ignore
        self.exclude_stop_spinbox.setSingleStep(0.05)

        layout.addWidget(label1)
        layout.addWidget(self.estimated_datapoint)
        layout.addWidget(label2)
        layout.addWidget(self.offset)
        layout.addWidget(QLabel("Exclude Start %"))

        layout.addWidget(self.exclude_start_spinbox)
        layout.addWidget(QLabel("Exclude End %"))
        layout.addWidget(self.exclude_stop_spinbox)

    def to_slicing_func(self):
        return partial(
            data_slicing_derivative,
            n=int(self.estimated_datapoint.value()),
            start_range=float(self.exclude_start_spinbox.value()),
            stop_range=float(self.exclude_stop_spinbox.value()),
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = RaActiveDataSlicingWidget()
    w.show()

    sys.exit(app.exec_())
