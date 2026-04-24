import csv
import logging
import multiprocessing as mp
import os
import re
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from functools import lru_cache, partial, reduce
from itertools import islice
from typing import Iterator

import numpy as np
from deprecated import deprecated
from numpy.typing import NDArray
from typing import Optional, List
from scipy.io import loadmat
from tqdm import tqdm

from .lib import SweepFitResult, peaks_to_traces_default
from .utils.tqdm_qt import tqdm_qt

logger = logging.getLogger(__name__)


Data = tuple[float, NDArray[np.floating], NDArray[np.floating]]
Sweep = NDArray[np.floating]


class DataReaderBase(metaclass=ABCMeta):
    @abstractmethod
    def __iter__(self) -> Iterator[Data]:
        # return the timestamp, wavelength of a sweep and the sweep 2D power data itself
        ...

    @abstractmethod
    def __len__(self) -> int:
        ...

    @abstractmethod
    def __getitem__(self, index: int) -> Data:
        ...

    @abstractmethod
    def sweep_only(self) -> Iterator[Sweep]:
        ...


@lru_cache
def read_mat(file_path: str) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    mat: dict[str, NDArray[np.floating]] = loadmat(file_path)
    power = np.array(mat["power"]).transpose()
    wavelengths = np.array(mat["wavelength"][0])
    if power.shape[1] != wavelengths.shape[0]:
        raise RuntimeError("Number of wavelengths and powers do not match")
    return (power, wavelengths)


@dataclass(frozen=True)
class MatDataReader(DataReaderBase):
    files: list[str]
    timestamps: NDArray[np.floating]

    @staticmethod
    def new(
        dir: str,
        files: list[str],
        timestamp_input: str | float,
        multiplier: float = 1,
    ):
        files = [os.path.join(dir, f) for f in files]
        match timestamp_input:
            case float():
                return MatDataReader(
                    files=files,
                    timestamps=np.arange(len(files)) * timestamp_input,
                )
            case str():
                name_index = 1
                time_index = 2
                time_dict: dict[str, float] = {}

                rows_seen = -1 # start at -1 because the first row is a header
                with open(timestamp_input) as csv_file:
                    for row in csv.reader(csv_file, delimiter=","):
                        rows_seen += 1
                        if len(row) != 0:
                            if row[0] == "Segment":
                                name_index = 2
                                time_index = 3
                                continue

                            elif len(row) >= 3 and row[2] != "":
                                time_dict[str(row[name_index])] = float(row[time_index])

                    base_names = [b for f in files if (b := os.path.basename(f)) in time_dict]  # type: ignore
                    timestamps = (
                        np.array(
                            [time_dict.get(k) for k in base_names], dtype=np.float64
                        )
                        * multiplier
                    )
                logger.debug(f"{rows_seen=}")
                logger.debug(f"{len(files)=}")
                logger.debug(f"{len(timestamps)=}")

                if rows_seen != len(files):
                    logger.warning(f"Number of rows in .csv file ({rows_seen}) does not align with the length of the file list ({len(files)}).")

                if rows_seen != len(timestamps):
                    logger.warning(f"Number of rows in .csv file ({rows_seen}) does not align with the length of the timestamps list ({len(timestamps)}).")

                return MatDataReader(files=files, timestamps=timestamps)

    def __iter__(self) -> Iterator[Data]:
        for t, f in zip(self.timestamps, self.files):
            power, wavelength = read_mat(f)
            yield t, wavelength, power

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, index: int) -> Data:
        power, wavelength = read_mat(self.files[index])
        timestamp = self.timestamps[index]
        return timestamp, wavelength, power

    def sweep_only(self) -> Iterator[Sweep]:
        for _, _, power in self:
            yield power


