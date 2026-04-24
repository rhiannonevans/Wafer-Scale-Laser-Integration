import logging
import os
import re
import sys
import pyqtgraph as pg
from pyqtgraph import ImageView
from PySide6.QtCore import QDir, Qt, Signal, Slot, QStringListModel
from PySide6.QtGui import QAction, QCloseEvent, QTextCursor
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QFileSystemModel,
    QMainWindow,
    QMenuBar,
    QSplitter,
    QStatusBar,
    QTextBrowser,
    QTreeView,
    QListView,
    QVBoxLayout,
    QWidget,
    QLabel,
    QMenu,
    QListView,
    QAbstractItemView,
)
from tqdm import tqdm
import webbrowser
from ..core.passive_tools import DataReaderBase, MatDataReader, read_mat, NPZDataReader
from ..widgets.base2.ra_peak_tracking_widget import PeakTrackingWidget
from ..widgets.base2.ra_spectrogram_widget import PlotSpectrogramWidget
from ..widgets.base2.ra_sweep_plotter_common_args_widget import AnalyzerSettingsWidget
from ..widgets.base2.ra_peak_tracking_args_tab import (
    RaPeakTrackingArgsTab,
)
from ..widgets.base2.ra_sweep_plotter_tab import FilePlotterWidget
from ..widgets.lib.ra_progress_bar import RaProgressBar

logger = logging.getLogger(__name__)


