from __future__ import annotations

import logging
import os
import pathlib
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from itertools import repeat
from multiprocessing import JoinableQueue, Pool, Process
from typing import Callable, Optional

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from ordered_set import OrderedSet
from pyqtgraph import ImageView, PlotItem, PlotWidget, ScatterPlotItem
from PySide6.QtCore import QFileSystemWatcher, Qt, QThread, Signal, Slot
from PySide6.QtGui import QCloseEvent, QTextCursor, QTransform
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..core.lib import SweepFitResult
from ..core.passive_tools import read_mat
from ..widgets.lib.ra_drop_widgets import RaDropLineEdit, RaDropPushButton

logger = logging.getLogger(__name__)


DEFAULT_RESULT_FILENAME = "ra_peaks.npz"
DEFAULT_SPECTROGRAM_FILENAME = "ra_spectrograms.npz"
DEFAULT_SWEEP_TEMP_DIR = ".ra_temp_curve_fits"

NP_PEAK_KEY = "sweeps"
NP_SPECTROGRAM_KEY = "spectrograms"
NP_WAVELENGTH_KEY = "wavelength"


WATCH_BUTTON_DEFAULT_TEXT = "Watch"
WATCH_BUTTON_RUN_TEXT = "Analyzing..."
WATCH_BUTTON_IDLE_TEXT = "Watching new files..."


@dataclass(frozen=True)
class OutputQueueItem:
    sweeps: list[SweepFitResult]
    powers: NDArray[np.floating]
    wavelength: NDArray[np.floating]
    file_name: str


def worker_process(
    input_queue: JoinableQueue[Optional[str]],
    output_queue: JoinableQueue[Optional[OutputQueueItem]],
    output_dir: str,
):
    with Pool() as pool:
        while True:
            path = input_queue.get()
            if path is not None:
                powers, wavelength = read_mat(path)
                wavelength *= 1e9
                sweeps = [
                    s
                    for s in pool.starmap(
                        SweepFitResult.from_data,
                        zip([channel for channel in powers], repeat(wavelength)),
                    )
                ]

                np.savez_compressed(
                    os.path.join(output_dir, os.path.basename(path)) + ".npz",
                    sweeps=np.array(sweeps, dtype=object),
                )

                output_queue.put(
                    OutputQueueItem(
                        sweeps=[
                            SweepFitResult.from_data(channel, wavelength)
                            for channel in powers
                        ],
                        powers=powers,
                        wavelength=wavelength,
                        file_name=os.path.basename(path),
                    )
                )

                input_queue.task_done()
            else:  # None means terminate
                input_queue.task_done()
                return


class WorkerThread(QThread):
    def __init__(self, f: Callable, *args, **kwargs):
        super().__init__()
        self.__f = f
        self.__args = args
        self.__kwargs = kwargs

    def run(self):
        self.__ret = self.__f(*self.__args, **self.__kwargs)

    @property
    def result(self):
        return self.__ret


