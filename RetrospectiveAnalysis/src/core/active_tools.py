import csv
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from itertools import pairwise
from typing import Any, Callable, Optional, Self

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, lsim, lti, sawtooth

logger = logging.getLogger(__name__)


@dataclass
class ConverterConfig:
    @dataclass(frozen=True)
    class ConvertMethod1:
        ai: list[float]
        xi: list[float]

        def __post_init__(self):
            if len(self.ai) != len(self.xi):
                raise ValueError("length of ci and xi mismatch")

        def __call__(self, x: float) -> float:
            return sum(
                [c * (x - x0) ** i for i, (c, x0) in enumerate(zip(self.ai, self.xi))]
            )

    @dataclass(frozen=True)
    class ConvertMethod2:
        fsr: float
        p_fsr: float
        r_heater: float
        v_offset: float

        def __call__(self, v: float) -> float:
            return (
                (self.fsr / (self.p_fsr * 1e-3))
                * (v - self.v_offset) ** 2
                / self.r_heater
            )

    class KeyTypes(Enum):
        SKIP_ROW = ("Skip_row", int)
        SKIP_COLUMN = ("Skip_column", int)
        RAMP_SIGNAL_SYMMETRY = ("Ramp signal symmetry", float)
        V_MIN = ("V_min", float)
        V_MAX = ("V_max", float)
        FREQUENCY = ("Frequency", float)
        LASER_WAVELENGTH = ("Laser Wavelength, lambda_0 [nm]", float)
        FILENAME_REGEX = ("Filename Prefix", str)
        DATA_SLICING_METHODS = ("Data Slicing Methods:", None)
        SLICING_METHOD1 = ("Method1: Ramp Reference Signal", bool)
        RAMP_CHANNEL = ("Ramp_channel", int)
        SLICING_METHOD2 = ("Method2: Fixed Sweep Datapoints", bool)
        EXCLUDE_START = ("exclude_start", float)
        EXCLUDE_END = ("exclude_end", float)
        FIXED_DATAPOINTS = ("fixed datapoints", int)
        OFFSET = ("offset", int)
        
        WAVELENGTH_CONVERSION_METHODS = ("Wavelength Conversion Methods:", None)
        METHOD1 = ("Method1: dlambda = Sigma{Ai*(x-xi)^i}", bool)
        A_ARRAY = ("A_array", list)
        X_ARRAY = ("X_array", list)
        METHOD2 = (
            "Method2: Thermal Phaseshifter , dlambda = (FSR/P_FSR)*(V-Voffset)^2/R",
            bool,
        )
        FSR = ("FSR", float)
        P_FSR = ("P_FSR", float)
        R_HEATER = ("R_heater", float)
        V_OFFSET = ("Voffset", float)

        THERMAL_RESPONSE = ("Thermal Response Methods:", None)
        THERMAL_METHOD1 = ("Method1: R and C values of thermal impedance", bool)
        R_ARRAY = ("R_array", list)
        C_ARRAY = ("C_array", list)
        TAU_ARRAY = ("Tau_array", list)
        GAIN = ("Gain", float)
        THERMAL_METHOD2 = ("Method2: Zero/Pole Transfer function", bool)
        Z_ARRAY = ("System_zeros", list)
        P_ARRAY = ("System_poles", list)
        ZP_GAIN = ("ZP_Gain", float)
        THERMAL_METHOD3 = ("Method3: Numerator and Denominator", bool)
        Num_ARRAY = ("Num_array", list)
        Denom_ARRAY = ("Denom_array", list)

    skip_row: int
    skip_column: int
    laser_wavelength: float
    ramp_signal_symmetry: float
    v_min: float
    v_max: float
    slicing_method1 : bool
    ramp_channel: int
    data_slicing_methods: None
    slicing_method2: bool
    exclude_start : float
    exclude_end: float
    fixed_datapoints : int
    offset : int
    wavelength_conversion_methods: None
    method1: bool
    a_array: list[float]
    x_array: list[float]
    method2: bool
    fsr: float
    p_fsr: float
    r_heater: float
    v_offset: float
    thermal_response: None
    thermal_method1: bool
    r_array: list[Optional[float]]
    c_array: list[Optional[float]]
    tau_array: list[Optional[float]]
    gain: float
    thermal_method2: bool
    z_array: list[Optional[float]]
    p_array: list[Optional[float]]
    zp_gain: float
    thermal_method3: bool
    num_array: list[Optional[float]]
    denom_array: list[Optional[float]]
    filename_prefix: str
    frequency: float

    def __post_init__(self):
        for e in self.KeyTypes:
            match e:
                case self.KeyTypes.SKIP_ROW:
                    self.__dict__.update({e.value[0]: self.skip_row})
                case self.KeyTypes.SKIP_COLUMN:
                    self.__dict__.update({e.value[0]: self.skip_column})
                case self.KeyTypes.RAMP_SIGNAL_SYMMETRY:
                    self.__dict__.update({e.value[0]: self.ramp_signal_symmetry})
                case self.KeyTypes.FILENAME_REGEX:
                    self.__dict__.update({e.value[0]: self.filename_prefix})
                case self.KeyTypes.V_MIN:
                    self.__dict__.update({e.value[0]: self.v_min})
                case self.KeyTypes.V_MAX:
                    self.__dict__.update({e.value[0]: self.v_max})
                case self.KeyTypes.FREQUENCY:
                    self.__dict__.update({e.value[0]: self.frequency})
                case self.KeyTypes.LASER_WAVELENGTH:
                    self.__dict__.update({e.value[0]: self.laser_wavelength})
                case self.KeyTypes.DATA_SLICING_METHODS:
                    self.__dict__.update({e.value[0]: self.data_slicing_methods})
                case self.KeyTypes.SLICING_METHOD1:
                    self.__dict__.update({e.value[0]: self.slicing_method1})
                case self.KeyTypes.RAMP_CHANNEL:
                    self.__dict__.update({e.value[0]: self.ramp_channel})
                case self.KeyTypes.SLICING_METHOD2:
                    self.__dict__.update({e.value[0]: self.slicing_method2})
                case self.KeyTypes.EXCLUDE_START:
                    self.__dict__.update({e.value[0]: self.exclude_start})         
                case self.KeyTypes.EXCLUDE_END:
                    self.__dict__.update({e.value[0]: self.exclude_end})         
                case self.KeyTypes.FIXED_DATAPOINTS:
                    self.__dict__.update({e.value[0]: self.fixed_datapoints})
                case self.KeyTypes.OFFSET:
                    self.__dict__.update({e.value[0]: self.offset})
                case self.KeyTypes.WAVELENGTH_CONVERSION_METHODS:
                    self.__dict__.update(
                        {e.value[0]: self.wavelength_conversion_methods}
                    )
                case self.KeyTypes.METHOD1:
                    self.__dict__.update({e.value[0]: self.method1})
                case self.KeyTypes.A_ARRAY:
                    self.__dict__.update({e.value[0]: self.a_array})
                case self.KeyTypes.X_ARRAY:
                    self.__dict__.update({e.value[0]: self.x_array})
                case self.KeyTypes.METHOD2:
                    self.__dict__.update({e.value[0]: self.method2})
                case self.KeyTypes.FSR:
                    self.__dict__.update({e.value[0]: self.fsr})
                case self.KeyTypes.P_FSR:
                    self.__dict__.update({e.value[0]: self.p_fsr})
                case self.KeyTypes.R_HEATER:
                    self.__dict__.update({e.value[0]: self.r_heater})
                case self.KeyTypes.V_OFFSET:
                    self.__dict__.update({e.value[0]: self.v_offset})
                case self.KeyTypes.THERMAL_RESPONSE:
                    self.__dict__.update({e.value[0]: self.thermal_response})
                case self.KeyTypes.THERMAL_METHOD1:
                    self.__dict__.update({e.value[0]: self.thermal_method1})
                case self.KeyTypes.R_ARRAY:
                    self.__dict__.update({e.value[0]: self.r_array})
                case self.KeyTypes.C_ARRAY:
                    self.__dict__.update({e.value[0]: self.c_array})
                case self.KeyTypes.TAU_ARRAY:
                    self.__dict__.update({e.value[0]: self.tau_array})
                case self.KeyTypes.GAIN:
                    self.__dict__.update({e.value[0]: self.gain})
                case self.KeyTypes.THERMAL_METHOD2:
                    self.__dict__.update({e.value[0]: self.thermal_method2})
                case self.KeyTypes.Z_ARRAY:
                    self.__dict__.update({e.value[0]: self.z_array})
                case self.KeyTypes.P_ARRAY:
                    self.__dict__.update({e.value[0]: self.p_array})
                case self.KeyTypes.ZP_GAIN:
                    self.__dict__.update({e.value[0]: self.zp_gain})
                case self.KeyTypes.THERMAL_METHOD3:
                    self.__dict__.update({e.value[0]: self.thermal_method3})
                case self.KeyTypes.Num_ARRAY:
                    self.__dict__.update({e.value[0]: self.num_array})
                case self.KeyTypes.Denom_ARRAY:
                    self.__dict__.update({e.value[0]: self.denom_array})
                case _:
                    raise ValueError(f"unsupported key {e}")

    @classmethod
    def from_csv(cls, csv_path: str) -> Self:
        params: dict[str, Any] = {}
        with open(csv_path, newline="") as f:
            reader = csv.reader(f, delimiter=",")
            for row in reader:
                for e in cls.KeyTypes:
                    if (key := row[0]) == e.value[0]:
                        type = e.value[1]
                        if type is list:
                            while row[-1].isspace() or row[-1] == "":
                                row = row[:-1]
                            params[key] = [
                                float(x) if x != "" else None for x in row[1:]
                            ]
                        elif type in (int, float):
                            params[key] = type(row[1])
                        elif type is bool:
                            params[key] = bool(int(row[1]))
                        elif type is str:
                            params[key] = str(row[1])
                        elif type is None:
                            continue
                        else:
                            raise ValueError(f"unsupported type {key}:{type}")
                        break

        config = cls(
            skip_row=params[cls.KeyTypes.SKIP_ROW.value[0]],
            skip_column=params[cls.KeyTypes.SKIP_COLUMN.value[0]],
            filename_prefix=params[cls.KeyTypes.FILENAME_REGEX.value[0]],
            ramp_channel=params[cls.KeyTypes.RAMP_CHANNEL.value[0]],
            ramp_signal_symmetry=params[cls.KeyTypes.RAMP_SIGNAL_SYMMETRY.value[0]],
            v_min=params[cls.KeyTypes.V_MIN.value[0]],
            v_max=params[cls.KeyTypes.V_MAX.value[0]],
            frequency=params[cls.KeyTypes.FREQUENCY.value[0]],
            laser_wavelength=params[cls.KeyTypes.LASER_WAVELENGTH.value[0]],
            data_slicing_methods=None,
            slicing_method1 = params[cls.KeyTypes.SLICING_METHOD1.value[0]],
            slicing_method2 = params[cls.KeyTypes.SLICING_METHOD2.value[0]],
            exclude_start = params[cls.KeyTypes.EXCLUDE_START.value[0]],
            exclude_end = params[cls.KeyTypes.EXCLUDE_END.value[0]],
            fixed_datapoints = params[cls.KeyTypes.FIXED_DATAPOINTS.value[0]],
            offset = params[cls.KeyTypes.OFFSET.value[0]],
            wavelength_conversion_methods=None,
            method1=params[cls.KeyTypes.METHOD1.value[0]],
            a_array=params[cls.KeyTypes.A_ARRAY.value[0]],
            x_array=params[cls.KeyTypes.X_ARRAY.value[0]],
            method2=params[cls.KeyTypes.METHOD2.value[0]],
            fsr=params[cls.KeyTypes.FSR.value[0]],
            p_fsr=params[cls.KeyTypes.P_FSR.value[0]],
            r_heater=params[cls.KeyTypes.R_HEATER.value[0]],
            v_offset=params[cls.KeyTypes.V_OFFSET.value[0]],
            thermal_response=None,
            thermal_method1=params[cls.KeyTypes.THERMAL_METHOD1.value[0]],
            r_array=params[cls.KeyTypes.R_ARRAY.value[0]],
            c_array=params[cls.KeyTypes.C_ARRAY.value[0]],
            tau_array=params[cls.KeyTypes.TAU_ARRAY.value[0]],
            gain=params[cls.KeyTypes.GAIN.value[0]],
            thermal_method2=params[cls.KeyTypes.THERMAL_METHOD2.value[0]],
            z_array=params[cls.KeyTypes.Z_ARRAY.value[0]],
            p_array=params[cls.KeyTypes.P_ARRAY.value[0]],
            zp_gain=params[cls.KeyTypes.ZP_GAIN.value[0]],
            thermal_method3=params[cls.KeyTypes.THERMAL_METHOD3.value[0]],
            num_array=params[cls.KeyTypes.Num_ARRAY.value[0]],
            denom_array=params[cls.KeyTypes.Denom_ARRAY.value[0]],
        )

        return config

    def to_csv(self, path: str):
        with open(path, "w", newline="") as f:
            writer = csv.writer(f, delimiter=",")
            for e in self.KeyTypes:
                k, t = e.value
                if t is None:
                    writer.writerow([None])
                    writer.writerow([k])
                elif t is list:
                    writer.writerow([k] + self.__dict__[k])
                elif t is bool:
                    writer.writerow([k, int(self.__dict__[k])])
                else:
                    writer.writerow([k, self.__dict__[k]])

    def wavelength_conversion_method(self):
        if self.method1:
            return self.ConvertMethod1(ai=self.a_array, xi=self.x_array)
        elif self.method2:
            return self.ConvertMethod2(
                fsr=self.fsr,
                p_fsr=self.p_fsr,
                r_heater=self.r_heater,
                v_offset=self.v_offset,
            )
        else:
            raise ValueError("No wavelength conversion method selected")


