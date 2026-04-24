import logging
import os
import sys
from itertools import cycle
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from pyqtgraph import ImageView, PlotCurveItem, PlotItem, PlotWidget
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QTextCursor, QTransform
from PySide6.QtWidgets import (
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from scipy.io import savemat

from ..core.lib import SweepFitResult, group_peaks, lorentzian, peaks_to_traces_default
from ..widgets.lib.ra_channel_selector import RaChannelSelector
from ..widgets.lib.ra_drop_widgets import RaDropLineEdit, RaDropPushButton
from ..widgets.lib.ra_plot_curve_item import RaPlotCurveItem
from .ra_watcher_window import (
    DEFAULT_RESULT_FILENAME,
    DEFAULT_SPECTROGRAM_FILENAME,
    NP_PEAK_KEY,
    NP_SPECTROGRAM_KEY,
    NP_WAVELENGTH_KEY,
)

DEFAULT_OUTPUT_DIR_NAME = "RA_result"

logger = logging.getLogger(__name__)


class RaQuickAnalyzerWindow(QMainWindow):
    signal_close = Signal()
    signal_write = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(1440, 810)

        self.__central_widget = self.RaQuickAnalyzerWindowCentralWidget()
        self.setCentralWidget(self.__central_widget)

        self.__text_browser = QTextBrowser()
        dock_widget = QDockWidget()
        dock_widget.setWidget(self.__text_browser)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

        # connections
        self.__central_widget.signal_analyze.connect(self.__slot_analyze)
        self.__central_widget.signal_load.connect(self.__slot_load)
        self.__central_widget.signal_save.connect(self.__slot_save)
        self.__central_widget.file_number_spin_box.valueChanged.connect(
            self.__slot_file_number_changed
        )

        # redirect logging
        sys.stdout = self
        sys.stderr = self
        self.__log_handler = logging.StreamHandler(self)
        self.__log_handler.setFormatter(logging.getLogger().handlers[0].formatter)
        self.__log_handler.setLevel(logging.getLogger().handlers[0].level)
        logging.getLogger().addHandler(self.__log_handler)
        self.signal_write.connect(self.slot_write)

    def write(self, text):
        self.signal_write.emit(text)

    def flush(self):
        pass

    @Slot(str)
    def slot_write(self, text: str):
        self.__text_browser.moveCursor(QTextCursor.End)  # type: ignore
        self.__text_browser.insertPlainText(text)
        self.__text_browser.ensureCursorVisible()

    def closeEvent(self, event: QCloseEvent):
        self.signal_close.emit()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        logging.getLogger().removeHandler(self.__log_handler)
        return super().closeEvent(event)

    # slots
    def __slot_load(self, peak_file_path: str, spectrogram_file_path: str):
        self.__central_widget.peak_tracking_tab_widget.clear()
        self.__central_widget.spectrum_plot_tab_widget.clear()

        self.__sweep_2d: list[list[SweepFitResult]] = np.load(
            peak_file_path, allow_pickle=True
        )[NP_PEAK_KEY]
        self.__spectrograms = np.load(spectrogram_file_path, allow_pickle=True)[
            NP_SPECTROGRAM_KEY
        ]
        self.__wavelength = np.load(spectrogram_file_path, allow_pickle=True)[
            NP_WAVELENGTH_KEY
        ]

        if (s1 := (self.__sweep_2d.shape)) != (s2 := self.__spectrograms.shape[:2]):  # type: ignore
            logger.error(
                f"Peak and spectrogram file mismatch in shape. Peak file has {s1[0]} channels, spectrogram file has {s2[0]} channels. Peak file has {s1[1]} sweeps, spectrogram file has {s2[1]} sweeps."
            )
            return

        for i, _ in enumerate(self.__spectrograms):
            plot_widget = PlotWidget()
            plot_item: PlotItem = plot_widget.getPlotItem()
            plot_item.getAxis("bottom").setLabel("Wavelength", units="m")  # type: ignore
            plot_item.getAxis("bottom").setScale(1e-9)  # type: ignore
            plot_item.getAxis("left").setLabel("Power", units="dBm")  # type: ignore
            plot_item.addLegend()  # type: ignore
            self.__central_widget.spectrum_plot_tab_widget.addTab(
                plot_widget, f"Channel {i+1}"
            )

        self.__central_widget.file_number_spin_box.blockSignals(True)
        self.__central_widget.file_number_spin_box.setEnabled(True)
        self.__central_widget.file_number_spin_box.setValue(1)
        self.__central_widget.file_number_spin_box.setMaximum(s1[1])
        self.__central_widget.file_number_spin_box.setSuffix(f" (Max: {s1[1]})")
        self.__central_widget.file_number_spin_box.blockSignals(False)
        self.__slot_file_number_changed(1)

        self.__central_widget.channel_selector.selections = [True] * s1[0]

        self.__central_widget.analyze_button.setEnabled(True)
        self.__central_widget.save_button.setDisabled(True)

        self.__central_widget.signal_thresholds_changed.connect(
            self.__slot_thresholds_changed
        )

    def __slot_thresholds_changed(self):
        self.__slot_file_number_changed(
            self.__central_widget.file_number_spin_box.value()
        )

    def __slot_file_number_changed(self, n: int):
        r2_threshold, n100dbm_threshold = self.__central_widget.thresholds
        for channel_index in range(
            self.__central_widget.spectrum_plot_tab_widget.count()
        ):
            widget: PlotWidget = self.__central_widget.spectrum_plot_tab_widget.widget(
                channel_index
            )  # type: ignore
            widget.clear()
            widget.plot(
                x=self.__wavelength, y=self.__spectrograms[channel_index][n - 1]
            )
            color_palette = cycle(["r", "g", "b", "c", "m", "y", "k"])
            sweep = self.__sweep_2d[channel_index][n - 1]
            for i, p in enumerate(sweep.get_peaks(r2_threshold, n100dbm_threshold)):
                x0, _y0, _i, gamma, _a = p
                xs = np.linspace(x0 - 2 * gamma, x0 + 2 * gamma, 100)
                plot_curve_item = PlotCurveItem(
                    x=xs,
                    y=lorentzian(xs, *p),
                    pen=next(color_palette),
                    name=f"Peak {i+1} | ER:{sweep.get_er(r2_threshold,n100dbm_threshold)[i]:.4g} | Q:{sweep.get_q(r2_threshold,n100dbm_threshold)[i]:.4g}",
                )
                widget.addItem(plot_curve_item)

    def __slot_analyze(self):
        self.__central_widget.peak_tracking_tab_widget.clear()

        r2_threshold, n100dbm_threshold = self.__central_widget.thresholds
        channel_selections = {
            i for i, b in enumerate(self.__central_widget.channel_selector) if b
        }

        for i in channel_selections:
            channel: NDArray[np.floating] = self.__spectrograms[i]
            plot_widget = RaQuickAnalyzerPlotWidget(i)

            tr = QTransform()
            tr.translate(-0.5, min(self.__wavelength))
            tr.scale(
                1,
                (max(self.__wavelength) - min(self.__wavelength))
                / len(self.__wavelength),
            )

            plot_widget.image_view.setImage(channel, transform=tr)
            self.__central_widget.peak_tracking_tab_widget.addTab(
                plot_widget, f"Channel {i+1}"
            )

            sweeps = self.__sweep_2d[i]
            peaks = [
                sweep.get_peaks(r2_threshold, n100dbm_threshold) for sweep in sweeps
            ]
            traces, fsr = peaks_to_traces_default(peaks)

            color_palette = cycle(["light green", "blue"])
            x0 = 0
            for trace in traces:
                plot_widget.add_curve_item(
                    RaPlotCurveItem(
                        fsr,
                        x=np.linspace(x0, x0 + len(trace) - 1, len(trace)),
                        y=trace,
                        pen={
                            "color": next(color_palette),
                            "width": 5,
                            "cosmetic": True,
                        },
                    )
                )
                x0 += len(trace)

        self.__central_widget.save_button.setEnabled(True)

    def __slot_save(self, dir: str):
        dir = os.path.join(dir, DEFAULT_OUTPUT_DIR_NAME)
        os.makedirs(dir, exist_ok=True)
        peak_shift_path = os.path.join(dir, "peak_shifts.mat")
        peaks_path = os.path.join(dir, "peaks.mat")
        fsr_er_q_path = os.path.join(dir, "fsr_er_q.mat")
        all_tabs: list[RaQuickAnalyzerPlotWidget] = [  # type: ignore
            self.__central_widget.peak_tracking_tab_widget.widget(i)
            for i in range(self.__central_widget.peak_tracking_tab_widget.count())
        ]

        r2_threshold, n100dbm_threshold = self.__central_widget.thresholds

        # save peak shifts
        savemat(
            peak_shift_path,
            {
                (tab.name).replace(" ", "_").lower() + "_peakWL_list": tab.full_trace
                for tab in all_tabs
            },
        )

        # save all fitted peaks and peak trace indices
        savemat(
            peaks_path,
            {
                tab.name.replace(" ", "").lower(): np.array(
                    [
                        s.get_peaks(r2_threshold, n100dbm_threshold)
                        for s in self.__sweep_2d[tab.index]
                    ],
                    dtype="object",
                )
                for tab in all_tabs
            }
            | {
                tab.name.replace(" ", "").lower()
                + "_peak_trace_indices": np.array(
                    group_peaks(
                        [[p[0] for p in ps] for ps in [s.get_peaks() for s in self.__sweep_2d[tab.index]]],  # type: ignore
                        tab.full_trace,
                    ),
                    dtype="object",
                )
                for tab in all_tabs
            },
        )

        # save FSR, ER, Q
        savemat(
            fsr_er_q_path,
            {
                tab.name.replace(" ", "").lower()
                + "_fsr": np.array(
                    [
                        s.get_fsr(r2_threshold, n100dbm_threshold)
                        for s in self.__sweep_2d[tab.index]
                    ],
                    dtype="object",
                )
                for tab in all_tabs
            }
            | {
                tab.name.replace(" ", "").lower()
                + "_er": np.array(
                    [
                        s.get_er(r2_threshold, n100dbm_threshold)
                        for s in self.__sweep_2d[tab.index]
                    ],
                    dtype="object",
                )
                for tab in all_tabs
            }
            | {
                tab.name.replace(" ", "").lower()
                + "_q": np.array(
                    [
                        s.get_q(r2_threshold, n100dbm_threshold)
                        for s in self.__sweep_2d[tab.index]
                    ],
                    dtype="object",
                )
                for tab in all_tabs
            },
        )

    class RaQuickAnalyzerWindowCentralWidget(QWidget):
        signal_load = Signal(str, str)
        signal_analyze = Signal()
        signal_save = Signal(str)
        signal_thresholds_changed = Signal()

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setLayout(QHBoxLayout())

            # widgets
            self.__peak_file_path_line_edit = RaDropLineEdit()
            self.__peak_file_path_line_edit.signal_drop.connect(  # type: ignore
                self.__peak_file_path_line_edit.setText
            )
            self.__peak_file_select_button = RaDropPushButton("Select RA Peak File")
            self.__peak_file_select_button.signal_drop.connect(  # type: ignore
                self.__peak_file_path_line_edit.setText
            )

            self.__spectrogram_file_path_line_edit = RaDropLineEdit()
            self.__spectrogram_file_path_line_edit.signal_drop.connect(  # type: ignore
                self.__spectrogram_file_path_line_edit.setText
            )
            self.__spectrogram_file_select_button = RaDropPushButton(
                "Select RA Spectrogram File"
            )
            self.__spectrogram_file_select_button.signal_drop.connect(  # type: ignore
                self.__spectrogram_file_path_line_edit.setText
            )

            self.__load_button = QPushButton("Load")

            self.__r2_threshold_double_spin_box = QDoubleSpinBox()
            self.__r2_threshold_double_spin_box.setValue(0.7)
            self.__r2_threshold_double_spin_box.setDecimals(4)
            self.__r2_threshold_double_spin_box.setMinimum(0)
            self.__r2_threshold_double_spin_box.setMaximum(1)
            self.__r2_threshold_double_spin_box.setSingleStep(0.01)
            self.__r2_threshold_double_spin_box.setPrefix("R2 > ")

            self.__n100dbm_threshold_spin_box = QSpinBox()
            self.__n100dbm_threshold_spin_box.setValue(30)
            self.__n100dbm_threshold_spin_box.setMinimum(0)
            self.__n100dbm_threshold_spin_box.setPrefix("#-100dBm < ")

            self.__file_number_spin_box = QSpinBox()
            self.__file_number_spin_box.setPrefix("Sweep #")
            self.__file_number_spin_box.setDisabled(True)
            self.__file_number_spin_box.setMinimum(1)

            self.__spectrum_plot_tab_widget = QTabWidget()

            self.__analyze_button = QPushButton("Analyze")
            self.__analyze_button.setDisabled(True)

            self.__save_button = QPushButton("Save Result")
            self.__save_button.setDisabled(True)

            self.__peak_tracking_tab_widget = QTabWidget()

            # layout
            grid_layout = QGridLayout()
            grid_layout.addWidget(self.__peak_file_path_line_edit, 0, 0)
            grid_layout.addWidget(self.__peak_file_select_button, 0, 1)
            grid_layout.addWidget(self.__spectrogram_file_path_line_edit, 1, 0)
            grid_layout.addWidget(self.__spectrogram_file_select_button, 1, 1)

            thresholds_layout = QHBoxLayout()
            thresholds_layout.addWidget(self.__r2_threshold_double_spin_box)
            thresholds_layout.addWidget(self.__n100dbm_threshold_spin_box)

            left_widget = QWidget()
            left_widget.setLayout(QVBoxLayout())
            left_widget.layout().addLayout(grid_layout)  # type: ignore
            left_widget.layout().addWidget(self.__load_button)
            left_widget.layout().addLayout(thresholds_layout)  # type: ignore
            left_widget.layout().addWidget(self.__file_number_spin_box)
            left_widget.layout().addWidget(self.__spectrum_plot_tab_widget)

            # self.__channel_selection_grid_layout = QGridLayout()
            # left_widget.layout().addLayout(self.__channel_selection_grid_layout)  # type: ignore

            self.__channel_selector = RaChannelSelector()
            left_widget.layout().addWidget(self.__channel_selector)  # type: ignore

            left_widget.layout().addWidget(self.__analyze_button)
            left_widget.layout().addWidget(self.__save_button)
            left_widget.layout().addSpacerItem(  # type: ignore
                QSpacerItem(
                    0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
                )
            )

            splitter = QSplitter(Qt.Orientation.Horizontal)
            splitter.addWidget(left_widget)
            splitter.setStretchFactor(0, 0)
            splitter.addWidget(self.__peak_tracking_tab_widget)
            splitter.setStretchFactor(1, 1)

            self.layout().addWidget(splitter)

            # connections
            self.__peak_file_select_button.clicked.connect(self.__slot_peak_file_select)
            self.__spectrogram_file_select_button.clicked.connect(
                self.__slot_spectrogram_file_select
            )
            self.__load_button.clicked.connect(self.__slot_load)
            self.__r2_threshold_double_spin_box.valueChanged.connect(
                self.__slot_thresholds_changed
            )
            self.__n100dbm_threshold_spin_box.valueChanged.connect(
                self.__slot_thresholds_changed
            )
            self.__analyze_button.clicked.connect(self.__slot_analyze)
            self.__save_button.clicked.connect(self.__slot_save)

        @property
        def file_number_spin_box(self):
            return self.__file_number_spin_box

        @property
        def thresholds(self):
            return (
                self.__r2_threshold_double_spin_box.value(),
                self.__n100dbm_threshold_spin_box.value(),
            )

        @property
        def spectrum_plot_tab_widget(self):
            return self.__spectrum_plot_tab_widget

        @property
        def channel_selector(self):
            return self.__channel_selector

        @property
        def analyze_button(self):
            return self.__analyze_button

        @property
        def save_button(self):
            return self.__save_button

        @property
        def peak_tracking_tab_widget(self):
            return self.__peak_tracking_tab_widget

        def __is_valid(self):
            return os.path.isfile(
                self.__peak_file_path_line_edit.text()
            ) and os.path.isfile(self.__spectrogram_file_path_line_edit.text())

        # slots
        def __slot_peak_file_select(self):
            file_path = QFileDialog.getOpenFileName(
                self, "Select RA Peak", filter=f"RA Peak ({DEFAULT_RESULT_FILENAME})"
            )
            self.__peak_file_path_line_edit.setText(file_path[0])

        def __slot_spectrogram_file_select(self):
            file_path = QFileDialog.getOpenFileName(
                self,
                "Select RA Spectrogram",
                filter=f"RA Spectrogram ({DEFAULT_SPECTROGRAM_FILENAME})",
            )
            self.__spectrogram_file_path_line_edit.setText(file_path[0])

        def __slot_load(self):
            if self.__is_valid():
                self.signal_load.emit(
                    self.__peak_file_path_line_edit.text(),
                    self.__spectrogram_file_path_line_edit.text(),
                )

        def __slot_thresholds_changed(self):
            self.signal_thresholds_changed.emit()

        def __slot_analyze(self):
            if self.__is_valid():
                self.signal_analyze.emit()

        def __slot_save(self):
            if dir := QFileDialog.getExistingDirectory(
                self,
                "Select Directory to Save Result",
                str(Path(self.__peak_file_path_line_edit.text()).parent),
                options=QFileDialog.Option.ShowDirsOnly,
            ):
                self.signal_save.emit(dir)


class RaQuickAnalyzerPlotWidget(QWidget):
    def __init__(self, index: int, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__index = index
        self.__name = f"Channel {index+1}"
        self.__curve_items: list[RaPlotCurveItem] = []

        # initialize members
        self.__plot_item = PlotItem()
        self.__plot_item.getAxis("bottom").setLabel("Sweep Number")
        self.__plot_item.getAxis("left").setLabel("Wavelength", units="m")
        self.__plot_item.getAxis("left").setScale(1e-9)
        self.__plot_item.setTitle(f"{self.__name} Spectrogram")

        self.__image_view = ImageView(view=self.__plot_item)
        self.__image_view.ui.roiBtn.hide()
        self.__image_view.ui.menuBtn.hide()
        self.__image_view.getView().invertY(False)
        self.__image_view.getView().setAspectLocked(False)
        self.__image_view.setColorMap(pg.colormap.getFromMatplotlib("inferno"))

        # layout widgets
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.__image_view)

    @property
    def plot_item(self):
        return self.__plot_item

    @property
    def curve_items(self):
        return self.__curve_items

    @property
    def image_view(self):
        return self.__image_view

    @property
    def name(self):
        return self.__name

    @property
    def index(self):
        return self.__index

    def add_curve_item(self, curve_item: RaPlotCurveItem):
        self.__plot_item.addItem(curve_item)
        self.__curve_items.append(curve_item)

    @property
    def full_trace(self):
        return np.concatenate([curve_item.yData for curve_item in self.__curve_items])  # type: ignore