class RaWatcherWindow(QMainWindow):
    signal_close = Signal()
    signal_write = Signal(str)
    signal_plot_process_output = Signal(OutputQueueItem)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(1440, 810)

        self.__central_widget = self.RaWatcherWindowCentralWidget()
        self.__central_widget.signal_start_watch.connect(self.__slot_start_watch)
        self.__central_widget.signal_stop_watch.connect(self.__slot_stop_watch)
        self.__central_widget.signal_table_widget_cell_double_clicked.connect(
            self.__slot_plot_single_file
        )
        self.setCentralWidget(self.__central_widget)

        self.__text_browser = QTextBrowser()
        dock_widget = QDockWidget()
        dock_widget.setWidget(self.__text_browser)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

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
        if self.__central_widget.watch_button.isChecked():
            self.__slot_stop_watch(self.__central_widget.path_line_edit.text())
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        logging.getLogger().removeHandler(self.__log_handler)
        return super().closeEvent(event)

    # slots
    def __slot_start_watch(self, dir: str):
        # remove np temp dir if exists
        if os.path.exists(np_tmp_dir := os.path.join(dir, DEFAULT_SWEEP_TEMP_DIR)):
            shutil.rmtree(np_tmp_dir)

        # clear table widget
        self.__central_widget.table_widget.setRowCount(0)

        # clear tab widget
        self.__central_widget.spectrogram_tab_widget.clear()

        # disable the watch button
        self.__central_widget.watch_button.setDisabled(True)

        # initialize file list
        self.__files_temp = {
            p for p in os.listdir(dir) if pathlib.Path(p).suffix == ".mat"
        }

        # initialize queues
        self.__queue_input: JoinableQueue[str] = JoinableQueue()
        self.__queue_output: JoinableQueue[OutputQueueItem] = JoinableQueue()

        # start the worker process
        sweep_dir = os.path.join(dir, DEFAULT_SWEEP_TEMP_DIR)
        os.makedirs(sweep_dir, exist_ok=True)
        self.__process = Process(
            target=worker_process,
            args=(
                self.__queue_input,
                self.__queue_output,
                sweep_dir,
            ),
        )
        self.__process.start()

        # start the plot update thread
        def thread_func():
            is_first_run = True
            while True:
                item = self.__queue_output.get()
                if item is None:  # None means terminate
                    self.__queue_output.task_done()
                    self.__central_widget.watch_button.setText(
                        WATCH_BUTTON_DEFAULT_TEXT
                    )
                    return
                else:
                    is_first_run = False
                    self.signal_plot_process_output.emit(item)
                    logger.info(f"Processing {item.file_name} done!")
                    self.__queue_output.task_done()
                if not is_first_run:
                    if self.__queue_output.empty() and self.__queue_input.empty():
                        self.__central_widget.watch_button.setText(
                            WATCH_BUTTON_IDLE_TEXT
                        )
                        self.__central_widget.watch_button.setEnabled(True)
                    else:
                        self.__central_widget.watch_button.setText(
                            WATCH_BUTTON_RUN_TEXT
                        )
                        self.__central_widget.watch_button.setEnabled(False)

        self.signal_plot_process_output.connect(self.__slot_plot_output_queue_item)
        self.__thread = WorkerThread(thread_func)
        self.__thread.start()

        # start a watcher
        self.__watcher = QFileSystemWatcher()
        self.__watcher.addPath(dir)
        self.__watcher.directoryChanged.connect(self.__slot_dir_changed)

    def __slot_stop_watch(self, dir: str):
        self.__watcher.directoryChanged.disconnect(self.__slot_dir_changed)
        self.__watcher.deleteLater()

        # put a None to terminate
        self.__queue_input.put(None)  # type: ignore
        self.__queue_input.join()
        self.__process.join()

        # put a None to terminate
        self.__queue_output.put(None)  # type: ignore
        self.__queue_output.join()
        self.__thread.wait()

        file_paths = OrderedSet(
            [
                os.path.join(
                    dir,
                    DEFAULT_SWEEP_TEMP_DIR,
                    self.__central_widget.table_widget.item(i, 1).text() + ".npz",
                )
                for i in range(self.__central_widget.table_widget.rowCount())
            ]
        )

        sweeps = np.array(
            [np.load(p, allow_pickle=True)[NP_PEAK_KEY] for p in file_paths]
        ).swapaxes(0, 1)

        np.savez_compressed(os.path.join(dir, DEFAULT_RESULT_FILENAME), sweeps=sweeps)

        np.savez_compressed(
            os.path.join(dir, DEFAULT_SPECTROGRAM_FILENAME),
            spectrograms=self.__spectrograms,
            wavelength=self.__wavelength,
        )

        # remove np temp file if exists
        if os.path.exists(np_tmp_dir := os.path.join(dir, DEFAULT_SWEEP_TEMP_DIR)):
            shutil.rmtree(np_tmp_dir)

    def __slot_dir_changed(self, dir: str):
        files_now = {p for p in os.listdir(dir) if pathlib.Path(p).suffix == ".mat"}
        for f in sorted(
            files_now.difference(self.__files_temp),
            key=lambda x: os.path.getmtime(os.path.join(dir, x)),
        ):
            logger.info(f"{f} added")
            self.__queue_input.put(os.path.join(dir, f))
        self.__files_temp.update(files_now)

    def __slot_plot_output_queue_item(self, item: OutputQueueItem):
        if self.__central_widget.table_widget.rowCount() == 0:
            # the first data
            self.__wavelength = item.wavelength
            self.__spectrograms: NDArray[np.floating] = np.array(
                [item.powers], ndmin=3
            ).swapaxes(0, 1)
            for i, channel in enumerate(item.powers):
                name = f"Channel {i+1}"
                self.__central_widget.spectrogram_tab_widget.addTab(
                    RaWatcherWindowSpectrogramPlotWidget(name), name
                )
        else:
            self.__spectrograms = np.append(
                self.__spectrograms,
                np.array([item.powers], ndmin=3).swapaxes(0, 1),
                axis=1,
            )

        row_index = self.__central_widget.table_widget.rowCount()
        self.__central_widget.table_widget.insertRow(row_index)
        self.__central_widget.table_widget.setItem(
            row_index, 0, QTableWidgetItem(str(datetime.now()))
        )
        self.__central_widget.table_widget.setItem(
            row_index, 1, QTableWidgetItem(item.file_name)
        )

        for i, channel in enumerate(item.powers):
            tr = QTransform()
            tr.translate(-0.5, min(item.wavelength))
            tr.scale(
                1,
                (max(item.wavelength) - min(item.wavelength)) / len(item.wavelength),
            )
            spectrogram_widget: RaWatcherWindowSpectrogramPlotWidget = (
                self.__central_widget.spectrogram_tab_widget.widget(i)
            )  # type: ignore
            spectrogram_widget.image_view.setImage(self.__spectrograms[i], transform=tr)

            current_index = self.__spectrograms[i].shape[0] - 1
            sweep = SweepFitResult.from_data(channel, item.wavelength)
            for p in sweep.get_peaks():
                spectrogram_widget.scatter_plot_item.addPoints([current_index], [p[0]])

    def __slot_plot_single_file(self, row: int, _col: int):
        file_name = self.__central_widget.table_widget.item(row, 1).text()
        self.__central_widget.spectrum_tab_widget.clear()
        for i in range(self.__spectrograms.shape[0]):
            plot_widget = PlotWidget()
            plot_widget.setTitle(f"{file_name} Channel {i+1}")
            plot_widget.plot(
                x=self.__wavelength,
                y=self.__spectrograms[i][row],
            )
            self.__central_widget.spectrum_tab_widget.addTab(
                plot_widget, f"Channel {i+1}"
            )
        self.__central_widget.spectrum_tab_widget.show()

    class RaWatcherWindowCentralWidget(QWidget):
        signal_start_watch = Signal(str)
        signal_stop_watch = Signal(str)
        signal_table_widget_cell_double_clicked = Signal(int, int)

        def __init__(self):
            super().__init__()

            self.path_line_edit = RaDropLineEdit()
            self.path_line_edit.signal_drop.connect(  # type: ignore
                self.path_line_edit.setText
            )

            self.path_select_button = RaDropPushButton("Select")
            self.path_select_button.signal_drop.connect(  # type: ignore
                self.path_line_edit.setText
            )

            self.watch_button = QPushButton(WATCH_BUTTON_DEFAULT_TEXT)
            self.watch_button.setCheckable(True)

            self.table_widget = QTableWidget()
            self.table_widget.setColumnCount(2)
            self.table_widget.setHorizontalHeaderLabels(["Time", "Name"])
            self.table_widget.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self.table_widget.setEditTriggers(
                QAbstractItemView.EditTrigger.NoEditTriggers
            )

            self.spectrum_tab_widget = QTabWidget()

            self.spectrogram_tab_widget = QTabWidget()

            # layout widgets
            self.setLayout(QHBoxLayout())
            splitter = QSplitter(Qt.Orientation.Horizontal)

            path_layout = QHBoxLayout()
            path_layout.addWidget(self.path_line_edit)
            path_layout.addWidget(self.path_select_button)

            left_widget = QWidget()
            left_widget.setLayout(QVBoxLayout())
            left_widget.layout().addLayout(path_layout)  # type: ignore
            left_widget.layout().addWidget(self.watch_button)
            left_widget.layout().addWidget(self.table_widget)

            splitter.addWidget(left_widget)
            splitter.setStretchFactor(0, 0)
            splitter.addWidget(self.spectrogram_tab_widget)
            splitter.setStretchFactor(1, 1)

            self.layout().addWidget(splitter)

            # connect signals
            self.path_select_button.clicked.connect(self.slot_select_path)
            self.watch_button.toggled.connect(self.slot_watch_toggled)
            self.table_widget.cellDoubleClicked.connect(
                self.signal_table_widget_cell_double_clicked
            )

        def slot_select_path(self):
            path = QFileDialog.getExistingDirectory(self, "Select Directory")
            self.path_line_edit.setText(path)

        def slot_watch_toggled(self, checked: bool):
            if not checked:
                self.path_line_edit.setReadOnly(False)
                self.path_select_button.setDisabled(False)
                self.watch_button.setText(WATCH_BUTTON_DEFAULT_TEXT)
                self.signal_stop_watch.emit(self.path_line_edit.text())
            elif not os.path.exists(path := self.path_line_edit.text()):
                logger.warning(f'Path "{path}" does not exist.')
                self.path_line_edit.setReadOnly(False)
                self.path_select_button.setDisabled(False)

                self.watch_button.blockSignals(True)
                self.watch_button.setChecked(False)
                self.watch_button.blockSignals(False)
            elif not (dir_set := set(os.listdir(path))).issubset(
                set([".DS_Store", DEFAULT_SWEEP_TEMP_DIR])
            ):
                logger.warning(f'Directory "{path}" is not empty: {dir_set}')
                self.watch_button.blockSignals(True)
                self.watch_button.setChecked(False)
                self.watch_button.blockSignals(False)
            else:
                self.path_line_edit.setReadOnly(True)
                self.path_select_button.setDisabled(True)
                self.watch_button.setText(WATCH_BUTTON_IDLE_TEXT)
                self.signal_start_watch.emit(path)


class RaWatcherWindowSpectrogramPlotWidget(QWidget):
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initialize members
        self.__plot_item = PlotItem()
        self.__plot_item.getAxis("bottom").setLabel("Sweep Number")
        self.__plot_item.getAxis("left").setLabel("Wavelength", units="m")
        self.__plot_item.getAxis("left").setScale(1e-9)
        self.__plot_item.setTitle(f"{name} Spectrogram")

        self.__image_view = ImageView(view=self.__plot_item)
        self.__image_view.ui.roiBtn.hide()
        self.__image_view.ui.menuBtn.hide()
        self.__image_view.getView().invertY(False)
        self.__image_view.getView().setAspectLocked(False)
        self.__image_view.setColorMap(pg.colormap.getFromMatplotlib("inferno"))

        self.__scatter_plot_item = ScatterPlotItem()
        self.__plot_item.addItem(self.__scatter_plot_item)

        # layout widgets
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.__image_view)

    @property
    def plot_item(self):
        return self.__plot_item

    @property
    def image_view(self):
        return self.__image_view

    @property
    def scatter_plot_item(self):
        return self.__scatter_plot_item