@dataclass
class CSVData:
    file_path: str
    skip_rows: int
    skip_columns: int
    ramp_channel: Optional[int]
    ramp: NDArray[np.floating] = field(default_factory=lambda: np.array([]))
    data: NDArray[np.floating] = field(default_factory=lambda: np.array([]))

    def __post_init__(self):
        data = np.loadtxt(
            self.file_path, delimiter=",", skiprows=self.skip_rows, encoding="cp1252"
        ).T
        if self.ramp_channel is not None:
            self.ramp = data[self.ramp_channel]
            data = np.delete(data, self.ramp_channel, 0)

        self.data = data[self.skip_columns :]

class SimpleRampCSVReaderBase:
    def __iter__(self) -> Any:
        ...

    @property
    def data_shape(self):
        ...


@dataclass
class SimpleRampUpCSVReader(SimpleRampCSVReaderBase):
    folder_path: str
    pattern: re.Pattern
    skip_rows: int
    skip_columns: int
    ramp_channel: Optional[int]
    data_slicing_method : Callable

    def __iter__(self):
        for filepath in [
            os.path.join(self.folder_path, f)
            for f in sorted(
                list(
                    filter(
                        lambda x: self.pattern.match(x),
                        iter(os.listdir(self.folder_path)),
                    )
                ),
                key=lambda x: int(self.pattern.match(x).group(1)),  # type: ignore
            )
        ]:
            csv_data = CSVData(
                filepath, self.skip_rows, self.skip_columns, self.ramp_channel
            )
    
            minima, maxima, _ = self.data_slicing_method(data=csv_data.ramp, num_of_points=csv_data.data.shape[1])

            if minima[0] >= maxima[0]:
                maxima = maxima[1:]
            if minima[-1] >= maxima[-1]:
                minima = minima[:-1]

            if len(minima) != len(maxima):
                raise ValueError(
                    "number of minima and maxima mismatch in reference signal"
                )
            for i, (start, stop) in enumerate(zip(minima, maxima)):
                yield csv_data.data[:, start:stop], (start, stop)

    @property
    def data_shape(self):
        filepath = [
            os.path.join(self.folder_path, f)
            for f in sorted(
                list(
                    filter(
                        lambda x: self.pattern.match(x),
                        iter(os.listdir(self.folder_path)),
                    )
                ),
                key=lambda x: int(self.pattern.match(x).group(1)),  # type: ignore
            )
        ][0]

        csv_data = CSVData(
            file_path=filepath,
            skip_rows=self.skip_rows,
            skip_columns=self.skip_columns,
            ramp_channel=self.ramp_channel,
        )

        return csv_data.data.shape


