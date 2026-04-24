import logging
from dataclasses import dataclass
from itertools import accumulate, groupby, pairwise, product
from typing import Callable, Optional

import numpy as np
from cv2 import HoughLinesPointSet
from deprecated import deprecated
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
from scipy.sparse import csr_array
from scipy.sparse.csgraph import dijkstra
from scipy.spatial.distance import cdist
from sklearn.metrics import r2_score
from sklearn.preprocessing import MinMaxScaler

from .utils.ragged_array import RaggedArray

logger = logging.getLogger(__name__)


def lorentzian(x, x0, y0, _i, gamma, a):
    return (
        y0
        + ((_i * (gamma / 2) ** 2) / ((gamma / 2) ** 2 + (x - x0) ** 2))
        + a * (x - x0)
    )


@dataclass
class LorentzianPeakFitResult:
    peak_params: NDArray[np.floating]
    er: float
    q: float
    r2: float
    lambda0: float
    fwhm: float
    n100dbm_points: int


def find_peak_and_properties(
    powers: NDArray[np.floating],
    gaussian_filter_sigma=8.0,
    prominence_scaler=0.1,
    distance: Optional[int] = None,
):
    powers_smoothed: NDArray[np.floating] = gaussian_filter1d(
        powers, sigma=gaussian_filter_sigma
    )  # type: ignore
    indices, properties = find_peaks(
        -1 * powers_smoothed,
        prominence=prominence_scaler * (max(powers_smoothed) - min(powers_smoothed)),
        width=0,
        height=min(-1 * powers_smoothed),
        distance=distance,
    )
    __base_indices = [int(np.mean(p)) for p in pairwise(indices)]
    left_base_indices = [0] + __base_indices
    right_base_indices = __base_indices + [len(powers_smoothed) - 1]
    return indices, properties, left_base_indices, right_base_indices