@dataclass(frozen=True)
class NPZDataReader(DataReaderBase):
    sweep_2d: dict[int, list[SweepFitResult]]
    spectrograms: NDArray[np.floating]
    wavelength: NDArray[np.floating]
    timestamps: NDArray[np.floating]

    @staticmethod
    def new(
        peak_file_path: str,
        spectrogram_file_path: str,
        timestamp_input: float,
    ):
        sweep_2d: list[list[SweepFitResult]] = np.load(
            peak_file_path, allow_pickle=True
        )["sweeps"]

        sweep_2d_dict: dict[int, list[SweepFitResult]] = {
            index: item for index, item in enumerate(sweep_2d)
        }
        spectrograms = np.load(spectrogram_file_path, allow_pickle=True)["spectrograms"]
        wavelength = np.load(spectrogram_file_path, allow_pickle=True)["wavelength"]

        return NPZDataReader(
            sweep_2d=sweep_2d_dict,
            spectrograms=spectrograms,
            wavelength=wavelength / 1e9,
            timestamps=np.arange(len(sweep_2d[0])) * timestamp_input,
        )

    def __iter__(self):
        for index in range(len(self.sweep_2d[0])):
            power = np.array(
                [np.array(channel[index]) for channel in self.spectrograms]
            )
            wavelength = self.wavelength
            yield self.timestamps[index], wavelength, power

    def __len__(self) -> int:
        return len(self.sweep_2d[0])

    def __getitem__(self, index: int):
        power = np.array([channel[index] for channel in self.spectrograms])
        wavelength = self.wavelength
        timestamp = self.timestamps[index]
        return timestamp, wavelength, power

    def sweep_only(self) -> Iterator[Sweep]:
        for _, _, power in self:
            yield power


def _powers_to_sweep_fit_results(
    powers: NDArray[np.floating], 
    wavelengths: NDArray[np.floating], 
    channels: set[int], 
    prom_scalar: Optional[List[float]]=None, 
    gaussian_filter: Optional[List[float]]=None
):
    if prom_scalar is None:
        prom_scalar = [0.1] * len(powers)
    if gaussian_filter is None:
        gaussian_filter = [8.0] * len(powers)

    return {c: [SweepFitResult.from_data(powers[c], 
                                        wavelengths,
                                        prominence_scaler=prom_scalar[c],
                                        gaussian_filter_sigma=gaussian_filter[c]
                                        )
                                    ] 
                                    for c in channels}

def get_spectrogram(
    data: DataReaderBase, channels: set[int], start, end, step
) -> dict[int, NDArray[np.floating]]:
    spectrogram_list_dict: dict[int, list[NDArray[np.floating]]] = {
        i: [] for i in channels
    }

    for _timestamp, _wavelengths, powers in islice(
        data, int(start), int(end), int(step)
    ):
        for k in spectrogram_list_dict.keys():
            spectrogram_list_dict[k].append(powers[k])

    return {k: np.array(v) for k, v in spectrogram_list_dict.items()}