class SimpleRampDownCSVReader(SimpleRampUpCSVReader):
    def __iter__(self):
        for filepath in [
            os.path.join(self.folder_path, f)
            for f in sorted(
                list(
                    filter(
                        lambda x: self.pattern.match(x),
                        iter(os.listdir(self.folder_path)),
                    )
                ),
                key=lambda x: int(self.pattern.match(x).group(1)),  # type: ignore
            )
        ]:
            csv_data = CSVData(
                filepath, self.skip_rows, self.skip_columns, self.ramp_channel
            )

            maxima, _ = find_peaks(
                gaussian_filter1d(csv_data.ramp, 1),
                prominence=(np.max(csv_data.ramp) - np.min(csv_data.ramp)) * 0.9,
            )
            minima, _ = find_peaks(
                gaussian_filter1d(-csv_data.ramp, 1),
                prominence=(np.max(csv_data.ramp) - np.min(csv_data.ramp)) * 0.9,
            )
            if minima[0] > maxima[0]:
                minima = minima[1:]
            if minima[-1] < maxima[-1]:
                maxima = maxima[:-1]

            if len(minima) != len(maxima):
                raise ValueError(
                    "number of minima and maxima mismatch in reference signal"
                )
            for i, (start, stop) in enumerate(zip(minima, maxima)):
                yield csv_data.data[:, start:stop], (start, stop)


