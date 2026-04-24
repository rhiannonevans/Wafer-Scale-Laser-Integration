import logging
from functools import partial
from itertools import islice

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from pyqtgraph import ImageView
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QFileDialog,
    QWidget,
)
import os
import pyqtgraph.exporters as exporters
from ...core.passive_tools import MatDataReader
from ...widgets.lib.ra_channel_selector import RaChannelSelector
from ...widgets.lib.utils.ra_qthread_worker import RaQThreadWorker


class PlotSpectrogramWidget(QGroupBox):
    def __init__(self, parent=None):
        super(PlotSpectrogramWidget, self).__init__(parent=parent)
        self.initUI()

        self.stop.valueChanged.connect(self.validateMinMax)
        self.start.valueChanged.connect(self.validateMinMax)
        self.setEnabled(False)

        self.image_window = QWidget()
        self.image_window.resize(1000, 1000)
        self.image_window_layout = QVBoxLayout()
        self.image_window.setLayout(self.image_window_layout)
        self.image_window.setWindowTitle("Spectrograms")
        self.image_tab = QTabWidget()
        self.save_all_button = QPushButton("Save All")
        self.image_window_layout.addWidget(self.image_tab)
        self.image_window_layout.addWidget(self.save_all_button)
        self.save_all_button.clicked.connect(self.slot_save_all)

        self.worker: RaQThreadWorker = None  # type: ignore

    @property
    def step_val(self):
        return self.step.value()

    @property
    def start_index(self):
        return self.start.value()

    @property
    def end_index(self):
        return self.stop.value()

    def initUI(self):
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # set layout
        self.spectrogramLayout = QVBoxLayout(self)
        self.channelSelector = RaChannelSelector()

        # group box style
        self.spectrogramStyle = QGroupBox("Style")
        self.xtick = QDoubleSpinBox(value=20)  # type: ignore
        self.ytick = QDoubleSpinBox(value=20)  # type: ignore
        self.y_decimal_points = QSpinBox(value=0)  # type: ignore
        self.powerUnit = QLineEdit("dBm")

        self.styleLayout = QGridLayout()
        self.styleLayout.setColumnStretch(1, 2)
        self.styleLayout.addWidget(QLabel("X tick"), 0, 0)
        self.styleLayout.addWidget(QLabel("Y tick"), 1, 0)
        self.styleLayout.addWidget(QLabel("Y Decimal Point"), 2, 0)
        self.styleLayout.addWidget(QLabel("Power Unit"), 3, 0)
        self.styleLayout.addWidget(self.xtick, 0, 1)
        self.styleLayout.addWidget(self.ytick, 1, 1)
        self.styleLayout.addWidget(self.y_decimal_points, 2, 1)
        self.styleLayout.addWidget(self.powerUnit, 3, 1)

        # group box settings
        self.spectrogramSettings = QGroupBox("Settings")
        self.step = QSpinBox(value=1)  # type: ignore
        self.start = QSpinBox(value=1)  # type: ignore
        self.stop = QSpinBox(value=1)  # type: ignore

        self.settingLayout = QGridLayout()
        self.settingLayout.setColumnStretch(1, 2)
        self.settingLayout.addWidget(QLabel("Step"), 0, 0)
        self.settingLayout.addWidget(QLabel("Start"), 1, 0)
        self.settingLayout.addWidget(QLabel("Stop"), 2, 0)
        self.settingLayout.addWidget(self.step, 0, 1)
        self.settingLayout.addWidget(self.start, 1, 1)
        self.settingLayout.addWidget(self.stop, 2, 1)

        self.styleSettingsLayout = QHBoxLayout()
        self.styleSettingsLayout.addLayout(self.styleLayout)
        self.styleSettingsLayout.addLayout(self.settingLayout)

        # button
        self.plotSpectrogram = QPushButton("Spectrogram")

        self.spectrogramLayout.addWidget(self.channelSelector)
        self.spectrogramLayout.addLayout(self.styleSettingsLayout)
        self.spectrogramLayout.addWidget(self.plotSpectrogram)

    def validateMinMax(self):
        min_value = self.start.value()
        max_value = self.stop.value()

        if min_value >= max_value:
            self.start.setValue(max_value - 1)

    def update_values(self, file_num, powers):
        self.start.setMaximum(file_num)
        self.start.setMinimum(1)
        self.stop.setMaximum(file_num)
        self.stop.setValue(file_num)
        self.stop.setMinimum(1)
        self.channelSelector.selections = [True] * powers

    def start_worker(self, data):
        logging.info("Generating Spectrogram...")
        if self.worker is not None:
            if not self.worker.isFinished():
                logging.info(
                    "Previously started process is still running. Please wait for it to finish and try again."
                )
                return None

        # start worker / data processing
        self.worker = RaQThreadWorker(self.get_spectrogram, data)  # type: ignore
        self.worker.finished.connect(partial(self.slot_finished, data))
        self.worker.start()

    def slot_finished(self, data: MatDataReader):
        logging.info("Spectrogram generated. Plotting Spectrogram...")
        spectrogram_images = self.worker.result
        self.image_tab.clear()

        (_, wavelength, _) = data[0]
        wavelength = wavelength * 1e9

        # get step size from x ticks
        x_tick_step = int((self.end_index - self.start_index) / (self.xtick.value()))
        y_tick_step = int((len(wavelength) / (self.ytick.value())))

        # get x ticks
        x_label = data.timestamps[
            self.start_index : self.end_index : self.step_val
        ].tolist()
        x_position = list(range(len(x_label)))[::x_tick_step]
        x_label = x_label[::x_tick_step]
        x_label = [str(format(time, ".0f")) for time in x_label]
        self.xTicks = list(zip((x_position), x_label))

        # get y ticks
        y_position = list(range(len(wavelength)))
        y_label = wavelength[::y_tick_step].tolist()
        y_decimal_points = str(self.y_decimal_points.value())
        y_label = [str(format(i, f".{y_decimal_points}f")) for i in y_label]
        y_position = y_position[::y_tick_step]

        self.yTicks: list[tuple[float, str]] = list(zip((y_position), y_label))

        if len(y_label) != len(set(y_label)):
            new_y_tick = len(set(y_label))

            while new_y_tick > 0:
                y_position = list(range(len(wavelength)))
                y_tick_step = int(len(wavelength) / (new_y_tick))
                y_label = wavelength[::y_tick_step].tolist()
                y_decimal_points = str(self.y_decimal_points.value())
                y_label = [str(format(i, f".{y_decimal_points}f")) for i in y_label]
                y_position = y_position[::y_tick_step]
                self.yTicks: list[tuple[float, str]] = list(zip((y_position), y_label))

                if len(y_label) == len(set(y_label)):
                    break
                new_y_tick -= 1

            logging.warning(f"""Repetitive wavelength values selected. {len(y_label)} ticks will be displayed as instead. Change the decimal point to avoid repetition.""")
        
        # Plot spectrograms
        for index, spectrogram in spectrogram_images.items():
            if spectrogram is not None:
                # Add Plot item to show axis labels
                plot = pg.PlotItem()
                plot.setLabel(axis="left", text="Wavelength (nm)")
                plot.setLabel(axis="bottom", text="Timestamp (min)")
                plot.setTitle(f"Power {str(index + 1)} Spectrogram")
                image = ImageView(self, view=plot)
                image.ui.roiBtn.hide()
                image.ui.menuBtn.hide()
                image.getView().invertY(False)
                image.getView().setAspectLocked(False)
                image.setColorMap(pg.colormap.getFromMatplotlib("inferno"))
                image.setImage(spectrogram)
                image.autoRange()
                ax = image.view.getAxis("bottom")
                ay = image.view.getAxis("left")
                ax.setTicks([self.xTicks, []])
                ay.setTicks([self.yTicks, []])
                self.image_tab.addTab(image, f"Power {str(index + 1)}")

        logging.info("Spectrogram plotted!")
        self.image_window.show()

    def get_spectrogram(self, data: MatDataReader) -> dict[int, NDArray[np.floating]]:
        spectrogram_list_dict: dict[int, list[NDArray[np.floating]]] = {
            i: [] for i, b in enumerate(self.channelSelector.selections) if b
        }

        for _timestamp, _wavelengths, powers in islice(
            data, self.start_index, self.end_index, self.step_val
        ):
            for k in spectrogram_list_dict.keys():
                spectrogram_list_dict[k].append(powers[k])

        return {k: np.array(v) for k, v in spectrogram_list_dict.items()}

    def slot_save_all(self):
        if self.channelSelector.selections.count(True) == 0:
            raise RuntimeError("No spectrogram to save")

        dir = QFileDialog.getExistingDirectory()

        if os.path.isdir(dir):
            dir_svg = os.path.join(dir, "spectrogram_svg")
            try: # Create the folder if it doesn't exist
                os.makedirs(dir_svg)
            except FileExistsError:
                print(f"Folder '{dir_svg}' already exists.")

            for i in range(self.image_tab.count()):
                self.image_tab.setCurrentIndex(i)
                image: ImageView = self.image_tab.widget(i)  # type: ignore
                exporter = exporters.ImageExporter(image.view)
                num = self.image_tab.tabText(i)
                file_name = f"Power {num} Spectrogram.png"
                exporter.export(os.path.join(dir, file_name))
                
                file_name_svg = f"Power {num} Spectrogram.svg"
                exporter_svg = exporters.SVGExporter(image.view)
                exporter_svg.export(os.path.join(dir_svg, file_name_svg))

            print("Spectrograms successfully saved")

        else:
            raise FileExistsError("Directory not found")