class RaPassiveAnalyzerWindow_new(QMainWindow):
    __signal_write = Signal(str)
    signal_close = Signal()
    signal_progress = Signal(dict)

    def __init__(self):
        super().__init__()
        self.initUI()

        self.__npz_spectrogram_path = None
        self.__npz_sweep_path = None

        # Connect signals
        self.__file_reader_widget.clicked.connect(self.slot_file_change)
        self.__sweep_plotter_tab_widget.param_tab.apply.clicked.connect(lambda state: self.slot_file_change(model_index=None))
        self.__plot_spectrogram_widget.plotSpectrogram.clicked.connect(
            self.slot_plot_spectrogram
        )
        self.__analyzer_settings_widget.loadFilesButton.clicked.connect(
            self.slot_load_analyzer
        )
        self.__action_open.triggered.connect(self.slot_action_open_folder)
        self.__action_open_npz.triggered.connect(self.slot_action_open_npz)
        self.__peak_tracking_widget.buttons.startFitAndTrack.clicked.connect(
            self.slot_fit_track_peak
        )
        self.__peak_tracking_widget.buttons.startTrack.clicked.connect(
            self.slot_track_peak
        )
        self.__peak_tracking_widget.buttons.savePeakFit.clicked.connect(
            self.slot_save_peak_fit
        )
        self.__peak_tracking_widget.buttons.getValues.clicked.connect(
            self.slot_FSR_ER_Q
        )  # move to main window
        self.__peak_tracking_widget.buttons.saveButton.clicked.connect(
            self.slot_save_results
        )
        self.signal_progress.connect(self.slot_signal_progress)

    def resizeEvent(self, event):
        if self.__peak_tracking_widget.peak_tracking_display:
            for i in range(
                self.__peak_tracking_widget.peak_tracking_display.spectrogram_tab.count()
            ):
                self.__peak_tracking_widget.peak_tracking_display.spectrogram_tab.setCurrentIndex(
                    i
                )
                self.__peak_tracking_widget.peak_tracking_display.spectrogram_tab.widget(
                    i
                ).getView().autoRange()

        return super(RaPassiveAnalyzerWindow_new, self).resizeEvent(event)

    def initUI(self):
        """
        Initialize the widgets of the main window
        """
        # log panel in the right dock area
        self.setWindowTitle("Retrospective Analysis - Passive Mode")
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, dock_widget := QDockWidget("log")
        )
        self.__text_browser = QTextBrowser()
        dock_widget.setWidget(self.__text_browser)

        # progress bar in status bar
        self.setStatusBar(status_bar := QStatusBar())
        status_bar.addPermanentWidget(QLabel("RA Passive Analyzer"))
        self.__progress_bar = RaProgressBar()
        status_bar.addWidget(self.__progress_bar)


        # Set central widget and layout
        self.setCentralWidget(central_widget := QWidget())
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(
            central_horizontal_splitter := QSplitter(Qt.Orientation.Horizontal)
        )

        # Left half window
        central_horizontal_splitter.addWidget(
            left_vertical_splitter := QSplitter(Qt.Orientation.Vertical)
        )

        # Right half window
        central_horizontal_splitter.addWidget(
            right_vertical_splitter := QSplitter(Qt.Orientation.Vertical)
        )

        # Initialize Widgets
        self.__file_reader_widget = QListView()
        self.model_dir = None
        self.model = QStringListModel()
        self.__file_reader_widget.setEditTriggers(QAbstractItemView.NoEditTriggers) # type: ignore

        self.__file_reader_widget.setModel(self.model)

        self.__peak_tracking_widget = PeakTrackingWidget(qt_signal=self.signal_progress)
        self.__sweep_plotter_tab_widget = FilePlotterWidget()
        self.__analyzer_settings_widget = AnalyzerSettingsWidget()
        self.__plot_spectrogram_widget = PlotSpectrogramWidget()

        self.__sample_spectrogram_plotter_widget = ImageView()  # not in a layout
        self.__sample_spectrogram_plotter_widget.ui.roiBtn.hide()
        self.__sample_spectrogram_plotter_widget.ui.menuBtn.hide()
        self.__sample_spectrogram_plotter_widget.getView().invertY(False)
        self.__sample_spectrogram_plotter_widget.getView().setAspectLocked(False)
        self.__sample_spectrogram_plotter_widget.setColorMap(
            pg.colormap.getFromMatplotlib("inferno")
        )

        # Add widgets to layout
        right_vertical_splitter.addWidget(self.__peak_tracking_widget)
        left_vertical_splitter.addWidget(self.__sweep_plotter_tab_widget)
        left_vertical_splitter.addWidget(self.__file_reader_widget)
        left_vertical_splitter.addWidget(self.__analyzer_settings_widget)
        left_vertical_splitter.addWidget(self.__plot_spectrogram_widget)
        left_vertical_splitter.setStretchFactor(1, 2)

        # set tool tips
        self.__analyzer_settings_widget.dataFilePatternLineEdit.setToolTip(
        """
        .* match any sequence of characters e.g "sweep_1.mat" -> ".*"
        text: match a specific text to file name e.g. "sweep_1.mat" -> "sweep_1"
        \\ : turn special regEx characters into normal characters e.g. "sweep_1.mat" -> "sweep_1\\.mat"
        \\d: matches a digit (equal to [0-9]) e.g. "sweep_1.mat" -> "sweep_\\d\\.mat"
        +: matches 1 or more repetitions of the preceding symbol. e.g. "sweep_1.mat" -> "sweep_\\d+\\.mat"
        (): capture group/number use for sorting files e.g. "sweep_1.mat" -> ".*(\\d+)\\.mat"  
        """ 
        )


        # Write to log panel
        sys.stdout = self
        sys.stderr = self
        self.__logging_handler = logging.StreamHandler(self)
        self.__logging_handler.setFormatter(logging.getLogger().handlers[0].formatter)
        self.__logging_handler.setLevel(logging.getLogger().handlers[0].level)
        logging.getLogger().addHandler(self.__logging_handler)
        self.__signal_write.connect(self.slot_log_write)

        # menu bar
        self.setMenuBar(menu_bar := QMenuBar())
        menu_file = menu_bar.addMenu("&File")
        menu_window = menu_bar.addMenu("&Window")
        menu_help = menu_bar.addMenu("&Help")

        # actions
        self.__action_open = QAction("&Open Folder")
        menu_file.addAction(self.__action_open)
        self.__action_open_npz = QAction("&Open Peak Fitted File")
        menu_file.addAction(self.__action_open_npz)

        panels = [
            (self.__peak_tracking_widget, "Peak Tracking"),
            (self.__analyzer_settings_widget, "Analyzer Setting"),
            (self.__plot_spectrogram_widget, "Spectrogram Plotter"),
            (self.__sweep_plotter_tab_widget, "Sweep Plotter"),
        ]
        for widget, string in panels:
            action = QAction(string, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(widget.setVisible)
            menu_window.addAction(action)

        self.__action_open_help = QAction("&Open RA Guide")
        menu_help.addAction(self.__action_open_help)
        self.__action_open_help.triggered.connect(self.slot_open_browser)
        

    # stdout and logger redirection requirement
    def write(self, m):
        self.__signal_write.emit(m)

    # stdout and logger redirection requirement
    def flush(self):
        pass

    @Slot()
    def slot_log_write(self, text):
        self.__text_browser.moveCursor(QTextCursor.End)  # type: ignore
        self.__text_browser.insertPlainText(text)
        self.__text_browser.ensureCursorVisible()

    def closeEvent(self, event: QCloseEvent):
        self.signal_close.emit()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        logging.getLogger().removeHandler(self.__logging_handler)
        return super().closeEvent(event)

    # Slots
    def slot_action_open_folder(self):
        if dir := QFileDialog.getExistingDirectory():
            logger.info(f"Opening {dir}")
            self.model_dir = dir
            files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]

            def extract_number_from_filename(filename):
                # Use regular expression to extract the number at the end of the filename
                match = re.search(r"\d+(?=.mat$)", filename)
                return int(match.group()) if match else float("inf")

            sorted_files = sorted(files, key=extract_number_from_filename)
            self.model.setStringList(sorted_files)

            os.chdir(dir)

            self.__peak_tracking_widget.setEnabled(False)
            self.__plot_spectrogram_widget.setEnabled(False)
            self.__analyzer_settings_widget.timestampComboBox.clear()
            self.__analyzer_settings_widget.timestampComboBox.addItem("0.25")

            pat = re.compile(r".*time.*\.csv")
            for f in filter(lambda x: pat.match(x), iter(os.listdir(dir))):
                self.__analyzer_settings_widget.timestampComboBox.addItem(str(f))
                self.__analyzer_settings_widget.timestampComboBox.setCurrentIndex(
                    self.__analyzer_settings_widget.timestampComboBox.count() - 1
                )

        else:
            logger.info("Open folder cancelled")

    def slot_open_browser(self):
        webbrowser.open("https://docs.google.com/document/d/1xOxcPlz0ombHXMdi0A5esTcf2OBMxV9mf7XFvUFK3m4/edit?usp=drive_link")

    def find_file(self, directory_path, file_name):
        for root, dirs, files in os.walk(directory_path):
            if file_name in files:
                return os.path.join(root, file_name)

        return None

    def slot_action_open_npz(self):
        self.slot_action_open_folder()
        self.__npz_spectrogram_path = self.find_file(
            self.model_dir, "ra_spectrograms.npz"
        )
        self.__npz_sweep_path = self.find_file(self.model_dir, "ra_peaks.npz")

        if self.__npz_spectrogram_path and self.__npz_sweep_path:
            self.__peak_tracking_widget.buttons.startFitAndTrack.setEnabled(True)
            logging.info(
                "Successfully load peak fitted (.npz) and spectrogram files at "
                + str(self.model_dir)
            )
        else:
            logger.info("No npz files found")
            return

    def slot_file_change(self, model_index):
        if model_index is None:
            model_index = self.__file_reader_widget.currentIndex()

        file_path = os.path.join(str(self.model_dir), str(model_index.data()))
        file_name = str(model_index.data())
        _, file_ext = os.path.splitext(file_name)

        if file_ext != ".mat":
            logger.error(f"{file_name} is not a matlab workspace file")
        else:
            self.__sweep_plotter_tab_widget.start_worker(file_path)

        return file_path

    def slot_plot_spectrogram(self):
        try:
            # Plot Spectrograms
            self.__plot_spectrogram_widget.start_worker(self.__reader)

            # TODO: optional: shift half pixel in x&y direction to align pixel center to axis tick

        except Exception as e:
            logging.error(str(e))
            raise e

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

    def slot_load_analyzer(self):
        if self.__analyzer_settings_widget.loadFilesButton.text() == "Edit Analyzer Settings":
            self.__analyzer_settings_widget.timestampComboBox.setEnabled(True)
            self.__analyzer_settings_widget.timeMultiplierLineEdit.setEnabled(True)
            self.__analyzer_settings_widget.timeMultiplierUnitLineEdit.setEnabled(True)
            self.__analyzer_settings_widget.dataFilePatternLineEdit.setEnabled(True)
            self.__analyzer_settings_widget.loadFilesButton.setText("Load .matlab Settings")

            # disable other widgets
            self.__peak_tracking_widget.setEnabled(False)
            self.__plot_spectrogram_widget.setEnabled(False)
            return
        
        else:
            folder_path = self.__analyzer_settings_widget.dataFilePattern
            timestamp = self.__analyzer_settings_widget.timestamp
            timestamp_multiplier = self.__analyzer_settings_widget.timeMultiplier
            multiplierUnit = self.__analyzer_settings_widget.timeMultiplierUnit

            # load analyzer parameters
            try:
                pattern = re.compile(eval(self.__analyzer_settings_widget.dataFilePattern))
                time_multiplier = float(eval(timestamp_multiplier))

            except Exception as e:
                logger.error(f"{e}")
                raise e

            try:
                timestamp = float(timestamp)
            except ValueError as e:  # if parse float failed
                if re.match(r".*\.csv", timestamp):
                    pass
                else:
                    logger.error(f"'{timestamp}' is not a number or a csv file")
                    raise e

            self.__peak_tracking_widget.buttons.toggle_buttons(True)

            if self.__npz_sweep_path is None and self.__npz_spectrogram_path is None:
                path = str(self.model_dir)
                filelist_sorted: list = list(filter(pattern.match, os.listdir(path)))

                # check if regex sorting is given 
                try: 
                    filelist_sorted = sorted(
                        filelist_sorted,
                        key = lambda x: int(pattern.match(x).group(1)), # type: ignore
                    )
                    self.__peak_tracking_widget.buttons.startFitAndTrack.setEnabled(True)
                    self.__plot_spectrogram_widget.setEnabled(True)

                except IndexError:
                    logging.info(" Cannot sort files. Peak Tracking and Spectrogram will be disabled to prevent inaccurate results.")
                    self.__peak_tracking_widget.buttons.startFitAndTrack.setEnabled(False)

                self.__reader: DataReaderBase = MatDataReader.new(
                    path,
                    filelist := filelist_sorted, # type: ignore
                    timestamp,
                    time_multiplier,
                )
                # read the first valid file to get the number of channels
                channel_num = read_mat(os.path.join(path, filelist[0]))[0].shape[0]
                self.__peak_tracking_widget.buttons.startTrack.setEnabled(False)
                self.__peak_tracking_widget.channelSelector.setEnabled(True)
                self.__peak_tracking_widget.channelSelector.selections = [
                    True
                ] * channel_num

                self.__analyzer_settings_widget.timestampComboBox.setEnabled(False)
                self.__analyzer_settings_widget.timeMultiplierLineEdit.setEnabled(False)
                self.__analyzer_settings_widget.timeMultiplierUnitLineEdit.setEnabled(False)
                self.__analyzer_settings_widget.dataFilePatternLineEdit.setEnabled(False)
                self.__analyzer_settings_widget.loadFilesButton.setText("Edit Analyzer Settings")
            else:
                path = str(os.path.dirname(self.__npz_sweep_path))
                self.__reader: DataReaderBase = NPZDataReader.new(
                    str(self.__npz_sweep_path),
                    str(self.__npz_spectrogram_path),
                    timestamp_input=timestamp, # type: ignore
                )
                channel_num = self.__reader[0][2].shape[0]
                self.__peak_tracking_widget.channelSelector.selections = [
                    True
                ] * channel_num

            file_num = len(self.__reader)
            self.__peak_tracking_widget.data_reader = self.__reader
            self.__peak_tracking_widget.time_unit = multiplierUnit
            self.__peak_tracking_widget.restart_workers()

            # update max min in spectrogram gram and peak tracking widgets
            self.__plot_spectrogram_widget.update_values(file_num, channel_num)
            self.__peak_tracking_widget.update_values(file_num, path, channel_num)
            self.__peak_tracking_widget.setEnabled(True)
            self.__peak_tracking_widget.buttons.savePeakFit.setEnabled(False)
            self.__peak_tracking_widget.buttons.saveButton.setEnabled(False)

            # TODO clear tabs before populating or only populate if needed

        # populate tabs
        for i in range(
            self.__peak_tracking_widget.peak_tracking_settings.algo_args.peakTrackingStackedWidget.count()
        ):
            widget: RaPeakTrackingArgsTab = self.__peak_tracking_widget.peak_tracking_settings.algo_args.peakTrackingStackedWidget.widget(
                i
            )  # type:ignore
            widget.add_tab(channel_num)

            self.__sweep_plotter_tab_widget.populate_tab(powers=channel_num)

    def slot_track_peak(self):
        self.update_param()
        self.__peak_tracking_widget.slot_clicked_peak_track()

    def slot_fit_track_peak(self):
        self.update_param()
        self.__peak_tracking_widget.buttons.toggle_buttons(False)
        self.__peak_tracking_widget.slot_clicked_peak_track_and_fit()

    def slot_save_peak_fit(self):
        self.__peak_tracking_widget.slot_clicked_save_peak_fit()

    def slot_save_results(self):
        self.__peak_tracking_widget.slot_clicked_save_results()

    def slot_FSR_ER_Q(self):
        self.update_param()
        self.__peak_tracking_widget.slot_clicked_FSR_ER_Q()

    def update_param(self):
        # update variables in peak tracking class
        self.__peak_tracking_widget.r2_threshold = (
            self.__sweep_plotter_tab_widget.param_tab.r2_threshold
        )
        self.__peak_tracking_widget.n100dBm_tolerance = (
            self.__sweep_plotter_tab_widget.param_tab.n100dBm_tolerance
        )
        self.__peak_tracking_widget.gaussian_filter = (
            self.__sweep_plotter_tab_widget.param_tab.gaussian_filter
        )
        self.__peak_tracking_widget.prominence_scalar = (
            self.__sweep_plotter_tab_widget.param_tab.prominence_scalar
        )