class SimpleRampUpDownCSVReader(SimpleRampUpCSVReader):
    def __iter__(self):
        for filepath in [
            os.path.join(self.folder_path, f)
            for f in sorted(
                list(
                    filter(
                        lambda x: self.pattern.match(x),
                        iter(os.listdir(self.folder_path)),
                    )
                ),
                key=lambda x: int(self.pattern.match(x).group(1)),  # type: ignore
            )
        ]:
            csv_data = CSVData(
                filepath, self.skip_rows, self.skip_columns, self.ramp_channel
            )

            minima, _ = find_peaks(
                gaussian_filter1d(-csv_data.ramp, 1),
                prominence=(np.max(csv_data.ramp) - np.min(csv_data.ramp)) * 0.9,
            )

            for start, stop in pairwise(minima):
                yield csv_data.data[:, start:stop], (start, stop)


class RampType(Enum):
    UP = 1
    DOWN = 0
    TRIANGLE = 0.5

    @classmethod
    def from_float(cls, value: float):
        if value == 1:
            return cls.UP
        elif value == 0:
            return cls.DOWN
        elif value == 0.5:
            return cls.TRIANGLE
        else:
            raise ValueError("unsupported value")


@dataclass(frozen=True)
class AdvancedCSVReaderBase:
    folder_path: str
    pattern: re.Pattern
    skip_rows: int
    skip_columns: int
    ramp_channel: Optional[int]
    lti_sys: lti
    frequency: float
    x_min: float
    x_max: float
    regulation_func: Callable[[float], float]
    data_slicing_func: Callable

    def __iter__(self) -> Any:
        ...

    def __len__(self) -> int:
        ...

    @property
    def data_shape(self):
        filepath = [
            os.path.join(self.folder_path, f)
            for f in sorted(
                list(
                    filter(
                        lambda x: self.pattern.match(x),
                        iter(os.listdir(self.folder_path)),
                    )
                ),
                key=lambda x: int(self.pattern.match(x).group(1)),  # type: ignore
            )
        ][0]

        csv_data = CSVData(
            file_path=filepath,
            skip_rows=self.skip_rows,
            skip_columns=self.skip_columns,
            ramp_channel=self.ramp_channel,
        )

        return csv_data.data.shape


