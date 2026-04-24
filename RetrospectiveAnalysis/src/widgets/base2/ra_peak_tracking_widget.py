from itertools import cycle, islice
from functools import reduce, partial
from PySide6.QtCore import Qt, Signal
from ...core.utils.tqdm_qt import tqdm_qt
from typing import Optional
import numpy as np
from deprecated import deprecated
import pyqtgraph as pg
from pyqtgraph import exporters
import multiprocessing as mp
from typing import Any
import matplotlib.pyplot as plt
import os
from PIL import Image
from numpy.typing import NDArray
from pyqtgraph import ImageView, PlotItem
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import (
    QComboBox,
    QSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QSplitter,
    QMessageBox,
    QCheckBox,
)

from ...core.lib import (
    SweepFitResult,
    peaks_to_traces,
)
from ...core.passive_tools import (
    DataReaderBase,
    MatDataReader,
    NPZDataReader,
    _powers_to_sweep_fit_results,
    get_spectrogram,
)
from ...widgets.lib.ra_channel_selector import RaChannelSelector
from ...widgets.lib.ra_plot_curve_item import RaPlotCurveItem
from ...widgets.lib.utils.ra_qthread_worker import RaQThreadWorker
from .ra_peak_tracking_args_tab import RaPeakTrackingArgsTab, RaPeakTrackingArgsWidget
import logging
from ...core.lib import group_peaks
from scipy.io import savemat
import json
import time
import copy
from .ra_tracing_split_widget import PeakTracingSplitWidget

DEFAULT_RESULT_FILENAME = "ra_peaks.npz"
DEFAULT_SPECTROGRAM_FILENAME = "ra_spectrograms.npz"

NP_PEAK_KEY = "sweeps"
NP_SPECTROGRAM_KEY = "spectrograms"
NP_WAVELENGTH_KEY = "wavelength"

RESULT_FOLDER_DEFAULT_NAME = "RA_result"
PEAK_SHIFT_FILE_NAME = "peak_shift.mat"
PEAKS_FILE_NAME = "peaks.mat"
FSR_ER_Q_RESULT_FILE_NAME = "fsr_er_q.mat"


logger = logging.getLogger(__name__)


