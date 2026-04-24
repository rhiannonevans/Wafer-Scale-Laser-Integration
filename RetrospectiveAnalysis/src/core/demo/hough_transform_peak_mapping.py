import os
import re

import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat

from src.core.lib import SweepFitResult, get_lorentzian_peaks

if __name__ == "__main__":
    base_folder = os.path.expanduser("~/path/to/folder")
    pat = re.compile(r"laser_sweep_(\d+)\.mat")
    filenames = sorted(
        list(filter(lambda x: pat.match(x), iter(os.listdir(base_folder)))),
        key=lambda x: int(pat.match(x).group(1)),  # type: ignore
    )

    powers = np.array(
        [loadmat(os.path.join(base_folder, f))["power"] for f in filenames]
    )
    wavelengths = np.array(
        [loadmat(os.path.join(base_folder, f))["wavelength"][0] for f in filenames]
    )

    powers = powers.swapaxes(0, 2)
    powers = powers.swapaxes(1, 2)

    power = powers[0]

    trace = loadmat(os.path.join(base_folder, "RA_result/peak_shifts.mat"))[
        "power_1_peakWL_list"
    ][0]

    peak_set = []
    for i, sweep in enumerate(power):
        # peaks_wl = get_lorentzian_peaks(sweep, wavelengths[i] * 1e9)[0]
        peaks_wl = SweepFitResult.from_data(sweep, wavelengths[i] * 1e9).get_peaks()
        for p in peaks_wl:
            peak_set.append(np.array([i, p[0] - trace[i]]))

    peak_set = np.array(peak_set, dtype=np.float32)
    lines = cv2.HoughLinesPointSet(
        peak_set.reshape(-1, 1, 2),
        lines_max=20,
        threshold=5,
        min_rho=-100,
        max_rho=100,
        rho_step=0.1,
        min_theta=(min_theta := np.pi / 2 - np.pi / 180 * 10),
        max_theta=(max_theta := np.pi / 2 + np.pi / 180 * 10),
        theta_step=(max_theta - min_theta) / 2,
    )

    print(lines)

    rhos = np.squeeze(lines)[:, 1]
    print(rhos)

    plt.scatter(peak_set[:, 0], peak_set[:, 1])
    for r in rhos:
        plt.hlines(r, min(peak_set[:, 0]), max(peak_set[:, 0]))
    plt.show()

    for x, y in peak_set:
        plt.scatter(x, y + trace[int(x)], color="blue")
    plt.show()

    foo = [[] for _ in range(len(rhos))]
    for p in peak_set:
        DELTA = 0.1
        for i, rho in enumerate(rhos):
            if abs(p[1] - rho) < DELTA:
                foo[i].append(p)
                break

    xs = [t[0] for t in peak_set]
    ys = np.array([t[1] for t in peak_set])
    # plt.scatter(xs, ys, alpha=0.3)
    for set in foo:
        xs = [t[0] for t in set]
        ys = np.array([t[1] + trace[int(t[0])] for t in set])
        plt.scatter(xs, ys)
    plt.show()