class AdvancedRampUpCSVReader(AdvancedCSVReaderBase):
    def __len__(self):
        files = [
            os.path.join(self.folder_path, f)
            for f in list(
                filter(
                    lambda x: self.pattern.match(x),
                    iter(os.listdir(self.folder_path)),
                )
            )
        ]

        csv_data = CSVData(
            files[0], self.skip_rows, self.skip_columns, self.ramp_channel
        )

        (
            _,
            offset,
            offset_end,
            num_period,
            len_period,
        ) = generate_sawtooth_from_data(csv_data, RampType.UP, self.data_slicing_func)
        
        input: NDArray[np.floating] = sawtooth(
            np.linspace(0, 2 * np.pi * 500, len_period * 500),
            RampType.UP.value,  # type: ignore
        )
        input += 1
        input *= 0.5
        input -= self.x_min
        input *= self.x_max - self.x_min
        input += self.x_min
        input = self.regulation_func(input)  # type: ignore
        t, y, _ = lsim(
            self.lti_sys,
            input,
            np.linspace(0, 500 / self.frequency, len(input)),
        )
        period = y[-len_period:]

        out = np.concatenate([period for _ in range(num_period)])[offset:offset_end]

        maxima, _ = find_peaks(out)

        return len(maxima) * len(files)

    def __iter__(self):
        for filepath in [
            os.path.join(self.folder_path, f)
            for f in sorted(
                list(
                    filter(
                        lambda x: self.pattern.match(x),
                        iter(os.listdir(self.folder_path)),
                    )
                ),
                key=lambda x: int(self.pattern.match(x).group(1)),  # type: ignore
            )
        ]:
            csv_data = CSVData(
                filepath, self.skip_rows, self.skip_columns, self.ramp_channel
            )
            (
                _,
                offset,
                offset_end,
                num_period,
                len_period,
            ) = generate_sawtooth_from_data(csv_data, RampType.UP, self.data_slicing_func)

            input = sawtooth(
                np.linspace(0, 2 * np.pi * 500, len_period * 500),
                RampType.UP.value,  # type: ignore
            )
            input += 1
            input *= 0.5
            input -= self.x_min
            input *= self.x_max - self.x_min
            input += self.x_min
            input = self.regulation_func(input)  # type: ignore
            t, y, _ = lsim(
                self.lti_sys,
                input,
                np.linspace(0, 500 / self.frequency, len(input)),
            )
            period = y[-len_period:]
            
            # output of lti system 
            out = np.concatenate([period for _ in range(num_period)])[offset:offset_end]

            # slice data 
            start_indices, stop_indices, _ = self.data_slicing_func(out, num_of_points=len(out))

            if start_indices[0] >= stop_indices[0]:
                stop_indices = stop_indices[1:]
            if start_indices[-1] >= stop_indices[-1]:
                start_indices = start_indices[:-1]

            for start, stop in zip(start_indices, stop_indices):
                yield out[start:stop], csv_data.data[:, start:stop], start, stop

