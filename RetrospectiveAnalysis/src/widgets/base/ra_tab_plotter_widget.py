from __future__ import annotations

import logging
import os

import numpy as np
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.lib import SweepFitResult, lorentzian
from ...core.passive_tools import PassiveAnalyzer, read_mat
from .ra_figure_widget import RaFigureWidget

logger = logging.getLogger(__name__)


class RaFilePlotterWidget(QGroupBox):
    class __Plotter(QTabWidget):
        class __RaFilePlotterWorker(QThread):
            def __init__(self, path: str):
                super().__init__()
                self.__path = path

            @property
            def powers(self):
                return self.__powers

            @property
            def wavelengths(self):
                return self.__wavelengths * 1e9

            def run(self):
                logger.debug(f"Analyzing {self.__path}")
                self.__powers, self.__wavelengths = read_mat(self.__path)

        def __init__(self, parent=None):
            super().__init__(parent)

            self.__current_tab_index: int = 0
            self.__current_file_basename: str | None = None

        def plot_file(
            self,
            file_path: str,
            r2_threshold: float,
            max_n100dBm_points: int,
        ):
            self.__current_file_basename = os.path.basename(file_path)
            self.__r2_threshold = r2_threshold
            self.__max_n100dBm_points = max_n100dBm_points
            self.__worker = self.__RaFilePlotterWorker(file_path)
            self.__worker.finished.connect(self.slot_work_done)  # type: ignore
            self.__worker.start()

        @Slot()
        def slot_work_done(self):
            # clear previous plots
            self.__current_tab_index = self.currentIndex()
            for index in range(self.count()):
                self.widget(index).deleteLater()
            self.clear()

            # make new plots
            for i, power in enumerate(self.__worker.powers):
                figure_widget = RaFigureWidget()
                axes = figure_widget.figure.subplots(1, 1)
                axes.plot(self.__worker.wavelengths, power)
                sweep_fit_result = SweepFitResult.from_data(
                    power, self.__worker.wavelengths
                )
                peaks = sweep_fit_result.get_peaks(
                    self.__r2_threshold, self.__max_n100dBm_points
                )
                er = sweep_fit_result.get_er(
                    self.__r2_threshold, self.__max_n100dBm_points
                )
                q = sweep_fit_result.get_q(
                    self.__r2_threshold, self.__max_n100dBm_points
                )
                # peaks, fsr, er, q = get_lorentzian_peaks(
                #     power,
                #     self.__worker.wavelengths,
                #     self.__r2_threshold,
                #     self.__max_n100dBm_points,
                # )
                for _j, peak in enumerate(peaks):
                    x0, y0, _i, gamma, a = peak
                    xs = np.linspace(x0 - 5 * gamma, x0 + 5 * gamma, 101)
                    ys = lorentzian(xs, x0, y0, _i, gamma, a)
                    axes.plot(xs, ys, "-", alpha=0.5)
                    if _j < len(er) and _j < len(q):
                        axes.text(x0, y0, f"ER:{er[_j]:.2f}")
                        axes.text(x0, y0 + _i, f"Q:{q[_j]:.4g}")

                axes.set_title(f"{self.__current_file_basename}")
                axes.set_xlabel("Wavelength")
                axes.set_ylabel("Power")
                figure_widget.figure.set_tight_layout(True)
                figure_widget.figure_canvas.show()
                self.addTab(figure_widget, f"Power {str(i + 1)}")

            self.__worker.deleteLater()

            if self.__current_tab_index < self.count():
                self.setCurrentIndex(self.__current_tab_index)

    def __init__(self, parent=None):
        super().__init__(title="Sweep Plotter", parent=parent)

        self.__file_plotter = self.__Plotter(self)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.__file_plotter)

    def clear(self):
        self.__file_plotter.clear()

    def update(self, file_path: str, r2_threshold: float, max_n100dBm_points: int):
        self.__file_plotter.plot_file(file_path, r2_threshold, max_n100dBm_points)