class PeakTrackingWidget(QWidget):
    save_weights = Signal()
    signal_resized = Signal()

    def __init__(self, qt_signal=None):
        super().__init__()
        self.initUI()

        self.peak_tracking_config.clicked.connect(self.show_settings)
        self.r2_threshold: list[float] = []
        self.n100dBm_tolerance: list[int] = []
        self.gaussian_filter = []
        self.prominence_scalar = []
        self.signal = qt_signal
        self.data_reader: DataReaderBase = None  # type: ignore
        self.time_unit: Optional[str] = None

        self.__peak_tracker_worker: Optional[RaQThreadWorker] = None
        self.__FSR_ER_Q_worker: Optional[RaQThreadWorker] = None

        self.setEnabled(False)

    def initUI(self):
        self.peak_tracking_layout = QVBoxLayout(self)
        self.setLayout(self.peak_tracking_layout)

        self.settings = Settings(self)
        self.buttons = Buttons(self)
        self.channelSelector = RaChannelSelector(self)
        self.peak_tracking_config = QPushButton("Peak Tracking Settings")
        self.peak_tracking_settings = RaPeakTrackingArgsWidget()
        self.peak_tracking_settings.setWindowTitle("Peak Tracking Settings")
        self.peak_tracking_display: PeakTrackingDisplayWidget = None  # type: ignore

        self.peak_tracking_config.setMaximumHeight(100)
        self.settings.setMaximumHeight(100)
        self.buttons.setMaximumHeight(150)
        self.channelSelector.setMaximumHeight(100)

        self.peak_tracking_layout.addWidget(self.settings)
        self.peak_tracking_layout.addWidget(self.peak_tracking_config)
        self.peak_tracking_layout.addWidget(self.buttons)
        self.peak_tracking_layout.addWidget(self.channelSelector)

        self.empty_widget = QWidget()
        self.peak_tracking_layout.addWidget(self.empty_widget)
        self.peak_tracking_layout.setStretch(4, 2)

        self.settings.pathBox.currentIndexChanged.connect(self.slot_update_path)

    @property
    def path(self):
        return self.settings.pathBox.currentText()

    @property
    def wavelength(self):
        return self.data_reader[0][1] * 1e9

    @property
    def timestamps(self):
        return self.data_reader.timestamps  # type: ignore
    
    def slot_update_path(self):
        if self.peak_tracking_display:
            self.peak_tracking_display.path = self.settings.pathBox.currentText()

    def show_settings(self):
        self.peak_tracking_settings.show()
        self.peak_tracking_settings.activateWindow()

    def restart_workers(self):
        self.__peak_tracker_worker = None
        self.__FSR_ER_Q_worker = None

    def update_values(self, file_num, path, powers):
        # update peak tracker output path combo box
        self.settings.pathBox.addItem(path)
        self.settings.pathBox.setCurrentText(path)

        self.settings.startBox.setMinimum(1)
        self.settings.startBox.setMaximum(file_num)
        self.settings.startBox.setValue(1)
        self.settings.endBox.setMinimum(1)
        self.settings.endBox.setMaximum(file_num)
        self.settings.endBox.setValue(file_num)
        self.channelSelector.selections = [True] * powers

    def peak_fit_all(self):
        channel_selections = {
            i for i, b in enumerate(self.channelSelector.selections) if b
        }
        (start, stop, step) = self.settings.start_stop_step

        sweep_fit_results: dict[int, list[SweepFitResult]] = {
            k: [] for k in channel_selections
        }

        with mp.Pool() as pool:
            sweep_fit_results: dict[int, list[SweepFitResult]] = reduce(
                lambda acc, b: {
                    x: acc.get(x, []) + b.get(x, []) for x in set(acc).union(b)  # type: ignore
                },
                    pool.starmap(
                        partial(
                            _powers_to_sweep_fit_results,
                            prom_scalar=self.prominence_scalar,
                            gaussian_filter=self.gaussian_filter,
                            channels=channel_selections,
                        ),
                        tqdm_qt(
                            map(
                                lambda x: (x[2], x[1]*1e9), 
                                islice(
                                    self.data_reader, 
                                    int(start), 
                                    int(stop), 
                                    int(step)
                                        )
                            ),
                            total=(stop - start) // step,
                            qt_signal=self.signal,
                            ),
                        ),
                    {},
                )

        return sweep_fit_results

    @deprecated(
            reason="Old peak_fit_all function that use only the wavelength of the first sweep", 
            action="always"
    )
    def peak_fit_all_old(self):
        channel_selections = {
            i for i, b in enumerate(self.channelSelector.selections) if b
        }
        (start, stop, step) = self.settings.start_stop_step

        sweep_fit_results: dict[int, list[SweepFitResult]] = {
            k: [] for k in channel_selections
        }

        with mp.Pool() as pool:
            sweep_fit_results: dict[int, list[SweepFitResult]] = reduce(
                lambda acc, b: {
                    x: acc.get(x, []) + b.get(x, []) for x in set(acc).union(b)  # type: ignore
                },
                tqdm_qt(
                    pool.imap(
                        partial(
                            _powers_to_sweep_fit_results,
                            wavelengths=self.wavelength,
                            channels=channel_selections,
                        ),
                        islice(
                            self.data_reader.sweep_only(),
                            int(start),
                            int(stop),
                            int(step),
                        ),
                    ),
                    total=(stop - start) // step,
                    qt_signal=self.signal,
                ),
                {},
            )

        return sweep_fit_results

    def peak_track_all(
        self, sweep_fit: dict[int, list[SweepFitResult]], spectrograms_dict=None
    ):
        shift_between_sweep = self.peak_tracking_settings.fsr_args_settings.percentage_fsr
        traces_num = self.peak_tracking_settings.fsr_args_settings.traces_num

        current_widget = (
            self.peak_tracking_settings.algo_args.peakTrackingStackedWidget.currentWidget()
        )
        widget: RaPeakTrackingArgsTab = current_widget  # type: ignore

        distance_func_dict = {
            i: widget.tabs[i].to_distance_func() for i in sweep_fit.keys()
        }

        (start, stop, step) = self.settings.start_stop_step

        spectrograms_dict = get_spectrogram(
            self.data_reader, set(sweep_fit.keys()), start, stop, step
        )

        peaks_dict: dict[int, list[NDArray]] = {
            k: [
                s.get_peaks(
                    r2_threshold=self.r2_threshold[k],
                    n100dbm_threshold=self.n100dBm_tolerance[k],
                )
                for s in v
            ]
            for k, v in sweep_fit.items()
        }

        for k, v in peaks_dict.items():
            if v[0].shape[0] == 0:
                raise RuntimeError(
                    f"The first sweep in channel {k+1} has no peaks detected. Consider adjusting the R2 threshold, -100dBm threshold or skipping this sweep."
                )
        
        traces_fsr_dict = {
            k: peaks_to_traces(
                v,
                distance_func_dict[k],
                shift_betweep_sweeps=shift_between_sweep,
                traces_threshold=traces_num,
            )
            for k, v in peaks_dict.items()
        }

        return spectrograms_dict, sweep_fit, traces_fsr_dict, peaks_dict

    def sweep_fit_peak_track(self):
        sweep_fit_results = self.peak_fit_all()
        spectrograms_dict, _, traces_fsr_dict, peaks_dict = self.peak_track_all(
            sweep_fit_results
        )

        return spectrograms_dict, sweep_fit_results, traces_fsr_dict, peaks_dict

    def slot_clicked_peak_track_and_fit(self):
        logger.info("Starting Peak Fitting and Tracking...")
        self.__peak_tracker_worker = RaQThreadWorker(self.sweep_fit_peak_track)  # type: ignore
        self.__peak_tracker_worker.finished.connect(self.slot_peak_track_finished)
        self.__peak_tracker_worker.start()

    def slot_clicked_peak_track(self):
        self.buttons.startTrack.setEnabled(True)

        if isinstance(self.data_reader, MatDataReader):
            if self.__peak_tracker_worker:
                _, sweep_fit_result, _, _ = self.__peak_tracker_worker.result  # type: ignore
                self.__peak_tracker_worker = RaQThreadWorker(self.peak_track_all, sweep_fit_result)  # type: ignore
                self.__peak_tracker_worker.finished.connect(
                    self.slot_peak_track_finished
                )
                self.__peak_tracker_worker.start()

            else:
                raise ValueError("Peak Fitting has not been done yet!")

        elif isinstance(self.data_reader, NPZDataReader):
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Select")
            msgBox.setText(
                "Do you want to load .npz peak fitted file or previous peak fit result?"
            )
            prev_peak_fit = msgBox.addButton(
                "Use Previous Peak Fit", QMessageBox.ActionRole # type: ignore
            )
            npz_peak_fit = msgBox.addButton("Load in Peak Fit (.npz file)", QMessageBox.ActionRole) # type: ignore
            # Add standard buttons
            msgBox.setStandardButtons(QMessageBox.Cancel) # type: ignore

            msgBox.exec_()

            if msgBox.clickedButton() == npz_peak_fit:
                sweep_fit_result = self.data_reader.sweep_2d
                self.__peak_tracker_worker = RaQThreadWorker(self.peak_track_all, sweep_fit_result)  # type: ignore
                self.__peak_tracker_worker.finished.connect(self.slot_peak_track_finished)
                self.__peak_tracker_worker.start()

            elif msgBox.clickedButton() == prev_peak_fit:
                if self.__peak_tracker_worker:
                    _, sweep_fit_result, _, _ = self.__peak_tracker_worker.result  # type: ignore
                    self.__peak_tracker_worker = RaQThreadWorker(self.peak_track_all, sweep_fit_result)  # type: ignore
                    self.__peak_tracker_worker.finished.connect(
                        self.slot_peak_track_finished
                    )
                    self.__peak_tracker_worker.start()
                else:
                    raise ValueError("Peak Fitting has not been done yet!")

        else:
            return

    def slot_peak_track_finished(self):
        if self.__peak_tracker_worker.error:
            self.buttons.toggle_buttons(True)
            raise RuntimeError(self.__peak_tracker_worker.error)

        else:
            spectrograms, _, traces_fsr_dict, _ = self.__peak_tracker_worker.result  # type: ignore

        logger.info("Peak Fitting Completed! Generating spectrograms and traces...")

        if self.peak_tracking_display:
            self.peak_tracking_layout.removeWidget(self.peak_tracking_display)
            self.peak_tracking_display.deleteLater()
            self.peak_tracking_display = None  # type: ignore

        else:
            self.peak_tracking_layout.removeWidget(self.empty_widget)

        self.peak_tracking_display = PeakTrackingDisplayWidget(
            spectrograms,
            self.wavelength,
            self.timestamps,
            traces_fsr_dict,
            self.settings.start_stop_step,
            time_unit=self.time_unit,
            power_unit="dBm",
            path=self.path,
        )

        self.peak_tracking_display.spectrogram_tab.clear()

        self.layout().addWidget(self.peak_tracking_display)

        for k, spectrogram in spectrograms.items():
            plot = PlotItem()
            image = ImageView(view=plot)
            image.ui.roiBtn.hide()
            image.ui.menuBtn.hide()
            image.getView().invertY(False)
            image.getView().setAspectLocked(False)
            image.setColorMap(pg.colormap.getFromMatplotlib("inferno"))

            # plot spectrogram background
            image.setImage(np.array(spectrogram), autoRange=True)
            plot.setTitle(f"Power {k+1} Peak Shift")
            plot.setLabel("left", "Wavelength (nm)")
            plot.setLabel("bottom", "Sweep Number")

            # TODO: transform image to fit x-y axis
            tr = QTransform()
            tr.translate(
                -0.5,
                -0.5 * max(np.diff(self.wavelength)) + float(np.min(self.wavelength)),
            )
            tr.scale(
                1,
                (float(np.max(self.wavelength)) - float(np.min(self.wavelength)))
                / len(self.wavelength),
            )

            image.getImageItem().setTransform(tr)
            traces, fsr = traces_fsr_dict[k]

            color_palette = cycle(["light green", "blue"])
            x0 = 0

            for trace in traces:
                xs = np.arange(x0, x0 + len(trace))
                plot.addItem(
                    RaPlotCurveItem(
                        fsr, x=xs, y=trace, pen=pg.mkPen(next(color_palette), width=3)
                    )
                )
                x0 += len(trace)

            self.peak_tracking_display.spectrogram_tab.addTab(image, f"{'Power'} {k+1}")
            image.autoRange()

        self.signal_resized.emit()
        logger.info("Successfully generated spectrograms and traces!")
        self.buttons.toggle_buttons(True)

        return

    def autoRange_all(self):
        if self.peak_tracking_display:
            for i in range(self.peak_tracking_display.spectrogram_tab.count()):
                self.peak_tracking_display.spectrogram_tab.setCurrentIndex(i)
                self.peak_tracking_display.spectrogram_tab.widget(
                    i
                ).getView().autoRange()

    def slot_clicked_FSR_ER_Q(self):
        self.buttons.getValues.setEnabled(False)

        try:
            if self.__peak_tracker_worker:
                msgBox = QMessageBox()
                msgBox.setWindowTitle("Select")
                msgBox.setText(
                    "Do you want to use the previous peak fit result? or rerun peak fitting with different data channels and/or parameters?"
                )

                prev_peak_fit = msgBox.addButton(
                    "Use Previous Peak Fit", QMessageBox.ActionRole #type: ignore
                )
                new_peak_fit = msgBox.addButton("New Peak Fit", QMessageBox.ActionRole) #type: ignore
                # Add standard buttons
                msgBox.setStandardButtons(QMessageBox.Cancel) #type: ignore

                msgBox.exec_()

                if msgBox.clickedButton() == prev_peak_fit:
                    try:
                        _, sweep_fit_result, _, _ = self.__peak_tracker_worker.result  # type: ignore
                        self.slot_FSR_ER_Q_finished(sweep_fit_result)

                    except Exception:
                        raise ValueError(
                            "Peak Fitting has not been done yet! Select new peak fit."
                        )

                elif msgBox.clickedButton() == new_peak_fit:
                    self.__FSR_ER_Q_worker = RaQThreadWorker(self.peak_fit_all)
                    self.__FSR_ER_Q_worker.finished.connect(self.slot_FSR_ER_Q_finished)
                    self.__FSR_ER_Q_worker.start()

                else:
                    msgBox.close()
                    return

            else:
                self.__FSR_ER_Q_worker = RaQThreadWorker(self.peak_fit_all)
                self.__FSR_ER_Q_worker.finished.connect(self.slot_FSR_ER_Q_finished)
                self.__FSR_ER_Q_worker.start()

        finally:
            self.buttons.getValues.setEnabled(True)

    def slot_FSR_ER_Q_finished(self, sweep_fit_result: dict[int, list[SweepFitResult]] = None):  # type: ignore
        self.buttons.getValues.setEnabled(False)

        output_path = os.path.join(
            self.path,
            RESULT_FOLDER_DEFAULT_NAME,
        )

        os.makedirs(output_path, exist_ok=True)

        output_path = os.path.join(output_path, FSR_ER_Q_RESULT_FILE_NAME)

        if sweep_fit_result is None:
            if self.__FSR_ER_Q_worker.error:  # type: ignore
                raise RuntimeError(self.__FSR_ER_Q_worker.error)  # type: ignore

            else:
                sweep_fit_result = self.__FSR_ER_Q_worker.result  # type: ignore

        fsr_er_q_dict = {
            k: [
                (
                    s.get_fsr(self.r2_threshold[k], self.n100dBm_tolerance[k]),
                    s.get_er(self.r2_threshold[k], self.n100dBm_tolerance[k]),
                    s.get_q(self.r2_threshold[k], self.n100dBm_tolerance[k]),
                    s.get_r2(self.r2_threshold[k], self.n100dBm_tolerance[k]), #ADDED, MAQ
                    s.get_lambda0(self.r2_threshold[k], self.n100dBm_tolerance[k]), #ADDED, MAQ
                    s.get_fwhm(self.r2_threshold[k], self.n100dBm_tolerance[k]), #ADDED, MAQ
                )
                for s in v
            ]
            for k, v in sweep_fit_result.items()
        }

        try:
            fsr = {k: [np.array(vv[0]) for vv in v] for k, v in fsr_er_q_dict.items()}
            er = {k: [np.array(vv[1]) for vv in v] for k, v in fsr_er_q_dict.items()}
            q = {k: [np.array(vv[2]) for vv in v] for k, v in fsr_er_q_dict.items()}
            r2 = {k: [np.array(vv[3]) for vv in v] for k, v in fsr_er_q_dict.items()}#ADDED, MAQ
            lambda0 = {k: [np.array(vv[4]) for vv in v] for k, v in fsr_er_q_dict.items()}#ADDED, MAQ
            fwhm = {k: [np.array(vv[5]) for vv in v] for k, v in fsr_er_q_dict.items()}#ADDED, MAQ

            savemat(
                output_path,
                {
                    f"channel{k+1}_fsr": np.array(v, dtype="object")
                    for k, v in fsr.items()
                }
                | {
                    f"channel{k+1}_er": np.array(v, dtype="object")
                    for k, v in er.items()
                }
                | {f"channel{k+1}_q": np.array(v, dtype="object") for k, v in q.items()}
                | {f"channel{k+1}_r2": np.array(v, dtype="object") for k, v in r2.items()}
                | {f"channel{k+1}_lambda0": np.array(v, dtype="object") for k, v in lambda0.items()}
                | {f"channel{k+1}_fwhm": np.array(v, dtype="object") for k, v in fwhm.items()}
                | {
                    "t_array": self.timestamps[
                        self.settings.start_stop_step[
                            0
                        ] : self.settings.start_stop_step[
                            1
                        ] : self.settings.start_stop_step[
                            2
                        ]
                    ]
                },
            )

        except Exception as e:
            logger.error(e.with_traceback(None))

        finally:
            self.buttons.getValues.setEnabled(True)
            logger.info("FSR ER Q analysis done!")

    def slot_clicked_save_peak_fit(self):
        spectrogram, sweep_fit_result, _, _ = self.__peak_tracker_worker.result  # type: ignore

        output_path = os.path.join(self.path, DEFAULT_RESULT_FILENAME)

        np.savez_compressed(
            output_path,
            sweeps=np.array(list(sweep_fit_result.values())),
        )

        output_path = os.path.join(self.path, DEFAULT_SPECTROGRAM_FILENAME)

        np.savez_compressed(
            output_path,
            spectrograms=np.array(list(spectrogram.values())),
            wavelength=self.wavelength,
        )

        logger.info("Peak Fitting Successfully Saved at {} ".format(self.path))

    def slot_clicked_save_results(self):
        output_path = os.path.join(self.path, RESULT_FOLDER_DEFAULT_NAME)
        os.makedirs(output_path, exist_ok=True)

        peak_shift_path = os.path.join(output_path, PEAK_SHIFT_FILE_NAME)
        peaks_path = os.path.join(output_path, PEAKS_FILE_NAME)

        _, _, _, peaks_dict = self.__peak_tracker_worker.result  # type: ignore

        tabs = self.peak_tracking_display.spectrogram_tab.count()
        self.peak_tracking_display.spectrogram_tab.setCurrentIndex(0)

        all_names = []
        all_traces: list[NDArray] = []
        all_channels = []

        for i in range(tabs):
            self.peak_tracking_display.spectrogram_tab.setCurrentIndex(i)
            all_names.append(
                self.peak_tracking_display.name.replace(" ", "_").lower()
                + "_peakWL_list"
            )
            all_traces.append(self.peak_tracking_display.full_trace)
            all_channels.append(self.peak_tracking_display.channel - 1)

        savemat(
            peak_shift_path,
            {all_names[i]: all_traces[i] for i in range(tabs)}
            | {
                "t_array": self.timestamps[
                    self.settings.start_stop_step[0] : self.settings.start_stop_step[
                        1
                    ] : self.settings.start_stop_step[2]
                ]
            },
        )

        # save all fitted peaks and peak trace indices
        savemat(
            peaks_path,
            {
                "channel" + str(k + 1): np.array(v, dtype="object")
                for k, v in peaks_dict.items()
            }
            | {
                "t_array": self.timestamps[
                    self.settings.start_stop_step[0] : self.settings.start_stop_step[
                        1
                    ] : self.settings.start_stop_step[2]
                ]
            }
            | {
                "channel"
                + str(all_channels[i] + 1)
                + "_peak_trace_indices": np.array(
                    group_peaks(
                        [[p[0] for p in ps] for ps in peaks_dict[all_channels[i]]],  # type: ignore
                        all_traces[i],
                    ),
                    dtype="object",
                )
                for i in range(tabs)
            },
        )

        self.save_configurations()

        plt.close("all")
        axes = plt.axes()
        for i in range(tabs):
            axes.plot(
                self.timestamps[
                    self.settings.start_stop_step[0] : self.settings.start_stop_step[
                        1
                    ] : self.settings.start_stop_step[2]
                ],
                all_traces[i] - all_traces[i][0],
                label=f"Power {all_channels[i]+1}",
            )

        axes.set_title("Collated Overlaid Peak Shifts")
        axes.set_xlabel(f"Time ({self.time_unit})")
        axes.set_ylabel("Resonance Peak Shift (nm)")
        plt.gcf().set_size_inches(8, 5)
        axes.axis("auto")
        axes.legend()
        plt.show()
        plt.savefig("Collated Overlaid Peak Shifts.png")

    def save_configurations(self):
        peak_tracking_config = self.peak_tracking_settings.algo_args.export_weights()

        json_dump = {}
        json_dump["peak tracking settings"] = {}
        json_dump["peak fitting settings"] = {}
        json_dump["peak tracking settings"]["algorithm"] = peak_tracking_config[
            "algorithm"
        ]

        for i in range(len(self.channelSelector.selections)):
            json_dump["peak fitting settings"][f"{i+1}"] = {}
            json_dump["peak fitting settings"][f"{i+1}"][
                "r2 threshold"
            ] = self.r2_threshold[i]
            json_dump["peak fitting settings"][f"{i+1}"][
                "n100dBm tolerance"
            ] = self.n100dBm_tolerance[i]
            json_dump["peak fitting settings"][f"{i+1}"][
                "gaussian filter"
            ] = self.gaussian_filter[i]
            json_dump["peak fitting settings"][f"{i+1}"][
                "prominence scalar"
            ] = self.prominence_scalar[i]

            json_dump["peak tracking settings"][f"{i+1}"] = {}
            json_dump["peak tracking settings"][f"{i+1}"][
                "weights"
            ] = peak_tracking_config["peak tracking weights"][i]

        with open(
            os.path.join(self.path, "Retrospective Analysis Config.json"), "w"
        ) as f:
            json.dump(json_dump, f, indent=4)