class AdvancedRampDownCSVReader(AdvancedCSVReaderBase):
    def __len__(self):
        files = [
            os.path.join(self.folder_path, f)
            for f in list(
                filter(
                    lambda x: self.pattern.match(x),
                    iter(os.listdir(self.folder_path)),
                )
            )
        ]

        csv_data = CSVData(
            files[0], self.skip_rows, self.skip_columns, self.ramp_channel
        )

        (
            _,
            offset,
            offset_end,
            num_period,
            len_period,
        ) = generate_sawtooth_from_data(csv_data.ramp, RampType.DOWN)

        input: NDArray[np.floating] = sawtooth(
            np.linspace(0, 2 * np.pi * 500, len_period * 500),
            RampType.UP.value,  # type: ignore
        )
        input += 1
        input *= 0.5
        input -= self.x_min
        input *= self.x_max - self.x_min
        input += self.x_min
        input = self.regulation_func(input)  # type: ignore
        t, y, _ = lsim(
            self.lti_sys,
            input,
            np.linspace(0, 500 / self.frequency, len(input)),
        )
        period = y[-len_period:]

        out = np.concatenate([period for _ in range(num_period)])[offset:offset_end]

        maxima, _ = find_peaks(out)

        return len(maxima) * len(files)

    def __iter__(self):
        for filepath in [
            os.path.join(self.folder_path, f)
            for f in sorted(
                list(
                    filter(
                        lambda x: self.pattern.match(x),
                        iter(os.listdir(self.folder_path)),
                    )
                ),
                key=lambda x: int(self.pattern.match(x).group(1)),  # type: ignore
            )
        ]:
            csv_data = CSVData(
                filepath, self.skip_rows, self.skip_columns, self.ramp_channel
            )

            (
                _,
                offset,
                offset_end,
                num_period,
                len_period,
            ) = generate_sawtooth_from_data(csv_data.ramp, RampType.DOWN)

            input = sawtooth(
                np.linspace(0, 2 * np.pi * 500, len_period * 500),
                RampType.DOWN.value,  # type: ignore
            )
            input += 1
            input *= 0.5
            input -= self.x_min
            input *= self.x_max - self.x_min
            input += self.x_min
            input = self.regulation_func(input)  # type: ignore
            t, y, _ = lsim(
                self.lti_sys,
                input,
                np.linspace(0, 500 / self.frequency, len(input)),
            )
            period = y[-len_period:]

            out = np.concatenate([period for _ in range(num_period)])[offset:offset_end]

            maxima, _ = find_peaks(out)
            minima, _ = find_peaks(-out)

            if minima[0] < maxima[0]:
                minima = minima[1:]

            if maxima[-1] > minima[-1]:
                maxima = maxima[:-1]

            if len(maxima) != len(minima):
                raise ValueError(
                    "number of minima and maxima mismatch in reference signal"
                )

            start_indices, stop_indices = self.data_slicing_func(out, offset=(len_period-offset))
            
            for start, stop in zip(stop_indices, start_indices):
                yield out[stop:start:-1], csv_data.data[:, stop:start:-1], start, stop