@dataclass
class SweepFitResult:
    peaks: list[LorentzianPeakFitResult]

    @staticmethod
    def from_data(
        powers: NDArray[np.floating],
        wavelengths: NDArray[np.floating],
        gaussian_filter_sigma: float=8,
        prominence_scaler=0.1,
        distance: Optional[int] = None,
    ):
        if len(powers) != len(wavelengths):
            raise RuntimeError("Number of wavelengths and powers do not match")

        (
            indices,
            properties,
            left_base_indices,
            right_base_indices,
        ) = find_peak_and_properties(
            powers,
            gaussian_filter_sigma=gaussian_filter_sigma,
            prominence_scaler=prominence_scaler,
            distance=distance,
        )

        peaks: list[LorentzianPeakFitResult] = []
        for i, peak_index in enumerate(indices):
            left_base_index = max(properties["left_bases"][i], left_base_indices[i])
            right_base_index = min(properties["right_bases"][i], right_base_indices[i])

            wavelength_range = wavelengths[left_base_index:right_base_index]
            power_range = powers[left_base_index:right_base_index]

            # -100 is a bug value and should be ignored
            indices_fixed = np.argwhere(power_range != float(-100)).flatten()
            if len(indices_fixed) <= 8:
                # nearly all points are -100
                continue
            n100dbm_points = max(np.diff(indices_fixed))
            wavelength_fixed = wavelength_range[indices_fixed]
            power_fixed = power_range[indices_fixed]

            try:
                parameters, _ = curve_fit(
                    f=lorentzian,
                    xdata=wavelength_fixed,
                    ydata=power_fixed,
                    p0=[
                        wavelengths[peak_index],  # x0
                        np.mean(
                            [powers[left_base_index], powers[right_base_index]]
                        ),  # y0
                        -100,  # I
                        0.01
                        * (
                            wavelengths[right_base_index] - wavelengths[left_base_index]
                        ),  # gamma
                        0,  # a
                    ],
                    bounds=(
                        [
                            wavelengths[left_base_index],
                            -100,
                            -100,
                            0,
                            -np.inf,
                        ],
                        [
                            wavelengths[right_base_index],
                            np.inf,
                            0,
                            max(wavelength_fixed) - min(wavelength_fixed),
                            np.inf,
                        ],
                    ),
                )

                x0, y0, _i, gamma, a = parameters
                r2: float = r2_score(  # type: ignore
                    power_fixed, lorentzian(wavelength_fixed, x0, y0, _i, gamma, a)
                )

                power_fixed_linear_scaled = (
                    MinMaxScaler()
                    .fit_transform(10 ** (power_fixed / 10).reshape(-1, 1))
                    .squeeze()
                )

                params_linear, _ = curve_fit(
                    f=lorentzian,
                    xdata=wavelength_fixed,
                    ydata=power_fixed_linear_scaled,
                    p0=[
                        x0,
                        0,
                        -0.5,
                        0.01
                        * (
                            wavelengths[right_base_index] - wavelengths[left_base_index]
                        ),
                        0,
                    ],
                    bounds=(
                        [wavelengths[left_base_index], 0, -2, 0, -np.inf],
                        [wavelengths[right_base_index], 1, 0, np.inf, np.inf],
                    ),
                )

                peaks.append(
                    LorentzianPeakFitResult(
                        peak_params=parameters,
                        er=-parameters[2],
                        q=params_linear[0] / params_linear[3],  # Q = x0/gamma
                        r2=r2,
                        lambda0=params_linear[0],
                        fwhm=params_linear[3],
                        n100dbm_points=n100dbm_points,
                    )
                )

            except RuntimeError as e:
                logger.debug(
                    f"Curve fitting at wavelength {wavelengths[peak_index]:.2f}: {e}"
                )
                continue
        return SweepFitResult(peaks)

    def get_peaks(self, r2_threshold: float = 0.5, n100dbm_threshold: int = 30):
        return np.array(
            [
                p.peak_params
                for p in self.peaks
                if p.r2 > r2_threshold and p.n100dbm_points < n100dbm_threshold
            ]
        )

    def get_fsr(self, r2_threshold: float = 0.5, n100dbm_threshold: int = 30):
        if len(self.peaks) <= 1:
            return np.array([])
        else:
            peaks = np.array(
                [
                    p.peak_params
                    for p in self.peaks
                    if p.r2 > r2_threshold and p.n100dbm_points < n100dbm_threshold
                ]
            )
            return np.diff(peaks[:, 0])

    def get_er(self, r2_threshold: float = 0.5, n100dbm_threshold: int = 30):
        return np.array(
            [
                p.er 
                for p in self.peaks
                if p.r2 > r2_threshold and p.n100dbm_points < n100dbm_threshold
            ]
        )

    def get_q(self, r2_threshold: float = 0.5, n100dbm_threshold: int = 30):
        return np.array(
            [
                p.q
                for p in self.peaks
                if p.r2 > r2_threshold and p.n100dbm_points < n100dbm_threshold
            ]
        )

    def get_r2(self, r2_threshold: float = 0.5, n100dbm_threshold: int = 30): # ADDED, MAQ
        return np.array(
            [
                p.r2
                for p in self.peaks
                if p.r2 > r2_threshold and p.n100dbm_points < n100dbm_threshold
            ]
        )

    def get_lambda0(self, r2_threshold: float = 0.5, n100dbm_threshold: int = 30): # ADDED, MAQ
        return np.array(
            [
                p.lambda0
                for p in self.peaks
                if p.r2 > r2_threshold and p.n100dbm_points < n100dbm_threshold
            ]
        )

    def get_fwhm(self, r2_threshold: float = 0.5, n100dbm_threshold: int = 30): # ADDED, MAQ
        return np.array(
            [
                p.fwhm
                for p in self.peaks
                if p.r2 > r2_threshold and p.n100dbm_points < n100dbm_threshold
            ]
        )


