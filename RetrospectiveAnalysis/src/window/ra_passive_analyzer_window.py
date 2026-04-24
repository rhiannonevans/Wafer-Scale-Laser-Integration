import logging
import os
import pathlib
import re
import sys

from PySide6.QtCore import QDir, Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFileSystemModel,
    QHeaderView,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QVBoxLayout,
)
from tqdm import tqdm

from ..core.passive_tools import PassiveAnalyzer
from ..uic.base.ra_main_window import Ui_RaMainWindow
from ..widgets.base.ra_peak_tracker_widget import RaPeakTrackerWidget
from ..widgets.base.ra_tab_plotter_widget import (
    RaFilePlotterWidget,
    RaSpectrogramPlotterWidget,
)
from ..widgets.lib.ra_progress_bar import RaProgressBar

logger = logging.getLogger(__name__)

RESULT_FOLDER_DEFAULT_NAME = "RA_result"
PEAK_SHIFT_FILE_NAME = "peak_shift.mat"
PEAKS_FILE_NAME = "peaks.mat"
FSR_ER_Q_RESULT_FILE_NAME = "fsr_er_q.mat"

TEMPORARY_MESSAGE_TIMEOUT = 5000


class RaPassiveAnalyzerWindow(QMainWindow):
    __signal_write = Signal(str)
    signal_close = Signal()
    signal_progress = Signal(dict)

    def __init__(self):
        super().__init__()
        self.__ui = Ui_RaMainWindow()
        self.__ui.setupUi(self)

        # status bar
        self.__ui.statusbar.addPermanentWidget(QLabel("RA Passive Analyzer"))
        self.__progress_bar = RaProgressBar()
        self.__progress_bar.hide()
        self.__ui.statusbar.addWidget(self.__progress_bar)
        self.signal_progress.connect(self.slot_signal_progress)

        # initialize file treeview
        model = QFileSystemModel()
        model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDot | QDir.Filter.AllDirs
        )
        model.setRootPath(QDir.rootPath())
        self.__ui.treeView.setModel(model)
        self.__ui.treeView.setRootIndex(model.index(os.path.expanduser("~")))
        self.__ui.treeView.header().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        # file plotter
        self.__file_plotter_widget = RaFilePlotterWidget()
        self.__ui.splitter.insertWidget(1, self.__file_plotter_widget)
        self.__ui.splitter.setStretchFactor(1, 2)

        # spectrum plotter
        # intended to be popped up so not in any layout
        self.__folder_plotter = RaSpectrogramPlotterWidget()
        self.__folder_plotter.signal_spectrograms_work_done.connect(
            self.__ui.spectrogramButton.setEnabled
        )

        # peak tracker
        self.__peak_tracker_widget = RaPeakTrackerWidget()
        self.__ui.peakTrackerWidget.setLayout(QVBoxLayout())
        self.__ui.peakTrackerWidget.layout().addWidget(self.__peak_tracker_widget)
        self.__peak_tracker_widget.signal_work_done.connect(
            self.__ui.trackPeakButton.setEnabled
        )
        self.__peak_tracker_widget.signal_work_done.connect(
            self.__ui.saveResultsButton.setEnabled
        )
        self.__peak_tracker_widget.signal_fsr_er_q_work_done.connect(
            self.__ui.FSRERQButton.setEnabled
        )

        # add a window manager on menu bar
        menu = QMenu("Window", self)
        panels = [
            (self.__ui.peakTracingGroupBox, "Peak Tracking"),
            (self.__ui.analyzerSettingsGroupBox, "Analyzer Setting"),
            (self.__ui.plotSpectrogramsGroupBox, "Spectrogram Plotter"),
            (self.__ui.thresholdSettingsGroupBox, "Threshold Settings"),
            (self.__ui.peakTracingSettingGroupBox, "Peak Tracing Settings"),
        ]
        for widget, string in panels:
            action = QAction(string, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(widget.setVisible)
            menu.addAction(action)
        self.__ui.menubar.addMenu(menu)

        # write to log panel
        sys.stdout = self
        sys.stderr = self
        self.__logging_handler = logging.StreamHandler(self)
        self.__logging_handler.setFormatter(logging.getLogger().handlers[0].formatter)
        self.__logging_handler.setLevel(logging.getLogger().handlers[0].level)
        logging.getLogger().addHandler(self.__logging_handler)
        self.__signal_write.connect(self.slot_log_write)

        self.__ui.analyzerSettingsGroupBox.setEnabled(False)
        self.__ui.plotSpectrogramsGroupBox.setEnabled(False)
        self.__ui.peakTracingGroupBox.setEnabled(False)

    # stdout and logger redirection requirement
    def write(self, m):
        self.__signal_write.emit(m)

    # stdout and logger redirection requirement
    def flush(self):
        pass

    @Slot()
    def slot_log_write(self, text):
        self.__ui.textBrowser.moveCursor(QTextCursor.End)  # type: ignore
        self.__ui.textBrowser.insertPlainText(text)
        self.__ui.textBrowser.ensureCursorVisible()

    def closeEvent(self, event: QCloseEvent):
        self.signal_close.emit()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        logging.getLogger().removeHandler(self.__logging_handler)
        return super().closeEvent(event)

    # Slots
    def slot_open_clicked(self):
        folder_path = QFileDialog.getExistingDirectory(
            dir=os.path.expanduser("~"),
        )
        if folder_path == "":
            self.__ui.statusbar.showMessage("Open cancelled", TEMPORARY_MESSAGE_TIMEOUT)
        else:
            tree_view = self.__ui.treeView
            model: QFileSystemModel = tree_view.model()  # type: ignore
            tree_view.setRootIndex(model.index(folder_path))
            self.__ui.statusbar.showMessage(f"{folder_path}", TEMPORARY_MESSAGE_TIMEOUT)
            os.chdir(folder_path)

            # clear
            self.__ui.powerListWidget.clear()
            self.__ui.peakTrackerPowerListWidget.clear()
            self.__ui.timeStampComboBox.clear()
            self.__peak_tracker_widget.clear()
            self.__file_plotter_widget.clear()

            # setup timestamp selector combo box
            pat = re.compile(r".*time.*\.csv")
            for f in filter(lambda x: pat.match(x), iter(os.listdir(folder_path))):
                self.__ui.timeStampComboBox.addItem(str(f))

            self.__ui.analyzerSettingsGroupBox.setEnabled(True)
            self.__ui.plotSpectrogramsGroupBox.setEnabled(False)
            self.__ui.peakTracingGroupBox.setEnabled(False)
            self.__ui.saveResultsButton.setEnabled(False)

    def slot_file_changed(self, model_index):
        tree_view = self.__ui.treeView
        model: QFileSystemModel = tree_view.model()  # type: ignore
        file_path = model.filePath(model_index)
        file_name = os.path.basename(file_path)
        _, file_ext = os.path.splitext(file_name)
        if model.isDir(model.index(file_path)):
            tree_view.setRootIndex(model.index(file_path))
            self.__ui.statusbar.showMessage(f"{file_path}", TEMPORARY_MESSAGE_TIMEOUT)
        elif file_ext != ".mat":
            logger.error(f"{file_name} is not a matlab workspace file")
        else:
            self.__file_plotter_widget.update(
                file_path,
                r2_threshold=self.__ui.r2ThresholdDoubleSpinBox.value(),
                max_n100dBm_points=self.__ui.n100dBmToleranceSpinBox.value(),
            )

    def slot_load_analyzer(self):
        # clear power list widget
        self.__ui.powerListWidget.clear()
        self.__ui.peakTrackerPowerListWidget.clear()
        # clear peak tracker
        self.__peak_tracker_widget.clear()

        # load analyzer parameters
        try:
            pattern = eval(self.__ui.patternLineEdit.text())
            time_multiplier = float(eval(self.__ui.timeMultiplierLineEdit.text()))
        except Exception as e:
            logger.error(f"{e}")
            raise e

        path = self.__ui.treeView.model().filePath(  # type: ignore
            self.__ui.treeView.rootIndex()
        )
        timestamp = self.__ui.timeStampComboBox.currentText()
        try:
            timestamp = float(timestamp)
        except ValueError as e:  # if parse float failed
            if re.match(r".*\.csv", timestamp):
                pass
            else:
                logger.error(f"'{timestamp}' is not a number or a csv file")
                raise e

        self.__analyzer = PassiveAnalyzer(path, timestamp, pattern, time_multiplier)

        file_num, power_num = self.__analyzer.info()
        logger.info(f"{path} has {file_num} files with {power_num} power channels")

        # update peak tracker output path combo box
        self.__ui.peakTracingOutputPathComboBox.setCurrentText(path)
        self.__ui.peakTracingOutputPathComboBox.addItem(path)

        # update spectrogram plotter start/stop values
        self.__ui.sampleStartSpinBox.setMaximum(file_num)
        self.__ui.sampleStopSpinBox.setMinimum(2)
        self.__ui.sampleStopSpinBox.setMaximum(file_num)
        self.__ui.sampleStopSpinBox.setValue(file_num)

        # update peak tracing start/stop values
        self.__ui.peakTracingStartSpinBox.setMaximum(file_num)
        self.__ui.peakTracingStopSpinBox.setMaximum(file_num)
        self.__ui.peakTracingStopSpinBox.setValue(file_num)

        # add power channels to power list widget
        for i in range(power_num):
            item = QListWidgetItem()
            checkbox = QCheckBox(f"Power {i+1}")
            self.__ui.powerListWidget.addItem(item)
            self.__ui.powerListWidget.setItemWidget(item, checkbox)

            item = QListWidgetItem()
            checkbox = QCheckBox(f"Power {i+1}")
            checkbox.setChecked(True)
            self.__ui.peakTrackerPowerListWidget.addItem(item)
            self.__ui.peakTrackerPowerListWidget.setItemWidget(item, checkbox)

        self.__ui.plotSpectrogramsGroupBox.setEnabled(True)
        self.__ui.peakTracingGroupBox.setEnabled(True)

    # Spectrogram plotting slots
    def slot_plot_spectrogram(self):
        self.__folder_plotter.analyzer = self.__analyzer
        lw = self.__ui.powerListWidget
        powers = {i for i in range(lw.count()) if lw.itemWidget(lw.item(i)).checkState() == Qt.Checked}  # type: ignore
        if len(powers) != 0:
            self.__folder_plotter.plot_spectrograms(
                powers,
                self.__ui.sampleStepSpinBox.value(),
                self.__ui.sampleStartSpinBox.value() - 1,
                self.__ui.sampleStopSpinBox.value(),
                self.__ui.xTicksSpinBox.value(),
                self.__ui.yTicksSpinBox.value(),
                self.__ui.powerUnitLineEdit.text(),
                self.__ui.timeUnitLineEdit.text(),
            )
            self.__folder_plotter.show()
            logger.info("Spectrogram plotting started!")
        else:
            logger.warning("No power channel selected!")

    def slot_spectrogram_select_all(self):
        lw = self.__ui.powerListWidget
        for i in range(lw.count()):
            lw.itemWidget(lw.item(i)).setChecked(True)  # type: ignore

    def slot_spectrogram_unselect_all(self):
        lw = self.__ui.powerListWidget
        for i in range(lw.count()):
            lw.itemWidget(lw.item(i)).setChecked(False)  # type: ignore

    def slot_spectrogram_on_start_spinbox_change(self, value: int):
        file_num, _ = self.__analyzer.info()
        self.__ui.sampleStopSpinBox.setMinimum(min(max(2, value + 1), file_num))

    def slot_spectrogram_on_stop_spinbox_change(self, value: int):
        self.__ui.sampleStartSpinBox.setMaximum(max(1, value - 1))

    # Peak tracking slots
    def slot_track_peak(self):
        self.__ui.statusbar.clearMessage()
        self.__progress_bar.reset()
        self.__progress_bar.show()
        lw = self.__ui.peakTrackerPowerListWidget
        powers = {i for i in range(lw.count()) if lw.itemWidget(lw.item(i)).checkState() == Qt.Checked}  # type: ignore
        self.__peak_tracker_widget.plot_initial(
            self.__analyzer,
            powers,
            (
                self.__ui.peakTracingStartSpinBox.value() - 1,
                self.__ui.peakTracingStopSpinBox.value(),
                self.__ui.peakTracingStepSpinBox.value(),
            ),
            self.__ui.timeUnitLineEdit.text(),
            self.__ui.powerUnitLineEdit.text(),
            self.__ui.r2ThresholdDoubleSpinBox.value(),
            self.__ui.n100dBmToleranceSpinBox.value(),
            self.signal_progress,
        )

    def slot_save_results(self):
        output_path = os.path.join(
            self.__ui.peakTracingOutputPathComboBox.currentText(),
            RESULT_FOLDER_DEFAULT_NAME,
        )
        os.makedirs(output_path, exist_ok=True)
        peak_shift_path = os.path.join(output_path, PEAK_SHIFT_FILE_NAME)
        peaks_path = os.path.join(output_path, PEAKS_FILE_NAME)
        self.__peak_tracker_widget.save_results(peak_shift_path, peaks_path)

    def slot_peak_tracking_select_all(self):
        lw = self.__ui.peakTrackerPowerListWidget
        for i in range(lw.count()):
            lw.itemWidget(lw.item(i)).setChecked(True)  # type: ignore

    def slot_peak_tracking_unselect_all(self):
        lw = self.__ui.peakTrackerPowerListWidget
        for i in range(lw.count()):
            lw.itemWidget(lw.item(i)).setChecked(False)  # type: ignore

    def slot_peak_tracking_select_output_path(self):
        path = QFileDialog.getExistingDirectory(
            dir=self.__ui.treeView.model().filePath(  # type: ignore
                self.__ui.treeView.rootIndex()
            ),
        )
        if path != "":
            self.__ui.peakTracingOutputPathComboBox.setCurrentText(path)
            self.__ui.peakTracingOutputPathComboBox.addItem(path)

    def slot_peak_tracking_on_start_spinbox_change(self, value: int):
        file_num, _ = self.__analyzer.info()
        self.__ui.peakTracingStopSpinBox.setMinimum(min(max(2, value + 1), file_num))

    def slot_peak_tracking_on_stop_spinbox_change(self, value: int):
        self.__ui.peakTracingStartSpinBox.setMaximum(max(1, value - 1))

    # FSR ER Q slots
    def slot_fsr_er_q(self):
        self.__ui.statusbar.clearMessage()
        lw = self.__ui.peakTrackerPowerListWidget
        powers = {i for i in range(lw.count()) if lw.itemWidget(lw.item(i)).checkState() == Qt.Checked}  # type: ignore
        output_path = os.path.join(
            self.__ui.peakTracingOutputPathComboBox.currentText(),
            RESULT_FOLDER_DEFAULT_NAME,
            FSR_ER_Q_RESULT_FILE_NAME,
        )
        os.makedirs(pathlib.Path(output_path).parent, exist_ok=True)
        self.__peak_tracker_widget.fsr_er_q(
            self.__analyzer,
            powers,
            (
                self.__ui.peakTracingStartSpinBox.value() - 1,
                self.__ui.peakTracingStopSpinBox.value(),
                self.__ui.peakTracingStepSpinBox.value(),
            ),
            self.__ui.r2ThresholdDoubleSpinBox.value(),
            self.__ui.n100dBmToleranceSpinBox.value(),
            output_path,
        )

    def slot_signal_progress(self, format_dict: dict):
        n = format_dict["n"]
        total = format_dict["total"]
        elapsed = format_dict["elapsed"]
        rate = format_dict["rate"]

        self.__progress_bar.value = n
        self.__progress_bar.maximum = total

        if all([n, total, elapsed, rate]):
            elapsed_time = tqdm.format_interval(elapsed)
            remaining_time = tqdm.format_interval((total - n) / rate)
            rate_str = f"{rate:.2f}/s"

            self.__progress_bar.text_left = (
                f"{n}/{total}({n/total*100:.2f}%) {rate_str} {elapsed_time}"
            )
            self.__progress_bar.text_right = f"{remaining_time}"
        else:
            self.__progress_bar.text_left = ""
            self.__progress_bar.text_right = (
                "" if format_dict["n"] != format_dict["total"] else "Done"
            )
