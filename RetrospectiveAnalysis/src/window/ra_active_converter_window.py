import logging
import os
import re
import sys
from functools import partial, reduce
from itertools import cycle, repeat
from logging import getLogger
from multiprocessing import Pool
from typing import Any, Optional, Callable
import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from pyqtgraph import (
    GraphicsLayoutWidget,
    ImageView,
    PlotItem,
)
import pyqtgraph.exporters as exporters
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QTextCursor, QTransform
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from scipy.io import savemat
from scipy.signal import impulse2, lsim, sawtooth, step
from tqdm import tqdm

from ..core.active_tools import (
    AdvancedCSVReaderBase,
    AdvancedRampDownCSVReader,
    AdvancedRampUpCSVReader,
    AdvancedRampUpDownCSVReader,
    ConverterConfig,
    CSVData,
    RampType,
    SimpleRampCSVReaderBase,
    SimpleRampDownCSVReader,
    SimpleRampUpCSVReader,
    SimpleRampUpDownCSVReader,
)
from ..core.lib import find_peak_and_properties
from ..core.utils.tqdm_qt import tqdm_qt
from ..uic.active import active_rc  # noqa: F401
from ..uic.active.ra_active_converter_window import Ui_MainWindow
from ..widgets.active.ra_conversion_tabs import (
    ConversionRCTFTab,
    ConversionTabBase,
    ConversionZPTFTab,
    ConversionNumDenTFTab,
)
from ..widgets.active.ra_fsr_tab_widget import (
    RaActiveConverterFSRTabWidget,
)
from ..widgets.active.ra_regulation_tabs import (
    RegulationPhaseShifterTab,
    RegulationPolynomialTab,
    RegulationTabBase,
)
from ..widgets.lib.ra_progress_bar import RaProgressBar
from ..widgets.lib.utils.ra_qthread_worker import RaQThreadWorker
from ..widgets.active.ra_data_slicing_tabs import (
    RaActiveDataSlicingWidget,
    DataSlicingTabBase,
)

logger = getLogger(__name__)

CONFIG_CSV_DEFAULT_NAME = "ra_config.csv"
OUTPUT_SUBDIR_DEFAULT_NAME = "passive"


# internal multiprocessing functions
def _interpolate_2d_spectrogram_data(data_2d: NDArray, interp_len: int) -> NDArray:
    return np.array(
        [
            np.interp(np.linspace(0, 1, interp_len), np.linspace(0, 1, len(x)), x)
            for x in data_2d
        ]
    )


def _advanced_reader_to_scatter(
    ref_data_start_stop: tuple[NDArray, NDArray, int, int],
    polarity: int,
    central_wavelength: float,
):
    ref, data, start, stop = ref_data_start_stop
    scatters = [[] for i in range(data.shape[0])]
    wls = ref * polarity + central_wavelength
    indices = np.argsort(wls)
    wls = wls[indices]
    for i, channel in enumerate(data):
        channel = channel[indices]
        # use peak finding result
        peak_indices, _, _, _ = find_peak_and_properties(channel)
        wl_array = wls[peak_indices]
        fsr_array = np.diff(wl_array)
        for p, f in zip(wl_array, fsr_array):
            scatters[i].append([p, f])

        # # use precise fitting result
        # sweep = ..core.lib.SweepFitResult.from_data(channel, wls) # import SweepFitResult and edit this line
        # fsr = sweep.get_fsr(0.0001)
        # if len(fsr) >= 1:
        #     wl = sweep.get_peaks(0.0001).T[0]
        #     for w, f in zip(wl, fsr):
        #         scatters[i].append([w, f])

    return scatters


def _advanced_reader_to_passive_format(
    index_ref_data_start_stop: tuple[int, tuple[NDArray, NDArray, int, int]],
    polarity: int,
    central_wavelength: float,
    interp_len: int,
    output_dir: str,
):
    index, (ref, data, start, stop) = index_ref_data_start_stop
    wls = ref * polarity + central_wavelength
    indices = np.argsort(wls)
    wls = wls[indices]
    wls_interp = np.linspace(np.min(wls), np.max(wls), interp_len)
    power_2d = [[] for i in range(data.shape[0])]
    for i, channel in enumerate(data):
        channel = channel[indices]
        channel_interp = np.interp(wls_interp, wls, channel)
        power_2d[i] = channel_interp

    ret: dict[str, NDArray] = {
        "power": np.array(power_2d).T,
        "wavelength": 1e-9 * wls_interp,
    }

    savemat(os.path.join(output_dir, f"active_sweep_{index}.mat"), ret)