def group_peaks(
    peaks_wl: list[NDArray[np.floating]],
    reference: NDArray[np.floating],
) -> list[list[tuple[int, int]]]:
    """group_peaks

    Args:
        peaks_wl (list[NDArray[np.float64]]): jagged array of peak wavelengths
        reference (NDArray[np.float64]): 1D array of reference wavelengths from peak tracking result

        The above two arguments should have the same length in their first dimension

    Returns:
        list[list[tuple[int, int]]]: 1D array of trace, where a trace is [(i,j)], peaks_wl[i][j] is a peak in this trace
    """
    peaks_wl_horizontal = [p - reference[i] for i, p in enumerate(peaks_wl)]
    point_set = np.array([[i, p] for i, ps in enumerate(peaks_wl_horizontal) for p in ps], dtype=np.float32)  # type: ignore
    lines = np.squeeze(
        HoughLinesPointSet(
            point_set.reshape(-1, 1, 2),
            lines_max=15,
            threshold=20,
            min_rho=-100,
            max_rho=100,
            rho_step=0.1,
            min_theta=(min_theta := np.pi / 2 - np.pi / 180 * 10),  # -10 deg
            max_theta=(max_theta := np.pi / 2 + np.pi / 180 * 10),  # +10 deg
            theta_step=(max_theta - min_theta)
            / 2,  # set a large step to check horizontal line only
        )
    )
    rhos = np.array(lines.T[1], ndmin=1)

    groups: list[list[tuple[int, int]]] = [[] for _ in range(len(rhos))]
    EPSILON = 0.1
    for i, ps in enumerate(peaks_wl_horizontal):
        for j, p in enumerate(ps):
            for k, r in enumerate(rhos):
                if abs(p - r) < EPSILON:
                    groups[k].append((i, j))
                    break

    return groups


def euclidean_distance(a, b):
    return cdist(np.array([a]), np.array([b]), "euclidean")[0][0]


def cosine_distance(a, b):
    return cdist(np.array([a]), np.array([b]), "cosine")[0][0]