class PeakTrackingDisplayWidget(QWidget):
    def __init__(
        self,
        spectrograms: dict[int, NDArray[np.floating]],
        wavelength: NDArray[np.floating],
        timestamp: NDArray[np.floating],
        traces: dict[int, tuple[list[list[Any]], float]],
        start_stop_step: tuple[int, Optional[int], int],
        time_unit: Optional[str],
        power_unit: str,
        path: str,
    ):
        super().__init__()
        self.__wavelength = wavelength
        self.__timestamps = timestamp
        self.__spectrograms = spectrograms
        self.__traces: dict[int, tuple[list[list[Any]], float]] = traces  # type: ignore
        self.__start_stop_step = start_stop_step
        self.__time_unit = time_unit
        self.path = path
        self.__original_traces = copy.deepcopy(traces)

        self.split_trace_widget = PeakTracingSplitWidget()
        self.__split_trace_button = QGroupBox()
        self.__show_split_button = QPushButton("Split Sweep")
        self.__split_trace_button.setLayout(layout0 := QHBoxLayout())
        layout0.addWidget(self.__show_split_button)

        self.__display_buttons = QGroupBox()
        self.autoSaveCheck = QCheckBox("auto-save")
        self.offsetAndSpectrogramButton = QPushButton("Offset+Spectrogram")
        self.peakOffsetButton = QPushButton("Peak Offset")
        self.overlayButton = QPushButton("Overlay")

        self.__display_buttons.setLayout(layout1 := QHBoxLayout())
        self.__spectrogram_tab = QTabWidget()

        layout1.addWidget(self.autoSaveCheck)
        layout1.addWidget(self.offsetAndSpectrogramButton)
        layout1.addWidget(self.peakOffsetButton)
        layout1.addWidget(self.overlayButton)

        self.setLayout(main_layout:=QVBoxLayout())
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(self.__split_trace_button)
        settings_layout.addWidget(self.__display_buttons)

        main_layout.addLayout(settings_layout)
        main_layout.addWidget(self.spectrogram_tab)

        self.split_trace_widget.add_sweep_button.clicked.connect(self.__slot_split_trace)
        self.split_trace_widget.reset_button.clicked.connect(self.__slot_split_trace_reset)
        self.__show_split_button.clicked.connect(self.__slot_split_show)
        self.offsetAndSpectrogramButton.clicked.connect(self.__slot_offset_spectrogram)
        self.peakOffsetButton.clicked.connect(self.__slot_peak_offset)
        self.overlayButton.clicked.connect(self.__slot_overlay)

    @property
    def spectrogram_tab(self):
        return self.__spectrogram_tab

    @property
    def display_buttons(self):
        return self.__display_buttons

    @property
    def channel(self):  # return current channel
        return int(
            self.spectrogram_tab.tabText(self.spectrogram_tab.currentIndex()).split(
                " "
            )[1]
        )

    @property
    def name(self):
        return self.spectrogram_tab.tabText(self.spectrogram_tab.currentIndex())

    @property
    def trace(self):
        return self.__traces[self.channel - 1][0]

    @property
    def spectrogram(self):
        return self.__spectrograms[self.channel - 1]

    @property
    def full_trace(self):
        ret = np.array([np.NAN] * sum(map(len, self.trace)))
        image_item: ImageView = self.spectrogram_tab.currentWidget()  # type: ignore
        plot_item: PlotItem = image_item.view

        for item in plot_item.listDataItems():
            xs, ys = item.getData()
            for i, x in enumerate(xs):
                ret[int(np.round(x))] = ys[i]

        return ret
    
    def split_trace(self, index: int):
        outer_index, inner_index = self.get_split_info(index) # type: ignore

        if outer_index is None or inner_index is None:
            return
        
        else:
            trace = self.__traces[self.channel - 1][0][outer_index]
            
            new_trace_one = trace[:inner_index]
            new_trace_two = trace[inner_index:]

            self.__traces[self.channel - 1][0][outer_index] = new_trace_one
            self.__traces[self.channel - 1][0].insert(outer_index + 1, new_trace_two)
            self.replot_traces()

    def get_split_info(self, index: int):
        sweep_num = 0

        try:
            for outer_index, trace in enumerate(self.__traces[self.channel - 1][0]):
                for inner_index, _ in enumerate(trace):
                    sweep_num += 1
                    if sweep_num == index:
                        if inner_index == 0 or inner_index == len(trace) - 1:
                            logging.info('Cannot split at the beginning or end of a trace')
                            return None, None
                        
                        return outer_index, inner_index + 1
                    
        except Exception as e:    
            logging.warning("Cannot split trace: " + str(e))
            return None, None
    
    def replot_traces(self):
        color_palette = cycle(["light green", "blue"])

        image_item: ImageView = self.spectrogram_tab.currentWidget()  # type: ignore
        plot_item: PlotItem = image_item.view
        
        for curve in plot_item.listDataItems():
            plot_item.removeItem(curve)

        fsr : float = self.__traces[self.channel - 1][1] # type: ignore

        x0 = 0
        for trace in self.__traces[self.channel - 1][0]:
            xs = np.arange(x0, x0 + len(trace))
            plot_item.addItem(
                RaPlotCurveItem(
                    fsr, x=xs, y=trace, pen=pg.mkPen(next(color_palette), width=3)
                )
            )
            x0 += len(trace)

    def create_trace(self):
        ys = self.full_trace
        # x0 = 0
        # trace_ax = pg.PlotCurveItem(np.arange(x0, x0 + len(ys)), ys, pen=pg.mkPen('b', width=5), connect='finite')
        trace_ax = pg.PlotCurveItem(
            self.__timestamps[
                self.__start_stop_step[0] : self.__start_stop_step[
                    1
                ] : self.__start_stop_step[2]
            ],
            ys,
            pen=pg.mkPen("b", width=3),
            connect="finite",
        )

        return trace_ax

    def create_spectrogram(self):
        spectrogram_plot_item = PlotItem()
        spectrogram = ImageView(view=spectrogram_plot_item)
        spectrogram.ui.roiBtn.hide()
        spectrogram.ui.menuBtn.hide()
        spectrogram.getView().invertY(False)
        spectrogram.getView().setAspectLocked(False)
        spectrogram.setColorMap(pg.colormap.getFromMatplotlib("inferno"))
        spectrogram.setImage(np.array(self.spectrogram))

        tr = QTransform()
        tr.translate(
            -0.5,
            -0.5 * max(np.diff(self.__wavelength)) + float(np.min(self.__wavelength)),
        )
        tr.scale(
            1,
            (float(np.max(self.__wavelength)) - float(np.min(self.__wavelength)))
            / len(self.__wavelength),
        )

        # get x ticks
        x_label = self.__timestamps[
            self.__start_stop_step[0] : self.__start_stop_step[
                1
            ] : self.__start_stop_step[2]
        ].tolist()

        ax = spectrogram.view.getAxis("bottom")

        self.xTicks = [
            (0, format(x_label[0], ".2f")),
            (len(x_label), format(x_label[-1], ".2f")),
        ]
        ax.setTicks([self.xTicks])

        spectrogram.getImageItem().setTransform(tr)

        return spectrogram

    def __slot_offset_spectrogram(self):
        self.pop_up = QWidget()
        self.pop_up.setWindowTitle("Peak Offset and Spectrogram Plot")
        self.pop_up.setMinimumSize(800, 600)
        self.pop_up.setLayout(QVBoxLayout())
        self.pop_up.layout().addWidget(splitter := QSplitter(Qt.Orientation.Vertical))

        plot_widget = pg.PlotWidget()
        plot_widget.addItem(self.create_trace())
        plot_widget.setMinimumHeight(300)
        plot_widget.setLabel("bottom", f"Time ({self.__time_unit})")
        plot_widget.setLabel("left", "Wavelength (nm)")
        plot_widget.setTitle(f"{self.name} Offset")

        spectrogram = self.create_spectrogram()

        spectrogram.view.setTitle(f"{self.name} Spectrogram")
        plot_widget.setLabel("bottom", f"Time ({self.__time_unit})")
        spectrogram.view.setLabel("left", "Wavelength (nm)")
        spectrogram.view.setLabel("bottom", f"Time ({self.__time_unit})")

        splitter.addWidget(plot_widget)
        splitter.addWidget(spectrogram)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.pop_up.show()
        spectrogram.getView().autoRange()

        if self.autoSaveCheck.isChecked():
            os.makedirs(self.path, exist_ok=True)
            exporter = exporters.ImageExporter(spectrogram.view)
            spectrogram_title = (
                self.name.replace(" ", "_").lower() + "_spectrogram" + ".png"
            )
            spectrogram_title = os.path.join(self.path, spectrogram_title)
            exporter.export(spectrogram_title)
            
            exporter_svg = exporters.SVGExporter(spectrogram.view)
            spectrogram_title_svg = (
                self.name.replace(" ", "_").lower() + "_spectrogram_svg" + ".svg"
            )
            spectrogram_title_svg = os.path.join(self.path, spectrogram_title_svg)
            exporter_svg.export(spectrogram_title_svg)

            # save offset plot
            plot = exporters.ImageExporter(plot_widget.plotItem)
            plot_title = self.name.replace(" ", "_").lower() + "_offset" + ".png"
            plot_title = os.path.join(self.path, plot_title)
            plot.export(plot_title)
            
            exporter_svg = exporters.SVGExporter(plot_widget.plotItem)
            plot_title_svg = self.name.replace(" ", "_").lower() + "_offset_svg" + ".svg"
            plot_title_svg = os.path.join(self.path, plot_title_svg)
            exporter_svg.export(plot_title_svg)
            
            image1 = Image.open(spectrogram_title)
            image2 = Image.open(plot_title)
            image2 = image2.resize(image1.size)

            combined_height = image1.height + image2.height
            combined_image = Image.new("RGB", (image1.width, combined_height))
            combined_image.paste(image1, (0, 0))
            combined_image.paste(image2, (0, image1.height))
            title = self.name.replace(" ", "_").lower() + "_offset_spectrogram" + ".png"
            title = os.path.join(self.path, title)
            combined_image.save(title)

    def __slot_peak_offset(self):
        self.pop_up = QWidget()
        self.pop_up.setWindowTitle("Peak Offset Plot")
        self.pop_up.setMinimumSize(800, 600)
        self.pop_up.setLayout(QVBoxLayout())
        self.pop_up.layout().addWidget(splitter := QSplitter(Qt.Orientation.Vertical))

        plot_widget = pg.PlotWidget()
        plot_widget.addItem(self.create_trace())
        plot_widget.setLabel("bottom", f"Time ({self.__time_unit})")
        plot_widget.setLabel("left", "Wavelength (nm)")
        plot_widget.setTitle(f"{self.name} Peak Offset")

        splitter.addWidget(plot_widget)

        if self.autoSaveCheck.isChecked():
            os.makedirs(self.path, exist_ok=True)
            exporter = exporters.ImageExporter(plot_widget.plotItem)
            title = self.name.replace(" ", "_").lower() + "_peak_offset" + ".png"
            title = os.path.join(self.path, title)
            exporter.export(title)

            exporter_svg = exporters.SVGExporter(plot_widget.plotItem)
            title_svg = self.name.replace(" ", "_").lower() + "_peak_offset_svg" + ".svg"
            title_svg = os.path.join(self.path, title_svg)
            exporter_svg.export(title_svg)

        self.pop_up.show()

    def __slot_overlay(self):
        self.pop_up = QWidget()
        self.pop_up.setWindowTitle("Overlay Plot")
        self.pop_up.setMinimumSize(800, 600)
        self.pop_up.setLayout(QVBoxLayout())
        self.pop_up.layout().addWidget(splitter := QSplitter(Qt.Orientation.Vertical))

        spectrogram = self.create_spectrogram()

        ys = self.full_trace
        # ys -= ys[0]
        # ys -= min(self.__wavelength * 1e-9)
        # ys /= max(self.__wavelength * 1e-9) - min(self.__wavelength * 1e-9)
        # ys *= len(self.__wavelength * 1e-9)

        x0 = 0
        trace_ax = pg.PlotCurveItem(
            np.arange(x0, x0 + len(ys)),
            ys,
            pen=pg.mkPen("b", width=3),
            connect="finite",
        )

        spectrogram.view.addItem(trace_ax)
        spectrogram.view.setTitle(f"{self.name} Overlay")
        spectrogram.view.setLabel("left", "Wavelength (nm)")
        spectrogram.view.setLabel("bottom", f"Time ({self.__time_unit})")

        splitter.addWidget(spectrogram)
        self.pop_up.show()
        spectrogram.autoRange()

        if self.autoSaveCheck.isChecked():
            os.makedirs(self.path, exist_ok=True)
            exporter = exporters.ImageExporter(spectrogram.view)
            title = self.name.replace(" ", "_").lower() + "_overlay" + ".png"
            title = os.path.join(self.path, title)
            exporter.export(title)
            
            title_svg = self.name.replace(" ", "_").lower() + "_overlay_svg" + ".svg"
            title_svg = os.path.join(self.path, title_svg)
            exporter_svg = exporters.SVGExporter(spectrogram.view)
            exporter_svg.export(title_svg)
    
    def __slot_split_trace(self):
        sweep_num = self.split_trace_widget.sweep
        self.split_trace(sweep_num)

        return
    
    def __slot_split_trace_reset(self):
        # derefernce original trace values and replot
        self.__traces[self.channel - 1] = copy.deepcopy(self.__original_traces[self.channel - 1])
        self.replot_traces()

        return
    
    def __slot_split_show(self):
        self.split_trace_widget.show()
        return