class AdvancedRampUpDownCSVReader(AdvancedCSVReaderBase):
    def __len__(self):
        files = [
            os.path.join(self.folder_path, f)
            for f in list(
                filter(
                    lambda x: self.pattern.match(x),
                    iter(os.listdir(self.folder_path)),
                )
            )
        ]

        csv_data = CSVData(
            files[0], self.skip_rows, self.skip_columns, self.ramp_channel
        )

        (
            _,
            offset,
            offset_end,
            num_period,
            len_period,
        ) = generate_sawtooth_from_data(csv_data.ramp, RampType.UP)
        input: NDArray[np.floating] = sawtooth(
            np.linspace(0, 2 * np.pi * 500, len_period * 500),
            RampType.UP.value,  # type: ignore
        )
        input += 1
        input *= 0.5
        input -= self.x_min
        input *= self.x_max - self.x_min
        input += self.x_min
        input = self.regulation_func(input)  # type: ignore
        t, y, _ = lsim(
            self.lti_sys,
            input,
            np.linspace(0, 500 / self.frequency, len(input)),
        )
        period = y[-len_period:]

        out = np.concatenate([period for _ in range(num_period)])[offset:offset_end]

        maxima, _ = find_peaks(out)
        minima, _ = find_peaks(-out)

        return (2 * min(len(maxima), len(minima)) - 1) * len(files)

    def __iter__(self):
        for filepath in [
            os.path.join(self.folder_path, f)
            for f in sorted(
                list(
                    filter(
                        lambda x: self.pattern.match(x),
                        iter(os.listdir(self.folder_path)),
                    )
                ),
                key=lambda x: int(self.pattern.match(x).group(1)),  # type: ignore
            )
        ]:
            csv_data = CSVData(
                filepath, self.skip_rows, self.skip_columns, self.ramp_channel
            )

            (
                _,
                offset,
                offset_end,
                num_period,
                len_period,
            ) = generate_sawtooth_from_data(csv_data.ramp, RampType.TRIANGLE)

            input = sawtooth(
                np.linspace(0, 2 * np.pi * 500, len_period * 500),
                RampType.TRIANGLE.value,  # type: ignore
            )
            input += 1
            input *= 0.5
            input -= self.x_min
            input *= self.x_max - self.x_min
            input += self.x_min
            input = self.regulation_func(input)  # type: ignore
            t, y, _ = lsim(
                self.lti_sys,
                input,
                np.linspace(0, 500 / self.frequency, len(input)),
            )
            period = y[-len_period:]

            out = np.concatenate([period for _ in range(num_period)])[offset:offset_end]

            maxima, _ = find_peaks(out)
            minima, _ = find_peaks(-out)

            is_rising = True if minima[0] < maxima[0] else False

            if is_rising:
                indices = [i for pair in zip(minima, maxima) for i in pair]
            else:
                indices = [i for pair in zip(maxima, minima) for i in pair]

            for start, stop in pairwise(indices):
                if is_rising:
                    yield out[start:stop], csv_data.data[:, start:stop], start, stop
                else:
                    yield out[stop:start:-1], csv_data.data[
                        :, stop:start:-1
                    ], start, stop
                is_rising = not is_rising


def generate_sawtooth_from_data(
        data: CSVData, 
        ramp_type: RampType, 
        data_slicing_method : Callable
    ):

    maxima, minima, length_period = data_slicing_method(data.ramp, num_of_points=data.data.shape[1])
    num_period = int(np.ceil(data.data.shape[1] / length_period)) + 1

    make_up = sawtooth(
        np.linspace(
            0,
            2 * np.pi * (num_period),
            length_period * (num_period),
        ),
        ramp_type.value,  # type: ignore
    )
    offset: int = (
        length_period - minima[0]
        if length_period > minima[0]
        else 2 * length_period - minima[0]
    )
    offset_end: int = -(len(make_up) - data.data.shape[1] - offset)

    make_up: NDArray[np.floating] = make_up[offset:offset_end]

    return make_up, offset, offset_end, num_period, length_period
