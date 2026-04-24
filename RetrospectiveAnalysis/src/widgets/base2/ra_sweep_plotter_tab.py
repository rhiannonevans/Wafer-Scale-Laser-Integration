from __future__ import annotations

import logging
import numpy as np
import pyqtgraph as pg
from pyqtgraph import AxisItem, PlotItem, ScatterPlotItem
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QPushButton,
)
from ...core.lib import SweepFitResult, lorentzian, find_peak_and_properties
from ...core.passive_tools import read_mat
from ..lib.utils.ra_qthread_worker import RaQThreadWorker
from .ra_sweep_plotter_common_args_widget import (
    PeakFindingSettingsTabWidget,
    PeakFindingSettings,
)
from itertools import cycle
import os

logger = logging.getLogger(__name__)


class FilePlotterWidget(QWidget):
    def __init__(self, parent=None):
        super(FilePlotterWidget, self).__init__(parent)
        self.initUI()
        self.worker = None

        # signals
        self.peak_finding_settings.clicked.connect(self.show_param)
        self.param_tab.tabWidget.currentChanged.connect(self.change_tab)
        self.figure_tab.currentChanged.connect(self.change_tab)
        # self.param_tab.apply_val.connect(self.slot_param_changed)

    def initUI(self):
        self.layout0 = QVBoxLayout()
        self.setLayout(self.layout0)

        self.peak_finding_settings = QPushButton("Peak Finding Settings")
        self.param_tab = PeakFindingSettingsTabWidget()
        self.figure_tab = QTabWidget(self)
        self.figure_tab.resize(300, 200)

        self.layout0.addWidget(self.peak_finding_settings)
        self.layout0.addWidget(self.figure_tab)

    def change_tab(self, i: int):
        self.param_tab.tabWidget.setCurrentIndex(i)
        self.figure_tab.setCurrentIndex(i)

    def show_param(self):
        self.param_tab.show()
        self.param_tab.activateWindow()

    def populate_tab(self, powers=0):
        # populate tab if there are no plots or number of channel is different
        if self.figure_tab.count() == 0 or self.figure_tab.count() != powers:
            self.figure_tab.clear()
            self.param_tab.tabWidget.clear()

            for i in range(powers):
                fig_tab = PlotterTab(self)
                self.figure_tab.addTab(fig_tab, f"Channel {i+1}")
                self.param_tab.add_tab()

    def start_worker(self, file_path: str):
        if self.worker is not None:
            if self.worker.isFinished() is False:
                logging.info(
                    "Previously started process is still running. Please wait for it to finish and try again."
                )
                return None

        filename = os.path.basename(file_path)
        # start worker / data processing
        self.worker = RaQThreadWorker(self.plot_sweep, file_path)  # type: ignore
        self.worker.finished.connect(lambda x=filename :self.slot_finished(file_name=x))
        self.worker.start()

    def plot_sweep(self, file_path):
        sweep_fit_results = []
        powers, wavelength = read_mat(file_path)

        for i in range(len(powers)):
            param: PeakFindingSettings = self.param_tab.tabWidget.widget(i)  # type: ignore
            sweep_fit_results.append(SweepFitResult.from_data(
                powers[i], 
                wavelength * 1e9,
                param.gaussian_filter,
                param.prominence_scalar)
            )

        return powers, wavelength, sweep_fit_results

    def plot_sweep_old(self, file_path):
        powers, wavelength = read_mat(file_path)
        sweep_fit_results = [
            SweepFitResult.from_data(p, wavelength * 1e9) for p in powers
        ]

        return powers, wavelength, sweep_fit_results

    def slot_finished(self, file_name=''):
        powers, wavelength, sweep_fit_results = self.worker.result  # type: ignore
        wavelength = wavelength * 1e9

        self.populate_tab(powers=len(powers))

        self.figure_tab.resize(300, 400)

        for i in range(len(powers)):
            # get each tab
            tab: PlotterTab = self.figure_tab.widget(i)  # type: ignore
            param: PeakFindingSettings = self.param_tab.tabWidget.widget(i)  # type: ignore
            tab.figure_widget.clear()

            # REplot the data
            tab.figure_widget.plot(wavelength, powers[i], ZValue=1)
            tab.figure_widget.setXRange(wavelength[0], wavelength[-1])
            tab.figure_widget.setYRange(min(powers[i]) - 3, max(powers[i]) + 3)

            # plot peaks in finding process
            indices, _, _, _ = find_peak_and_properties(
                powers[i],
                param.gaussian_filter,
                param.prominence_scalar,
            )
            xs = wavelength[indices]
            ys = powers[i][indices]
            tab.figure_widget.addItem(ScatterPlotItem(xs, ys, symbol="o", symbolSize=5))

            # get fitted peaks, er, q based on each tab r2 and 100 value
            sweep: SweepFitResult = sweep_fit_results[i]

            color_cycle = cycle(["r", "m", "b", "k"])

            for j, ((x0, y0, _i, gamma, a), er, q, r2) in enumerate(
                zip(
                    sweep.get_peaks(
                        r2_threshold=param.r2_threshold,
                        n100dbm_threshold=param.n100dBm_tolerance,
                    ),
                    sweep.get_er(
                        r2_threshold=param.r2_threshold,
                        n100dbm_threshold=param.n100dBm_tolerance,
                    ),
                    sweep.get_q(
                        r2_threshold=param.r2_threshold,
                        n100dbm_threshold=param.n100dBm_tolerance,
                    ),
                    sweep.get_r2(
                        r2_threshold=param.r2_threshold,
                        n100dbm_threshold=param.n100dBm_tolerance,
                    )
                )
            ):
                xs = np.linspace(x0 - 5 * gamma, x0 + 5 * gamma, 101)
                ys = lorentzian(xs, x0, y0, _i, gamma, a)

                color = next(color_cycle)
                curve_name = f"Peak {j+1} | ER:{er:.2f} | Q:{q:.4f} | R2:{r2:.2f}"
                tab.figure_widget.plot(xs, ys, pen=color, name=curve_name)

                pass

            plot_item: PlotItem = tab.figure_widget.getPlotItem()
            plot_item.setTitle(title=file_name) # type: ignore
            bottom_axis: AxisItem = plot_item.getAxis("bottom")  # type: ignore
            bottom_axis.setLabel(text="Wavelength")

            left_axis: AxisItem = plot_item.getAxis("left")  # type: ignore
            left_axis.setLabel(text="Power", units="dBm")

class PlotterTab(QWidget):
    def __init__(self, parent=None):
        super(PlotterTab, self).__init__(parent)
        self.figure_widget = pg.PlotWidget(self)
        self.figure_widget.plot([0], [0], pen="b")
        self.figure_widget.addLegend()

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.figure_widget)