class RaActiveConverterWindow(QMainWindow):
    __signal_write = Signal(str)
    signal_close = Signal()
    signal_progress = Signal(dict)

    def __init__(
        self, folder_path: str, parent: Optional[QWidget] = None, *args, **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.__ui = Ui_MainWindow()
        self.__ui.setupUi(self)

        self.__folder_path = folder_path
        self.__csv_reader: SimpleRampUpCSVReader = None  # type: ignore
        self.__advanced_csv_reader: AdvancedCSVReaderBase = None  # type: ignore

        # status bar
        self.__ui.statusbar.addPermanentWidget(QLabel("RA Active Converter"))
        self.__progress_bar = RaProgressBar()
        self.__progress_bar.hide()
        self.__ui.statusbar.addWidget(self.__progress_bar)
        self.signal_progress.connect(self.slot_signal_progress)

        # sweep raw preview
        self.__sweep_raw_preview_widget = GraphicsLayoutWidget()
        self.__ui.rawPreviewPlotPlaceholderWidget.setLayout(QHBoxLayout())
        self.__ui.rawPreviewPlotPlaceholderWidget.layout().addWidget(
            self.__sweep_raw_preview_widget
        )
        self.__sweep_raw_preview_widget_ramp_plot: PlotItem = (
            self.__sweep_raw_preview_widget.addPlot(row=1, col=0)
        )
        self.__sweep_raw_preview_widget_data_plot: PlotItem = (
            self.__sweep_raw_preview_widget.addPlot(row=0, col=0)
        )
        self.__sweep_raw_preview_widget_data_plot.addLegend()
        self.__sweep_raw_preview_widget_data_plot.setXLink(
            self.__sweep_raw_preview_widget_ramp_plot.getViewBox()
        )
        self.__ui.rawLoadPushButton.clicked.connect(
            self.slot_on_sweep_raw_preview_setting_load
        )
        self.__ui.rawPreviewFileComboBox.currentIndexChanged.connect(
            self.slot_on_sweep_raw_preview_file_changed
        )

        # spectrogram raw preview
        self.__ui.rawSpectrogramPlotPushButton.clicked.connect(
            self.slot_on_plot_spectrogram_clicked
        )

        plot_item = PlotItem()
        plot_item.setLabel(axis="bottom", text="Sweep Number")
        plot_item.setLabel(axis="left", text="Voltage", units="V")
        self.__raw_spectrogram_preview_image_view = ImageView(view=plot_item)

        self.__raw_spectrogram_preview_image_view.ui.roiBtn.hide()
        self.__raw_spectrogram_preview_image_view.ui.menuBtn.hide()
        self.__raw_spectrogram_preview_image_view.getView().invertY(False)
        self.__raw_spectrogram_preview_image_view.getView().setAspectLocked(False)
        self.__raw_spectrogram_preview_image_view.setColorMap(
            pg.colormap.get("inferno")
        )

        self.__raw_spectrogram_widget = QWidget()
        self.__raw_spectrogram_widget.setLayout(QVBoxLayout())
        self.__spectrogram_save_all_button = QPushButton("Save All")
        self.__spectrogram_save_all_button.clicked.connect(self.slot_save_all_spectrogram)
        self.__raw_spectrogram_widget.layout().addWidget(self.__spectrogram_save_all_button)

        # data slicing pop up window
        self.__data_slicing_show_button = QPushButton("Data Slicing Method")
        self.__ui.splitter_2.insertWidget(2, self.__data_slicing_show_button)
        self.__data_slicing_widget = RaActiveDataSlicingWidget()
        self.__data_slicing_show_button.clicked.connect(
            self.slot_show_data_slicing_widget
        )

        self.__spectrogram_worker: Optional[RaQThreadWorker] = None

        # wavelength conversion block diagram
        self.__wavelength_conversion_block_diagram_widget = QSvgWidget(
            ":/diagrams/resources/block_diagram/block_diagram.svg"
        )
        self.__wavelength_conversion_block_diagram_widget.renderer().setAspectRatioMode(
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self.__wavelength_conversion_block_diagram_widget.setMinimumHeight(60)

        self.__ui.splitter.insertWidget(
            0, self.__wavelength_conversion_block_diagram_widget
        )
        self.__ui.splitter.setStretchFactor(0, 0)
        self.__ui.splitter.setStretchFactor(1, 1)
        self.__ui.splitter.setSizes([1, 5, 1])

        # File config 
        self.__ui.skipRowsSpinBox.setValue(12)
        self.__ui.rawRampChannelSpinBox.setValue(3)

        # input regulation
        self.__ui.inputRegulationComboBox.currentIndexChanged.connect(
            self.__ui.inputRegulationStackedWidget.setCurrentIndex
        )

        self.__input_regulation_thermal_phase_shifter_tab = RegulationPhaseShifterTab()
        self.__ui.inputRegulationStackedWidget.addWidget(
            self.__input_regulation_thermal_phase_shifter_tab
        )

        self.__input_regulation_polynomial_tab = RegulationPolynomialTab()
        self.__ui.inputRegulationStackedWidget.addWidget(
            self.__input_regulation_polynomial_tab
        )

        self.__ui.inputRegulationComboBox.addItems(
            ["Thermal Phase Shifter", "Polynomial"]
        )
        self.__ui.inputRegulationComboBox.setCurrentIndex(0)

        # conversion methods
        self.__ui.conversionMethodComboBox.currentIndexChanged.connect(
            self.__ui.conversionMethodStackedWidget.setCurrentIndex
        )

        self.__rctf_tab = ConversionRCTFTab()
        self.__ui.conversionMethodStackedWidget.addWidget(self.__rctf_tab)

        self.__ZPGTF_tab = ConversionZPTFTab()
        self.__ui.conversionMethodStackedWidget.addWidget(self.__ZPGTF_tab)

        self.__NumDemonTF_tab = ConversionNumDenTFTab()
        self.__ui.conversionMethodStackedWidget.addWidget(self.__NumDemonTF_tab)

        self.__ui.conversionMethodComboBox.addItems(["RC Circuit", "Zero-Pole","Numerator-Demonenator"])
        self.__ui.conversionMethodComboBox.setCurrentIndex(0)

        self.__conversion_method_visualize_button = QPushButton("Visualize")
        self.__conversion_method_visualize_button.clicked.connect(
            self.slot_on_wavelength_conversion_plot_clicked
        )
        self.__ui.conversionMethodSplitter.insertWidget(
            self.__ui.conversionMethodSplitter.count() - 1,
            self.__conversion_method_visualize_button,
        )

        self.__conversion_method_graphics_layout_widget = GraphicsLayoutWidget()
        self.__conversion_method_impulse_response_plot: PlotItem = (
            self.__conversion_method_graphics_layout_widget.addPlot(
                title="Impulse Response"
            )
        )
        self.__conversion_method_step_response_plot: PlotItem = (
            self.__conversion_method_graphics_layout_widget.addPlot(
                title="Step Response"
            )
        )
        self.__conversion_method_periodic_response_plot: PlotItem = (
            self.__conversion_method_graphics_layout_widget.addPlot(
                title="Periodic Response"
            )
        )
        self.__ui.conversionMethodSplitter.insertWidget(
            self.__ui.conversionMethodSplitter.count() - 1,
            self.__conversion_method_graphics_layout_widget,
        )

        # Plot Setting
        self.__ui.plotPushButton.clicked.connect(self.slot_on_plot_FSR_clicked)

        # Output Path
        self.__ui.outputPathPushButton.clicked.connect(
            self.slot_select_output_path_clicked
        )
        default_output_path = os.path.join(
            self.__folder_path, OUTPUT_SUBDIR_DEFAULT_NAME
        )
        self.__ui.outputPathComboBox.setCurrentText(default_output_path)
        self.__ui.outputPathComboBox.addItem(default_output_path)

        # load csv config
        if os.path.exists(
            config_path := os.path.join(self.__folder_path, CONFIG_CSV_DEFAULT_NAME)
        ):
            csv_config = ConverterConfig.from_csv(config_path)
            self.__ui.skipRowsSpinBox.setValue(csv_config.skip_row)
            self.__ui.skipColumnsSpinBox.setValue(csv_config.skip_column)
            self.__ui.rawRegexLineEdit.setText(csv_config.filename_prefix)
            self.__ui.rawRampChannelSpinBox.setValue(csv_config.ramp_channel)
            self.__ui.rampSymmetryDoubleSpinBox.setValue(
                csv_config.ramp_signal_symmetry
            )
            self.__ui.rampVMinDoubleSpinBox.setValue(csv_config.v_min)
            self.__ui.rampVMaxDoubleSpinBox.setValue(csv_config.v_max)
            self.__ui.rampFrequencyDoubleSpinBox.setValue(csv_config.frequency)
            self.__ui.conversionMethodOutputOffsetDoubleSpinBox.setValue(
                csv_config.laser_wavelength
            )
            self.__data_slicing_widget.data_slicing_stacked_widget.setCurrentIndex(2)
            self.__data_slicing_widget.slice_fixed_datapoint_tab.exclude_start_spinbox.setValue(csv_config.exclude_start)
            self.__data_slicing_widget.slice_fixed_datapoint_tab.exclude_stop_spinbox.setValue(csv_config.exclude_end)
            self.__data_slicing_widget.slice_fixed_datapoint_tab.offset.setValue(csv_config.offset)
            self.__data_slicing_widget.slice_fixed_datapoint_tab.fixed_datapoint.setValue(csv_config.fixed_datapoints)

            self.__input_regulation_polynomial_tab.a_array_line_edit.setText(
                str(csv_config.a_array)
            )
            self.__input_regulation_polynomial_tab.x_array_line_edit.setText(
                str(csv_config.x_array)
            )
            self.__input_regulation_thermal_phase_shifter_tab.fsr_double_spinbox.setValue(
                csv_config.fsr * 1e9
            )
            self.__input_regulation_thermal_phase_shifter_tab.p_fsr_double_spinbox.setValue(
                csv_config.p_fsr * 1e3
            )
            self.__input_regulation_thermal_phase_shifter_tab.r_double_spinbox.setValue(
                csv_config.r_heater
            )
            self.__input_regulation_thermal_phase_shifter_tab.v_offset_double_spinbox.setValue(
                csv_config.v_offset
            )
            
            if csv_config.method1:
                self.__ui.inputRegulationComboBox.setCurrentIndex(1)
            elif csv_config.method2:
                self.__ui.inputRegulationComboBox.setCurrentIndex(0)

            # calculate r, c arrays from csv config and move to the right tab 
            if csv_config.thermal_method1:
                self.__ui.conversionMethodStackedWidget.setCurrentIndex(0)
            elif csv_config.thermal_method2:
                # ZP parameters
                self.__ui.conversionMethodStackedWidget.setCurrentIndex(1)
            elif csv_config.thermal_method3:
                # Num/Denom parameters
                self.__ui.conversionMethodStackedWidget.setCurrentIndex(2)

            rc_length = max(
                len(csv_config.r_array),
                len(csv_config.c_array),
                len(csv_config.tau_array),
            )
            r_array_pad = csv_config.r_array + [None] * (
                rc_length - len(csv_config.r_array)
            )
            c_array_pad = csv_config.c_array + [None] * (
                rc_length - len(csv_config.c_array)
            )
            tau_array_pad = csv_config.tau_array + [None] * (
                rc_length - len(csv_config.tau_array)
            )

            r_array: list[float] = []
            c_array: list[float] = []

            for r, c, tau in zip(r_array_pad, c_array_pad, tau_array_pad):
                match r, c, tau:
                    case float(r), float(c), None:
                        r_array.append(r)
                        c_array.append(c)
                    case float(r), None, float(tau):
                        r_array.append(r)
                        c_array.append(tau / r)
                    case None, float(c), float(tau):
                        r_array.append(tau / c)
                        c_array.append(c)
                    case _:
                        raise ValueError(
                            f"Invalid R C Tau array. Received r={r}, c={c}, tau={tau}"
                        )

            # RC parameters
            self.__rctf_tab.rs_line_edit.setText(str(r_array))
            self.__rctf_tab.cs_line_edit.setText(str(c_array))

            self.__ZPGTF_tab.zs_line_edit.setText(str(csv_config.z_array))
            self.__ZPGTF_tab.ps_line_edit.setText(str(csv_config.p_array))
            
            self.__NumDemonTF_tab.num_line_edit.setText(str(csv_config.num_array))
            self.__NumDemonTF_tab.denom_line_edit.setText(str(csv_config.denom_array))

        else:  # no config file, use ui default values
            pass

        # add a window manager on menu bar
        menu = QMenu("Window", self)
        panels: list[tuple[QWidget, str]] = [
            (self.__ui.sweepRawPreviewSettingGroupBox, "Sweep Raw Preview Setting"),
            (self.__ui.sweepRawPreviewGroupBox, "Sweep Raw Preview"),
            (self.__ui.rampSignalConfigGroupBox, "Ramp Signal Config"),
            (self.__ui.spectrogramRawPreviewGroupBox, "Spectrogram Raw Preview"),
            (self.__ui.fsrPlotSettingGroupBox, "FSR Plot Setting"),
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

    def slot_save_all_spectrogram(self):
        if self.__raw_spectrogram_widget.layout().count() == 0:
            raise RuntimeError("No spectrogram to save")

        self.__raw_spectrogram_widget.showMaximized()
        dir = QFileDialog.getExistingDirectory()
        for index in range(1, self.__raw_spectrogram_widget.layout().count()):
            file_name = f"Power {index} Spectrogram.png"
            widget : ImageView = self.__raw_spectrogram_widget.layout().itemAt(index).widget() # type: ignore
            exporter = exporters.ImageExporter(widget.view)
            exporter.export(os.path.join(dir, file_name))
        
        logger.info(f"Spectrograms saved at {dir}")

    # stdout and logger redirection requirement
    def write(self, m):
        self.__signal_write.emit(m)

    # stdout and logger redirection requirement
    def flush(self):
        pass

    def slot_log_write(self, text):
        self.__ui.textBrowser.moveCursor(QTextCursor.End)  # type: ignore
        self.__ui.textBrowser.insertPlainText(text)
        self.__ui.textBrowser.ensureCursorVisible()

    def slot_show_data_slicing_widget(self):
        self.__data_slicing_widget.show()

    def closeEvent(self, event: QCloseEvent):
        self.signal_close.emit()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        logging.getLogger().removeHandler(self.__logging_handler)
        return super().closeEvent(event)

    # Custom Slots
    def slot_on_sweep_raw_preview_setting_load(self):
        self.__ui.plotTabWidget.setEnabled(False)
        self.__ui.rawPreviewFileComboBox.blockSignals(True)

        pattern = re.compile(self.__ui.rawRegexLineEdit.text())

        data_slicing_tab: DataSlicingTabBase = self.__data_slicing_widget.data_slicing_stacked_widget.currentWidget()  # type: ignore
        data_slicing_function : Callable = data_slicing_tab.to_slicing_func()

        # set up csv reader
        match RampType.from_float(
            int(self.__ui.rampSymmetryDoubleSpinBox.value()) / 100
        ):
            case RampType.UP:
                reader_type = SimpleRampUpCSVReader
            case RampType.DOWN:
                reader_type = SimpleRampDownCSVReader
            case RampType.TRIANGLE:
                reader_type = SimpleRampUpDownCSVReader
            case _:
                raise ValueError(
                    "Only support ramp symmetry of 0 (down), 50 (triangular), 100 (up)"
                )
        ramp_channel = self.__ui.rawRampChannelSpinBox.value() - 1 if self.__ui.rawRampChannelSpinBox.value() != 0 else None

        self.__csv_reader: SimpleRampCSVReaderBase = reader_type(
            folder_path=self.__folder_path,
            pattern=pattern,
            skip_rows=self.__ui.skipRowsSpinBox.value(),
            skip_columns=self.__ui.skipColumnsSpinBox.value(),
            ramp_channel=ramp_channel,
            data_slicing_method=data_slicing_function,
        )

        # set up file list
        filenames = sorted(
            list(
                filter(lambda x: pattern.match(x), iter(os.listdir(self.__folder_path)))
            ),
            key=lambda x: int(pattern.match(x).group(1)),  # type: ignore
        )
        self.__ui.rawPreviewFileComboBox.clear()
        self.__ui.rawPreviewFileComboBox.addItems(filenames)

        # set up plot tabs according to the number of channels
        self.__ui.plotTabWidget.clear()
        channel_num = self.__csv_reader.data_shape[0]
        for i in range(channel_num):
            self.__ui.plotTabWidget.addTab(
                RaActiveConverterFSRTabWidget(), f"Channel {i+1}"
            )

        self.__ui.rawSpectrogramPlotPushButton.setEnabled(True)
        self.__ui.plotPushButton.setEnabled(True)

        self.__ui.rawPreviewFileComboBox.blockSignals(False)
        self.slot_on_sweep_raw_preview_file_changed()

    def slot_on_sweep_raw_preview_file_changed(self):
        self.__sweep_raw_preview_widget_data_plot.clear()
        self.__sweep_raw_preview_widget_ramp_plot.clear()

        # get CSV data from selected file
        csv_data = CSVData(
            file_path=os.path.join(
                self.__folder_path, self.__ui.rawPreviewFileComboBox.currentText()
            ),
            skip_rows=self.__csv_reader.skip_rows,  # type: ignore
            skip_columns=self.__csv_reader.skip_columns,  # type: ignore
            ramp_channel=self.__csv_reader.ramp_channel,  # type: ignore
        )

        # plot sweep data and ramp data
        color_palette = cycle(["r", "g", "b", "c", "m", "y", "k"])
        for i, channel in enumerate(csv_data.data):
            self.__sweep_raw_preview_widget_data_plot.plot(
                channel, pen=next(color_palette), name=f"Channel {i+1}"
            )
        self.__sweep_raw_preview_widget_data_plot.getAxis("bottom").setLabel(
            text="#Sample Point"
        )
        self.__sweep_raw_preview_widget_data_plot.getAxis("left").setLabel(text="Power")

        self.__sweep_raw_preview_widget_ramp_plot.plot(csv_data.ramp)
        self.__sweep_raw_preview_widget_ramp_plot.getAxis("bottom").setLabel(
            text="#Sample Point"
        )
        self.__sweep_raw_preview_widget_ramp_plot.getAxis("left").setLabel(text="Power")

        # if plot tab widget is enabled, update converted sweep stream data
        if self.__ui.plotTabWidget.isEnabled():
            selected_file_basename = self.__ui.rawPreviewFileComboBox.currentText()
            file_index: str = re.compile(self.__ui.rawRegexLineEdit.text()).match(selected_file_basename).group(1)  # type: ignore
            pattern = re.compile(selected_file_basename.replace(file_index, f"({file_index})"))  # type: ignore

            if self.__advanced_csv_reader is not None:
                reader = type(self.__advanced_csv_reader)(
                    folder_path=self.__advanced_csv_reader.folder_path,
                    pattern=pattern,
                    skip_rows=self.__advanced_csv_reader.skip_rows,
                    skip_columns=self.__advanced_csv_reader.skip_columns,
                    ramp_channel=self.__advanced_csv_reader.ramp_channel,
                    lti_sys=self.__advanced_csv_reader.lti_sys,
                    frequency=self.__advanced_csv_reader.frequency,
                    x_min=self.__advanced_csv_reader.x_min,
                    x_max=self.__advanced_csv_reader.x_max,
                    regulation_func=self.__advanced_csv_reader.regulation_func,
                    data_slicing_func=self.__advanced_csv_reader.data_slicing_func,
                )

                def generate_equalized_number(
                    ref_data_start_stop: tuple[
                        NDArray[np.floating], NDArray[np.floating], int, int
                    ],
                ):
                    ref, data, start, stop = ref_data_start_stop
                    num = ref.copy()
                    num -= np.min(ref)
                    num /= np.max(ref) - np.min(ref)
                    num *= stop - start
                    num += start
                    power_number_2d = [[] for i in range(data.shape[0])]
                    for i, channel in enumerate(data):
                        power_number_2d[i] = [num, channel]
                    return power_number_2d

                y_2d = reduce(
                    lambda acc, x: np.array(
                        [np.hstack((a, x[i])) for i, a in enumerate(acc)]
                    ),
                    map(
                        generate_equalized_number,
                        reader,
                    ),
                    np.array(
                        [
                            np.array([[], []])
                            for _ in range(self.__ui.plotTabWidget.count())
                        ]
                    ),
                )

                for i in range(self.__ui.plotTabWidget.count()):
                    tab: RaActiveConverterFSRTabWidget = self.__ui.plotTabWidget.widget(i)  # type: ignore
                    tab.set_stream_plot(y_2d[i].T)

    def slot_on_plot_spectrogram_clicked(self):
        interp_len = self.__ui.rawSpectrogramInterpolateSpinBox.value()
        data_slicing_function = self.__data_slicing_widget.data_slicing_stacked_widget.currentWidget().to_slicing_func()  # type: ignore
        self.__csv_reader.data_slicing_method = data_slicing_function # type: ignore
        
        def get_spectrogram_data():
            with Pool() as pool:
                return np.array(
                    list(
                        pool.starmap(
                            _interpolate_2d_spectrogram_data,
                            zip(
                                map(lambda x: x[0], self.__csv_reader),
                                repeat(interp_len),
                            ),
                        )
                    )
                ).swapaxes(0, 1)

        if (
            self.__spectrogram_worker is not None
            and self.__spectrogram_worker.isRunning()
        ):
            return
        else:
            self.__ui.rawSpectrogramPlotPushButton.setEnabled(False)
            self.__ui.rawPreviewFileComboBox.setEnabled(False)

            self.__spectrogram_worker = RaQThreadWorker(f=get_spectrogram_data)
            self.__spectrogram_worker.finished.connect(self.slot_plot_spectrogram_done)
            self.__spectrogram_worker.start()

    def slot_plot_spectrogram_done(self):
        self.__ui.rawSpectrogramPlotPushButton.setEnabled(True)
        self.__ui.rawPreviewFileComboBox.setEnabled(True)
        data_interpolated = self.__spectrogram_worker.result  # type: ignore
        self.__spectrogram_worker.deleteLater()  # type: ignore
        self.__spectrogram_worker = None

        while self.__raw_spectrogram_widget.layout().count() > 1:
            self.__raw_spectrogram_widget.layout().takeAt(0).widget().deleteLater()

        view_box = None
        for i, channel in enumerate(data_interpolated):
            plot_item = PlotItem()
            plot_item.setLabel(axis="bottom", text="Sweep Number")
            plot_item.setLabel(axis="left", text="Voltage", units="V")
            plot_item.setTitle(f"Channel {i+1}")
            if view_box is None:
                view_box = plot_item.getViewBox()
            else:
                plot_item.setXLink(view_box)
                plot_item.setYLink(view_box)

            image_view = ImageView(view=plot_item)
            image_view.ui.roiBtn.hide()
            image_view.ui.menuBtn.hide()
            image_view.getView().invertY(False)
            image_view.getView().setAspectLocked(False)
            image_view.setColorMap(pg.colormap.get("inferno"))
            image_view.setImage(channel)
            tr = QTransform()
            tr.scale(
                1,
                (
                    self.__ui.rampVMaxDoubleSpinBox.value()
                    - self.__ui.rampVMinDoubleSpinBox.value()
                )
                / channel.shape[1],
            )
            tr.translate(0, self.__ui.rampVMinDoubleSpinBox.value())
            image_view.imageItem.setTransform(tr)
            image_view.getView().autoRange()

            self.__raw_spectrogram_widget.layout().addWidget(image_view)

        self.__raw_spectrogram_widget.show()

    def slot_on_wavelength_conversion_plot_clicked(self):
        for i in (
            self.__conversion_method_impulse_response_plot,
            self.__conversion_method_step_response_plot,
            self.__conversion_method_periodic_response_plot,
        ):
            i.clear()

        conversion_tab: ConversionTabBase = self.__ui.conversionMethodStackedWidget.currentWidget()  # type: ignore
        system = conversion_tab.to_lti()

        self.__conversion_method_impulse_response_plot.plot(*impulse2(system))
        self.__conversion_method_impulse_response_plot.getAxis("bottom").setLabel(
            units="s"
        )
        self.__conversion_method_step_response_plot.plot(*step(system))
        self.__conversion_method_step_response_plot.getAxis("bottom").setLabel(
            units="s"
        )

        v_min = self.__ui.rampVMinDoubleSpinBox.value()
        v_max = self.__ui.rampVMaxDoubleSpinBox.value()
        width = self.__ui.rampSymmetryDoubleSpinBox.value() / 100
        freq = self.__ui.rampFrequencyDoubleSpinBox.value()

        t_final = 500 / freq
        len_period = 200
        t = np.arange(0, t_final, 1 / freq / len_period)

        voltage = (sawtooth(2 * np.pi * freq * t, width) + 1) / 2  # type: ignore
        voltage *= v_max - v_min
        voltage += v_min

        regulation_tab: RegulationTabBase = self.__ui.inputRegulationStackedWidget.currentWidget()  # type: ignore
        regulation_function = regulation_tab.to_regulate_function()

        input = regulation_function(voltage)  # type: ignore

        t, y, x = lsim(system, input, t)
        t_plot = t[-len_period * 2 :]
        t_plot -= t_plot[0]
        y_plot = y[-len_period * 2 :]
        voltage_plot = voltage[-len_period * 2 :]
        input_plot: list[float] = input[-len_period * 2 :]  # type: ignore

        self.__conversion_method_periodic_response_plot.addLegend()
        self.__conversion_method_periodic_response_plot.getAxis("bottom").setLabel(
            units="s"
        )
        self.__conversion_method_periodic_response_plot.plot(
            t_plot,
            voltage_plot,
            name="V_input",
            pen={"color": "r", "style": Qt.PenStyle.DashLine},
        )
        self.__conversion_method_periodic_response_plot.plot(
            t_plot,
            input_plot,
            name="lambda_target",
            pen={"color": "g", "style": Qt.PenStyle.DashLine},
        )
        self.__conversion_method_periodic_response_plot.plot(
            t_plot,
            y_plot,
            name="lambda_real",
        )

    def slot_on_plot_FSR_clicked_old(self):
        csv_config_path = os.path.join(self.__folder_path, CONFIG_CSV_DEFAULT_NAME)
        csv_config = ConverterConfig(
            skip_row=self.__ui.skipRowsSpinBox.value(),
            skip_column=self.__ui.skipColumnsSpinBox.value(),
            ramp_signal_symmetry=self.__ui.rampSymmetryDoubleSpinBox.value(),
            v_min=self.__ui.rampVMinDoubleSpinBox.value(),
            v_max=self.__ui.rampVMaxDoubleSpinBox.value(),
            laser_wavelength=self.__ui.conversionMethodOutputOffsetDoubleSpinBox.value(),
            data_slicing_methods=None,
            slicing_method1=self.__data_slicing_widget.data_slicing_stacked_widget.currentWidget() 
            is self.__data_slicing_widget.slice_min_max_tab,
            ramp_channel=self.__ui.rawRampChannelSpinBox.value(),
            slicing_method2=self.__data_slicing_widget.data_slicing_stacked_widget.currentWidget() 
            is self.__data_slicing_widget.slice_fixed_datapoint_tab,
            exclude_start=self.__data_slicing_widget.slice_fixed_datapoint_tab.exclude_start_spinbox.value(),
            exclude_end=self.__data_slicing_widget.slice_fixed_datapoint_tab.exclude_stop_spinbox.value(),
            offset=self.__data_slicing_widget.slice_fixed_datapoint_tab.offset.value(),
            fixed_datapoints=self.__data_slicing_widget.slice_fixed_datapoint_tab.fixed_datapoint.value(),
            wavelength_conversion_methods=None,
            method1=self.__ui.inputRegulationStackedWidget.currentWidget()
            is self.__input_regulation_polynomial_tab,
            a_array=list(
                eval(self.__input_regulation_polynomial_tab.a_array_line_edit.text())
            ),
            x_array=list(
                eval(self.__input_regulation_polynomial_tab.x_array_line_edit.text())
            ),
            method2=self.__ui.inputRegulationStackedWidget.currentWidget()
            is self.__input_regulation_thermal_phase_shifter_tab,
            fsr=self.__input_regulation_thermal_phase_shifter_tab.fsr_double_spinbox.value()
            * 1e-9,
            p_fsr=self.__input_regulation_thermal_phase_shifter_tab.p_fsr_double_spinbox.value()
            * 1e-3,
            r_heater=self.__input_regulation_thermal_phase_shifter_tab.r_double_spinbox.value(),
            v_offset=self.__input_regulation_thermal_phase_shifter_tab.v_offset_double_spinbox.value(),
            thermal_response=None,
            thermal_method1=self.__ui.conversionMethodStackedWidget.currentWidget() 
            is self.__ZPGTF_tab,
            r_array=list(eval(self.__rctf_tab.rs_line_edit.text())),
            c_array=list(eval(self.__rctf_tab.cs_line_edit.text())),
            tau_array=list(),
            gain=self.__rctf_tab.gain_double_spinbox.value(),
            thermal_method2=self.__ui.conversionMethodStackedWidget.currentWidget() is 
            self.__ZPGTF_tab,
            z_array=list(eval(self.__ZPGTF_tab.zs_line_edit.text())),
            p_array=list(eval(self.__ZPGTF_tab.ps_line_edit.text())),
            zp_gain=float(0),
            thermal_method3=self.__ui.conversionMethodStackedWidget.currentWidget() is self.__NumDemonTF_tab,
            num_array=list(eval(self.__NumDemonTF_tab.num_line_edit.text())),
            denom_array=list(eval(self.__NumDemonTF_tab.denom_line_edit.text())),
        )

        csv_config.to_csv(csv_config_path)
        logger.info(f"RA-Active-Converter config csv file saved to {csv_config_path}")

    def slot_on_plot_FSR_clicked(self):
        self.__ui.statusbar.clearMessage()
        self.__progress_bar.reset()
        self.__progress_bar.show()

        data_slicing_tab: DataSlicingTabBase = self.__data_slicing_widget.data_slicing_stacked_widget.currentWidget()  # type: ignore
        data_slicing_function = data_slicing_tab.to_slicing_func()

        conversion_tab: ConversionTabBase = self.__ui.conversionMethodStackedWidget.currentWidget()  # type: ignore
        system = conversion_tab.to_lti()

        v_min = self.__ui.rampVMinDoubleSpinBox.value()
        v_max = self.__ui.rampVMaxDoubleSpinBox.value()
        width = self.__ui.rampSymmetryDoubleSpinBox.value() / 100
        freq = self.__ui.rampFrequencyDoubleSpinBox.value()

        regulation_tab: RegulationTabBase = self.__ui.inputRegulationStackedWidget.currentWidget()  # type: ignore
        regulation_function = regulation_tab.to_regulate_function()
        ui_ramp_channel = self.__ui.rawRampChannelSpinBox.value() - 1 if self.__ui.rawRampChannelSpinBox.value() != 0 else None

        match RampType.from_float(width):
            case RampType.UP:
                self.__advanced_csv_reader = AdvancedRampUpCSVReader(
                    self.__folder_path,
                    re.compile(self.__ui.rawRegexLineEdit.text()),
                    self.__ui.skipRowsSpinBox.value(),
                    self.__ui.skipColumnsSpinBox.value(),
                    ui_ramp_channel,
                    system,
                    freq,
                    v_min,
                    v_max,
                    regulation_function,
                    data_slicing_function,
                )

            case RampType.DOWN:
                self.__advanced_csv_reader = AdvancedRampDownCSVReader(
                    self.__folder_path,
                    re.compile(self.__ui.rawRegexLineEdit.text()),
                    self.__ui.skipRowsSpinBox.value(),
                    self.__ui.skipColumnsSpinBox.value(),
                    ui_ramp_channel,
                    system,
                    freq,
                    v_min,
                    v_max,
                    regulation_function,
                    data_slicing_function,
                )
            case RampType.TRIANGLE:
                self.__advanced_csv_reader = AdvancedRampUpDownCSVReader(
                    self.__folder_path,
                    re.compile(self.__ui.rawRegexLineEdit.text()),
                    self.__ui.skipRowsSpinBox.value(),
                    self.__ui.skipColumnsSpinBox.value(),
                    ui_ramp_channel,
                    system,
                    freq,
                    v_min,
                    v_max,
                    regulation_function,
                    data_slicing_function,
                )
            case _:
                raise ValueError(
                    "Only support ramp symmetry of 0% (down), 50% (triangular), 100% (up)"
                )

        polarity = (
            1 if self.__ui.conversionMethodPolarityComboBox.currentIndex() else -1
        )
        central_wavelength = self.__ui.conversionMethodOutputOffsetDoubleSpinBox.value()

        def acc_func(acc: list, x: Any):
            for i, channel in enumerate(x):
                acc[i].extend(channel)
            return acc

        def f():
            with Pool() as pool:
                return reduce(
                    acc_func,
                    tqdm_qt(
                        pool.imap(
                            partial(
                                _advanced_reader_to_scatter,
                                polarity=polarity,
                                central_wavelength=central_wavelength,
                            ),
                            self.__advanced_csv_reader,
                        ),
                        total=len(self.__advanced_csv_reader),
                        qt_signal=self.signal_progress,
                    ),
                    [[] for _ in range(self.__advanced_csv_reader.data_shape[0])],
                )

        self.__fsr_worker = RaQThreadWorker(f)
        self.__fsr_worker.finished.connect(self.slot_on_plot_FSR_finished)
        self.__ui.plotPushButton.setDisabled(True)
        self.__fsr_worker.start()

    def slot_on_plot_FSR_finished(self):
        try:
            scatter = self.__fsr_worker.result
            for i in range(self.__ui.plotTabWidget.count()):
                tab: RaActiveConverterFSRTabWidget = self.__ui.plotTabWidget.widget(i)  # type: ignore
                points = np.array(scatter[i]).T
                try:
                    tab.set_scatter_plot(
                        points[0],
                        points[1],
                        fit=self.__ui.plotTrendlineCheckBox.isChecked(),
                        order=self.__ui.plotTrendlineOrderSpinBox.value(),
                        outlier_range=self.__ui.plotTrendlineOutlierRangeDoubleSpinBox.value()
                        * 1e-3,
                    )
                except IndexError as e:
                    logger.warning(
                        f"channel {i+1} plot failed for the following reason: {e}"
                    )
                    continue

        except Exception as e:
            logger.exception(f'Error occured during FSR plot: {e}')
            self.__ui.plotTabWidget.setEnabled(True)
            self.__ui.plotPushButton.setEnabled(True)
            return
        
        self.__ui.plotTabWidget.setEnabled(True)
        self.__ui.plotPushButton.setEnabled(True)

        # set progress bar to 100%
        self.__progress_bar.text_left = ""
        self.__progress_bar.text_right = "Done"
        self.__progress_bar.value = self.__progress_bar.maximum

        # trigger this slot to update the equalized stream plot
        self.slot_on_sweep_raw_preview_file_changed()

    def slot_select_output_path_clicked(self):
        path = QFileDialog.getExistingDirectory(dir=self.__folder_path)
        if path:
            if path not in [
                self.__ui.outputPathComboBox.itemText(i)
                for i in range(self.__ui.outputPathComboBox.count())
            ]:
                self.__ui.outputPathComboBox.addItem(path)
            self.__ui.outputPathComboBox.setCurrentText(path)

    # Dialog Slots
    def slot_accept(self):
        if self.__csv_reader is None:
            logger.info("Conversion failed with no CSV rules loaded.")
            return

        if self.__advanced_csv_reader is None:
            conversion_tab: ConversionTabBase = self.__ui.conversionMethodStackedWidget.currentWidget()  # type: ignore
            system = conversion_tab.to_lti()

            v_min = self.__ui.rampVMinDoubleSpinBox.value()
            v_max = self.__ui.rampVMaxDoubleSpinBox.value()
            width = self.__ui.rampSymmetryDoubleSpinBox.value() / 100
            freq = self.__ui.rampFrequencyDoubleSpinBox.value()

            data_slicing_tab: DataSlicingTabBase = self.__data_slicing_widget.data_slicing_stacked_widget.currentWidget()  # type: ignore
            data_slicing_function = data_slicing_tab.to_slicing_func()

            regulation_tab: RegulationTabBase = self.__ui.inputRegulationStackedWidget.currentWidget()  # type: ignore
            regulation_function = regulation_tab.to_regulate_function()
            match RampType.from_float(width):
                case RampType.UP:
                    self.__advanced_csv_reader = AdvancedRampUpCSVReader(
                        self.__folder_path,
                        re.compile(self.__ui.rawRegexLineEdit.text()),
                        self.__ui.skipRowsSpinBox.value(),
                        self.__ui.skipColumnsSpinBox.value(),
                        self.__ui.rawRampChannelSpinBox.value() - 1,
                        system,
                        freq,
                        v_min,
                        v_max,
                        regulation_function,
                        data_slicing_function,
                    )
                case RampType.DOWN:
                    self.__advanced_csv_reader = AdvancedRampDownCSVReader(
                        self.__folder_path,
                        re.compile(self.__ui.rawRegexLineEdit.text()),
                        self.__ui.skipRowsSpinBox.value(),
                        self.__ui.skipColumnsSpinBox.value(),
                        self.__ui.rawRampChannelSpinBox.value() - 1,
                        system,
                        freq,
                        v_min,
                        v_max,
                        regulation_function,
                        data_slicing_function,
                    )
                case RampType.TRIANGLE:
                    self.__advanced_csv_reader = AdvancedRampUpDownCSVReader(
                        self.__folder_path,
                        re.compile(self.__ui.rawRegexLineEdit.text()),
                        self.__ui.skipRowsSpinBox.value(),
                        self.__ui.skipColumnsSpinBox.value(),
                        self.__ui.rawRampChannelSpinBox.value() - 1,
                        system,
                        freq,
                        v_min,
                        v_max,
                        regulation_function,
                        data_slicing_function,
                    )
                case _:
                    raise ValueError(
                        "Only support ramp symmetry of 0% (down), 50% (triangular), 100% (up)"
                    )

        polarity = (
            1 if self.__ui.conversionMethodPolarityComboBox.currentIndex() else -1
        )

        interp_len = self.__ui.rawSpectrogramInterpolateSpinBox.value()

        output_dir = self.__ui.outputPathComboBox.currentText()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        def f():
            with Pool() as pool:
                return list(
                    tqdm_qt(
                        pool.imap(
                            partial(
                                _advanced_reader_to_passive_format,
                                polarity=polarity,
                                central_wavelength=self.__ui.conversionMethodOutputOffsetDoubleSpinBox.value(),
                                interp_len=interp_len,
                                output_dir=output_dir,
                            ),
                            enumerate(self.__advanced_csv_reader),
                        ),
                        total=len(self.__advanced_csv_reader),
                        qt_signal=self.signal_progress,
                    )
                )

        self.__convert_worker = RaQThreadWorker(f)
        self.__convert_worker.finished.connect(self.slot_on_conversion_done)

        csv_config_path = os.path.join(self.__folder_path, CONFIG_CSV_DEFAULT_NAME)
        csv_config = ConverterConfig(
            skip_row=self.__ui.skipRowsSpinBox.value(),
            skip_column=self.__ui.skipColumnsSpinBox.value(),
            laser_wavelength=self.__ui.conversionMethodOutputOffsetDoubleSpinBox.value(),
            filename_prefix=self.__ui.rawRegexLineEdit.text(),
            ramp_signal_symmetry=self.__ui.rampSymmetryDoubleSpinBox.value(),
            v_min=self.__ui.rampVMinDoubleSpinBox.value(),
            v_max=self.__ui.rampVMaxDoubleSpinBox.value(),
            frequency=self.__ui.rampFrequencyDoubleSpinBox.value(),
            data_slicing_methods=None,
            slicing_method1=self.__data_slicing_widget.data_slicing_stacked_widget.currentWidget() 
            is self.__data_slicing_widget.slice_min_max_tab,
            ramp_channel=self.__ui.rawRampChannelSpinBox.value(),
            slicing_method2=self.__data_slicing_widget.data_slicing_stacked_widget.currentWidget() 
            is self.__data_slicing_widget.slice_fixed_datapoint_tab,
            exclude_start=self.__data_slicing_widget.slice_fixed_datapoint_tab.exclude_start_spinbox.value(),
            exclude_end=self.__data_slicing_widget.slice_fixed_datapoint_tab.exclude_stop_spinbox.value(),
            offset=self.__data_slicing_widget.slice_fixed_datapoint_tab.offset.value(),
            fixed_datapoints=self.__data_slicing_widget.slice_fixed_datapoint_tab.fixed_datapoint.value(),
            wavelength_conversion_methods=None,
            method1=self.__ui.inputRegulationStackedWidget.currentWidget()
            is self.__input_regulation_polynomial_tab,
            a_array=list(
                eval(self.__input_regulation_polynomial_tab.a_array_line_edit.text())
            ),
            x_array=list(
                eval(self.__input_regulation_polynomial_tab.x_array_line_edit.text())
            ),
            method2=self.__ui.inputRegulationStackedWidget.currentWidget()
            is self.__input_regulation_thermal_phase_shifter_tab,
            fsr=self.__input_regulation_thermal_phase_shifter_tab.fsr_double_spinbox.value()
            * 1e-9,
            p_fsr=self.__input_regulation_thermal_phase_shifter_tab.p_fsr_double_spinbox.value()
            * 1e-3,
            r_heater=self.__input_regulation_thermal_phase_shifter_tab.r_double_spinbox.value(),
            v_offset=self.__input_regulation_thermal_phase_shifter_tab.v_offset_double_spinbox.value(),
            thermal_response=None,
            thermal_method1=self.__ui.conversionMethodStackedWidget.currentWidget() 
            is self.__ZPGTF_tab,
            r_array=list(eval(self.__rctf_tab.rs_line_edit.text())),
            c_array=list(eval(self.__rctf_tab.cs_line_edit.text())),
            tau_array=list(),
            gain=self.__rctf_tab.gain_double_spinbox.value(),
            thermal_method2=self.__ui.conversionMethodStackedWidget.currentWidget() is 
            self.__ZPGTF_tab,
            z_array=list(eval(self.__ZPGTF_tab.zs_line_edit.text())),
            p_array=list(eval(self.__ZPGTF_tab.ps_line_edit.text())),
            zp_gain=float(0),
            thermal_method3=self.__ui.conversionMethodStackedWidget.currentWidget() is self.__NumDemonTF_tab,
            num_array=list(eval(self.__NumDemonTF_tab.num_line_edit.text())),
            denom_array=list(eval(self.__NumDemonTF_tab.denom_line_edit.text())),
        )

        csv_config.to_csv(csv_config_path)
        logger.info(f"RA-Active-Converter config csv file saved to {csv_config_path}")

        self.__ui.statusbar.clearMessage()
        self.__progress_bar.reset()
        self.__progress_bar.show()

        self.setEnabled(False)
        self.__convert_worker.start()

    def slot_on_conversion_done(self):
        logging.info(f"Conversion done. Passive data saved to output directory : {self.__ui.outputPathComboBox.currentText()}.")
        self.setEnabled(True)
        self.__ui.statusbar.clearMessage()
        self.__progress_bar.reset()
        self.__progress_bar.show()


    def slot_reject(self):
        self.close()

    # Progress bar slot
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