@deprecated(
    reason="Use DataReaderBase and other analyze functions instead.", action="always"
)
class PassiveAnalyzer(object):
    def __init__(
        self,
        folder_path: str,
        timestamp: str | float,
        pattern: str = r".*sweep_(\d+)\.mat",
        timestamp_multiplier: float = 1 / 60,
    ):
        pat = re.compile(pattern)
        filenames = sorted(
            list(filter(lambda x: pat.match(x), iter(os.listdir(folder_path)))),
            key=lambda x: int(pat.match(x).group(1)),  # type: ignore
        )
        logger.debug(f"{folder_path=}")
        logger.debug(f"{filenames=}")
        logger.debug(f"{timestamp=}")
        logger.debug(f"{timestamp_multiplier=}")
        self.__data_reader: DataReaderBase = MatDataReader.new(
            folder_path, filenames, timestamp, timestamp_multiplier
        )

    @property
    def timestamps(self):
        return [t for t, _, _ in self.__data_reader]

    @property
    def wavelengths(self):
        _, wavelengths, _ = self.__data_reader[0]
        return wavelengths * 1e9

    def info(self) -> tuple[int, int]:
        """Get the number of files in the folder and the number of powers in the first file.

        Returns:
            Tuple[number_of_files, number_of_powers]
        """
        _, _, powers = self.__data_reader[0]

        return len(self.__data_reader), powers.shape[0]

    def get_spectrograms(
        self,
        channels: set[int],
        step: int = 1,
        start_index: int = 0,
        stop_index: int | None = None,
    ) -> dict[int, NDArray[np.floating]]:
        """Get spectrums at a given sample rate for the given channels.

        Args:
            `channels` (List[int]): the channel indexes e.g. [0,2,4] for channel 1,3,5
            `step` (int, optional): the down sample rate. Read one for each `step` files. Defaults to 1 (no down sample).

        Returns:
            `data`: Dict[K:`index`, V:`spectrogram`], where `spectrogram` is ready to be plotted with matplotlib.imshow()
        """
        data: dict[int, NDArray[np.floating]] = {}
        for matrix in islice(
            self.__data_reader.sweep_only(), start_index, stop_index, step
        ):
            for key in channels:
                vector = np.flip(np.array([matrix[key]])).transpose()
                data[key] = np.hstack((data[key], vector)) if key in data else vector
        return data

    def analyze(
        self,
        channels: set[int],
        start_stop_step: tuple[int, int, int],
        r2_threshold: float,
        max_n100dBm_points: int,
        qt_signal=None,
    ):
        """analyze

        Args:

            - channels (list[int]): the channel indexes e.g. [0,2,4] for channel 1,3,5
            - prominence (float): prominence for the peak detection
            - enable_multi_processing (bool, optional): Defaults to True. Set to false for debugging.

        Returns:

            - tuple[dict[int, tuple[list[list[float]], float]], dict[int, list[NDArray[np.float64]]] ]: traces dictionary and peaks dictionary, where keys are channel indexes and values are:

                - traces: (list of list of floats, FSR), the traces start at an actual peak wavelength in spectrogram.
                - peaks: list of sweep matrix, indexes are sweep number and values are rows of sweep vectors.
        """
        start, stop, step = start_stop_step[0], start_stop_step[1], start_stop_step[2]

        with mp.Pool() as pool:
            sweep_fit_dict: dict[int, list[SweepFitResult]] = reduce(
                lambda acc, b: {
                    x: acc.get(x, []) + b.get(x, []) for x in set(acc).union(b)  # type: ignore
                },
                tqdm_qt(
                    pool.imap(
                        partial(
                            _powers_to_sweep_fit_results,
                            wavelengths=self.wavelengths,
                            channels=channels,
                        ),
                        islice(self.__data_reader.sweep_only(), start, stop, step),
                    ),
                    total=(stop - start) // step,
                    qt_signal=qt_signal,
                ),
                {},
            )

        peaks_dict = {
            k: [s.get_peaks(r2_threshold, max_n100dBm_points) for s in v]
            for k, v in sweep_fit_dict.items()
        }

        for k, v in peaks_dict.items():
            if v[0].shape[0] == 0:
                raise RuntimeError(
                    f"The first sweep in channel {k+1} has no peaks detected. Consider adjusting the R2 threshold, -100dBm threshold or skipping this sweep."
                )

        return {k: peaks_to_traces_default(v) for k, v in peaks_dict.items()}, peaks_dict  # type: ignore

    def analyze_fsr_er_q(
        self,
        channels: set[int],
        start_stop_step: tuple[int, int, int],
        r2_threshold: float,
        max_n100dBm_points: int,
    ):
        start, stop, step = start_stop_step[0], start_stop_step[1], start_stop_step[2]

        with mp.Pool() as pool:
            sweep_fit_dict: dict[int, list[SweepFitResult]] = reduce(
                lambda acc, b: {
                    x: acc.get(x, []) + b.get(x, []) for x in set(acc).union(b)  # type: ignore
                },
                tqdm(
                    pool.imap(
                        partial(
                            _powers_to_sweep_fit_results,
                            wavelengths=self.wavelengths,
                            channels=channels,
                        ),
                        islice(self.__data_reader.sweep_only(), start, stop, step),
                    ),
                    total=(stop - start) // step,
                ),
                {},
            )

        return {
            k: [
                (
                    s.get_fsr(r2_threshold, max_n100dBm_points),
                    s.get_er(r2_threshold, max_n100dBm_points),
                    s.get_q(r2_threshold, max_n100dBm_points),
                )
                for s in v
            ]
            for k, v in sweep_fit_dict.items()
        }