@deprecated(
    reason="This is the old algorithm used in 202205-202308 Use `peaks_to_traces` instead",
    action="always",
)
def peaks_to_traces_old(
    peaks: list[NDArray[np.floating]],
    weights: NDArray[np.floating] = np.diag([1, 1, 1, 1, 1]),
) -> tuple[list[list[float]], float]:
    """__peaks_to_traces

    Convert sweeps (in matrix form) into a few traces with FSR

    Args:
        peaks (list[NDArray[np.float64]]): list of sweeps in matrix form where each row is a peak vector

    Returns:
        tuple[list[list[float]], float]: ([traces], FSR)
    """

    def __weighted_distance_with_x0(a, b):
        return euclidean_distance(np.matmul(weights, a), np.matmul(weights, b))

    def __weighted_distance_without_x0(a, b):
        return euclidean_distance(np.matmul(weights, a)[1:], np.matmul(weights, b)[1:])

    try:
        FSR = float(
            np.mean(
                [
                    d
                    for sweep in peaks[::10]
                    if sweep.ndim > 1
                    for d in np.diff(sweep[:, 0])
                ]
            )
        )
        population: NDArray[np.floating] = np.array(
            [p for sweep in peaks[::10] for p in sweep]
        )
        mean_population = np.mean(population, axis=0)
        std_population = np.std(population, axis=0)

        pair_iter = enumerate(pairwise(peaks))

        ret: list[list[float]] = []
        shifts: list[float] = []
        start_wavelength: float = peaks[0][0][0]
        last_peak = peaks[0][0]
    except IndexError as e:
        raise IndexError("No peaks found in the first sweep.") from e

    for i, (p1s, p2s) in pair_iter:
        ps = sorted(  # possible peaks in p2s to pair with the last peak
            [p for p in p2s if abs(p[0] - last_peak[0]) < 0.3 * FSR],
            key=lambda x: __weighted_distance_without_x0(
                (x - mean_population) / std_population,
                (last_peak - mean_population) / std_population,
            ),
        )
        if (  # normal case, a small shift near the last tracked peak is found and their shapes are similar
            ps and __weighted_distance_without_x0(ps[0], last_peak) < 2.5
        ):
            shifts.append(ps[0][0] - last_peak[0])
            last_peak: NDArray[np.floating] = ps[0]
            continue
        else:
            pairs = sorted(  # match other peaks in case that the peak correspond to the last peak is missing due to noise
                product([p for p in p1s if p[0] != last_peak[0]], p2s),
                key=lambda x: __weighted_distance_with_x0(
                    (x[0] - mean_population) / std_population,
                    (x[1] - mean_population) / std_population,
                ),
            )
            if (
                # if no other peaks in p1s
                len(pairs) <= 0
                or
                # if the minimum difference in shape is still too large
                __weighted_distance_without_x0(
                    (pairs[0][0] - mean_population) / std_population,
                    (pairs[0][1] - mean_population) / std_population,
                )
                > 2.5
            ):
                shifts.append(np.nan)
                logger.warning(
                    f"Peak shift from sweep index {i} to {i+1} cannot be determined. Cannot find matching peaks at wavelength {last_peak[0]:.2f}."
                )
                _, (_, temp) = next(pair_iter, (None, (None, None)))
                if temp is not None:
                    ret.append(list(accumulate([start_wavelength] + shifts)))
                    shifts = []
                    if temp.size > 0:
                        last_peak = temp[0]
                        start_wavelength = temp[0][0]
                continue
            elif (  # if the peak shift is too large but the shapes match
                abs(pairs[0][1][0] - pairs[0][0][0]) > 0.5 * FSR
            ):
                logger.warning(
                    f"Peak shift from sweep index {i} to {i+1} is too large and may be incorrect."
                )
                logger.debug(f"Peak index {i}: {pairs[0][0]}")
                logger.debug(f"Peak index {i+1}: {pairs[0][1]}")
                logger.debug(f"Peak shift: {pairs[0][1][0] - pairs[0][0][0]}")

                # degrade to the nearest peak
                pair = sorted(  # do not match the last on-track peak in case that the corresponding peak is missing in the next sweep
                    product([p for p in p1s if p[0] != last_peak[0]], p2s),
                    key=lambda x: abs(x[1][0] - x[0][0]),
                )[
                    0
                ]
                shifts.append(pair[1][0] - pair[0][0])
                last_peak = pair[1]

                # append the current trace and start a new trace
                _, (_, temp) = next(pair_iter, (None, (None, None)))
                if temp is not None:
                    ret.append(list(accumulate([start_wavelength] + shifts)))
                    shifts = []
                    if temp.size > 0:
                        last_peak = temp[0]
                        start_wavelength = temp[0][0]
                continue
            else:  # normal case, an acceptable pair in other peaks is found
                shifts.append(pairs[0][1][0] - pairs[0][0][0])
                last_peak = pairs[0][1]

    ret.append(list(accumulate([start_wavelength] + shifts)))

    return ret, FSR


@deprecated(reason="Directly call `peaks_to_traces` instead.", action="always")
def peaks_to_traces_default(peaks: list[list[np.floating]]):
    # Temporary API for backward compatibility
    return peaks_to_traces_dijkstra(peaks, euclidean_distance)
    # return peaks_to_traces_old(peaks) # The old algorithm


def peaks_to_traces(
    peaks: list[list[np.floating]] | list[NDArray[np.floating]],
    distance_func: Callable[[NDArray[np.floating], NDArray[np.floating]], float],
    shift_betweep_sweeps: float = 0.3,
    traces_threshold: int = 10,
):
    # API for future use
    return peaks_to_traces_dijkstra(peaks, distance_func, shift_betweep_sweeps, traces_threshold)