class RaSpectrogramPlotterWidget(QWidget):
    __signal_spectrograms_work_start = Signal()
    signal_spectrograms_work_done = Signal(bool)

    class __Worker(QThread):
        def __init__(
            self,
            analyzer: PassiveAnalyzer,
            channels: set[int],
            step: int,
            start_index: int,
            stop_index: int | None,
        ):
            super().__init__()
            self.__analyzer = analyzer
            self.__channels = channels
            self.__step = step
            self.__start_index = start_index
            self.__stop_index = stop_index

        @property
        def spectrogram_dict(self):
            return self.__spectrogram_dict

        def run(self):
            self.__spectrogram_dict = self.__analyzer.get_spectrograms(
                self.__channels, self.__step, self.__start_index, self.__stop_index
            )

    def __init__(self, parent=None):
        super().__init__(parent)
        # if not in a layout, resize to have a larger space
        if not self.parent():
            self.resize(800, 600)

        self.__tab_widget = QTabWidget()
        self.__save_all_button = QPushButton("Save All")

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.__tab_widget)
        self.layout().addWidget(self.__save_all_button)

        # connections
        self.__signal_spectrograms_work_start.connect(
            self.__slot_spectrograms_work_start
        )
        self.__save_all_button.clicked.connect(self.__slot_save_all)

        # an analyzer should be initialized outside and passed into this class
        self.analyzer: PassiveAnalyzer = None  # type: ignore

    def plot_spectrograms(
        self,
        channels: set[int],
        step: int,
        start_index: int,
        stop_index: int | None,
        x_tick_number: int,
        y_tick_number: int,
        power_unit: str,
        time_unit: str,
    ):
        if self.analyzer is None:
            raise RuntimeError("Analyzer is not initialized")
        else:
            # clear previous plots
            for index in range(self.__tab_widget.count()):
                self.__tab_widget.widget(index).deleteLater()
            self.__tab_widget.clear()

            self.__channels = channels
            self.__step = step
            self.__start_index = start_index
            self.__stop_index = stop_index
            self.__x_tick_step = int(len(self.analyzer.timestamps) / x_tick_number)
            self.__y_tick_step = int(len(self.analyzer.wavelengths) / y_tick_number)
            self.__power_unit = power_unit
            self.__time_unit = time_unit
            self.__signal_spectrograms_work_start.emit()

    @Slot()
    def __slot_spectrograms_work_start(self):
        self.__worker = self.__Worker(
            self.analyzer,
            self.__channels,
            self.__step,
            self.__start_index,
            self.__stop_index,
        )
        self.__worker.finished.connect(self.__slot_spectrograms_work_done)  # type: ignore
        self.__worker.start()
        self.signal_spectrograms_work_done.emit(False)

    @Slot()
    def __slot_spectrograms_work_done(self):
        try:
            # make new plots
            x_labels = np.vectorize(lambda x: "{:.5g}".format(x))(
                self.analyzer.timestamps[
                    self.__start_index : self.__stop_index : self.__step
                ]
            )
            y_labels = np.vectorize(lambda x: "{:.5g}".format(x))(
                self.analyzer.wavelengths[::-1]
            )
            x_formatter = FuncFormatter(
                lambda x, _: x_labels[int(x)]
                if int(x) in range(len(x_labels))
                else None
            )
            y_formatter = FuncFormatter(
                lambda y, _: y_labels[int(y)]
                if int(y) in range(len(y_labels))
                else None
            )
            for k, v in self.__worker.spectrogram_dict.items():
                figure_widget = RaFigureWidget()
                ax = figure_widget.figure.subplots(1, 1)
                image = ax.imshow(v, cmap="inferno")

                ax.set_xticks(
                    list(range(len(x_labels)))[:: self.__x_tick_step],
                    x_labels[:: self.__x_tick_step],
                )
                ax.set_xlabel(f"Time ({self.__time_unit})")
                ax.xaxis.set_major_formatter(x_formatter)

                ax.set_yticks(
                    list(range(len(y_labels)))[:: self.__y_tick_step],
                    y_labels[:: self.__y_tick_step],
                )
                ax.set_ylabel("Wavelength (nm)")
                ax.yaxis.set_major_formatter(y_formatter)

                ax.set_title(f"Power {k+1} Spectrogram")
                ax.axis("auto")

                color_bar = figure_widget.figure.colorbar(
                    image, orientation="horizontal"
                )
                color_bar.set_label(f"Power ({self.__power_unit})")

                figure_widget.figure.set_tight_layout(True)
                figure_widget.figure_canvas.show()
                self.__tab_widget.addTab(figure_widget, f"Power {k+1}")
        except IndexError | ValueError as e:
            raise IndexError(
                "Could not plot spectrograms. Please check range and tick settings"
            ) from e

        del self.__worker
        logger.info("Spectrogram plotting done!")
        self.signal_spectrograms_work_done.emit(True)

    @Slot()
    def __slot_save_all(self):
        if self.__tab_widget.count() == 0:
            raise RuntimeError("No spectrogram to save")

        dir = QFileDialog.getExistingDirectory()
        for index in range(self.__tab_widget.count()):
            file_name = f"Power {index+1} Spectrogram.png"
            widget: RaFigureWidget = self.__tab_widget.widget(index)  # type: ignore
            widget.figure.savefig(os.path.join(dir, file_name))
            logger.info(f"{file_name} saved")