class Settings(QGroupBox):
    def __init__(self, parent: QWidget):
        super(Settings, self).__init__(parent=parent)
        self.initUI()

        self.selectButton.clicked.connect(self.select_path)
        self.startBox.valueChanged.connect(self.validateMinMax)
        self.endBox.valueChanged.connect(self.validateMinMax)

    def initUI(self):
        self.setTitle("Settings")
        self.layout0 = QHBoxLayout()
        self.setLayout(self.layout0)

        self.label1 = QLabel("Output Path: ")
        self.pathBox = QComboBox()
        self.selectButton = QPushButton("Select...")

        self.label2 = QLabel("From: ")
        self.startBox = QSpinBox(value=1)  # type: ignore
        self.label3 = QLabel("To: ")
        self.endBox = QSpinBox(value=2)  # type: ignore
        self.label4 = QLabel("Step: ")
        self.stepBox = QSpinBox(value=1)  # type: ignore

        self.layout0.addWidget(self.label1)
        self.layout0.addWidget(self.pathBox)
        self.layout0.addWidget(self.selectButton)
        self.layout0.addWidget(self.label2)
        self.layout0.addWidget(self.startBox)
        self.layout0.addWidget(self.label3)
        self.layout0.addWidget(self.endBox)
        self.layout0.addWidget(self.label4)
        self.layout0.addWidget(self.stepBox)

    @property
    def start_stop_step(self):
        return self.startBox.value() - 1, self.endBox.value(), self.stepBox.value()

    def validateMinMax(self):
        min_value = self.startBox.value()
        max_value = self.endBox.value()

        if min_value >= max_value:
            self.startBox.setValue(max_value - 1)

    def select_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.pathBox.addItem(path)
        self.pathBox.setCurrentText(path)


class Buttons(QWidget):
    def __init__(self, parent: QWidget):
        super(Buttons, self).__init__(parent=parent)

        self.layout0 = QHBoxLayout()
        self.setLayout(self.layout0)

        self.savePeakFit = QPushButton("Save Peak Fitting")
        self.saveButton = QPushButton("Save Results")
        self.getValues = QPushButton("Get FSR, ER, Q")
        self.startTrack = QPushButton("Start Track Only")
        self.startFitAndTrack = QPushButton("Start Fitting and Track")

        self.layout1 = QVBoxLayout()
        self.layout1.addWidget(self.startFitAndTrack)
        self.layout1.addWidget(self.startTrack)

        self.layout2 = QVBoxLayout()
        self.layout2.addWidget(self.savePeakFit)
        self.layout2.addWidget(self.saveButton)

        self.layout0.addLayout(self.layout1)
        self.layout0.addWidget(self.getValues)
        self.layout0.addLayout(self.layout2)

    def toggle_buttons(self, state=False):
        self.savePeakFit.setEnabled(state)
        self.saveButton.setEnabled(state)
        self.getValues.setEnabled(state)
        self.startTrack.setEnabled(state)
        self.startFitAndTrack.setEnabled(state)