def __construct_adjacency_matrix(
    peaks: list[list[np.floating]] | list[NDArray[np.floating]],
    distance_func: Callable[[NDArray[np.floating], NDArray[np.floating]], float],
    shift_between_sweeps: float = 0.3,
):
    try:
        FSR = float(
            np.mean(
                [
                    d
                    for sweep in peaks[::10]
                    if len(sweep) > 1
                    for d in np.diff(sweep[:, 0])  # type: ignore
                ]
            )
        )
    except IndexError as e:
        raise IndexError("No peaks found in the first sweep.") from e

    ragged_peaks = RaggedArray(peaks)  # type: ignore

    # Create an adjacency matrix for the graph
    rows: list[float] = []
    cols: list[float] = []
    data: list[float] = []
    for (row1, col1, p1), (row2, col2, p2) in [
        [(row1, col1, p1), (row2, col2, p2)]
        for (row1, s1), (row2, s2) in pairwise(enumerate(ragged_peaks.array))
        for (col1, p1), (col2, p2) in product(enumerate(s1), enumerate(s2))
    ]:
        if abs(p1[0] - p2[0]) >= shift_between_sweeps * FSR:  # not a valid edge
            # weight = np.inf # This will still make them connected
            # weight = 0 # This will set the cost to 0, different than no value fields in sparse array. Do not use this.
            continue
        else:
            distance = distance_func(p1, p2)
            if distance == 0:  # avoid zero distance
                weight = np.nextafter(0, 1)  # the minimum positive float64
            else:
                weight = distance
        index1 = ragged_peaks.get_single_index(row1, col1)
        index2 = ragged_peaks.get_single_index(row2, col2)

        rows.append(index1)
        cols.append(index2)
        data.append(weight)

        rows.append(index2)
        cols.append(index1)
        data.append(weight)

    num_nodes = sum(len(sublist) for sublist in ragged_peaks.array)
    adjacency_matrix = csr_array((data, (rows, cols)), shape=(num_nodes, num_nodes))
    return FSR, adjacency_matrix


def peaks_to_traces_dijkstra(
    peaks: list[list[np.floating]] | list[NDArray[np.floating]],
    distance_func: Callable[[NDArray[np.floating], NDArray[np.floating]], float],
    shift_between_sweeps: float = 0.3,
    traces_threshold: int = 10,
):
    FSR, adjacency_matrix = __construct_adjacency_matrix(
        peaks, distance_func, shift_between_sweeps
    )

    ragged_peaks = RaggedArray(peaks)  # type: ignore

    start_single_index = 0
    end_single_index = len(ragged_peaks.double_indices)
    start_row = ragged_peaks.get_double_index(start_single_index)[0]
    end_row = ragged_peaks.get_double_index(end_single_index - 1)[0] + 1

    traces = np.ones(len(ragged_peaks.array)) * np.nan
    while end_row > start_row:
        end_single_indices = np.array(
            [
                ragged_peaks.get_single_index(end_row - 1, i)
                for i in range(len(ragged_peaks.array[end_row - 1]))
            ]
        )
        start_single_indices = np.array(
            [
                ragged_peaks.get_single_index(start_row, i)
                for i in range(len(ragged_peaks.array[start_row]))
            ]
        )

        dist_matrix, predecessors = dijkstra(
            adjacency_matrix[
                min(start_single_indices) : max(end_single_indices) + 1,
                min(start_single_indices) : max(end_single_indices) + 1,
            ],
            return_predecessors=True,
            indices=end_single_indices - min(start_single_indices),
        )

        if np.all(
            predecessors == -9999
        ):  # these end nodes are not connected to any other peaks in the previous sweep
            end_row -= 1
            logger.warning(f"sweep index {end_row} has no available peak connections")
            while len(ragged_peaks.array[end_row - 1]) == 0:
                end_row -= 1
            continue

        src = 0
        pivot = 0

        for i in range(dist_matrix.shape[1]):
            if np.all(np.isinf(dist_matrix[:, i])):
                continue
            else:
                pivot = i
                src = np.where(np.isfinite(dist_matrix[:, i]))[0][0]
                break

        trace = [pivot]
        while predecessors[src, pivot] != end_single_indices[src]:
            trace.append(predecessors[src, pivot])
            pivot = predecessors[src, pivot]
        trace.append(end_single_indices[src])

        if len(trace) > traces_threshold:  # threshold of minimum trace length
            for i, p in enumerate(trace[::-1]):
                traces[end_row - i - 1] = ragged_peaks[int(p)][0]

        end_row -= len(trace)
        if end_row != 0:
            traces[end_row] = np.nan
        while len(ragged_peaks.array[end_row - 1]) == 0:
            end_row -= 1
            if end_row != 0:
                traces[end_row] = np.nan

    return (
        [list(g) for _, g in groupby(traces, np.isnan)],  # split into sublist by nan
        FSR,
    )
