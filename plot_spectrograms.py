"""Simple spectrogram plotting script for .mat sweep files.

Saves per-channel spectrogram PNGs and an optional .npz with stacked spectrograms.

Usage (PowerShell):
    python .\plot_spectrograms.py -i "C:\path\to\mat_files" -o "C:\path\to\out" --invert

This script is purposely permissive when looking for variables inside .mat files:
- looks for common wavelength keys (wavelength, wl, lambda, x)
- looks for common power keys (power, powers, P, data, y)
- falls back to simple heuristics if the exact key isn't found

Dependencies:
    pip install numpy scipy matplotlib

"""
from __future__ import annotations

import argparse
import os
import sys
import logging
from typing import Tuple, List, Optional
import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy.io import loadmat, savemat
import re
from datetime import datetime
from pathlib import Path
from typing import Dict
try:
    # local import from repo
    from sweep_benchtop_continuous import extract_wavelength_and_ch3
except Exception:
    extract_wavelength_and_ch3 = None

# Import benchtop-specific Lorentzian fitter
try:
    from benchtop_lorentz_fitter import fit_and_track_benchtop_sweeps
    BENCHTOP_FITTER_AVAILABLE = True
except ImportError:
    BENCHTOP_FITTER_AVAILABLE = False
    fit_and_track_benchtop_sweeps = None

# Import on-chip Lorentzian fitter
try:
    from onchip_lorentz_fitter import fit_and_track_onchip_sweeps
    ONCHIP_FITTER_AVAILABLE = True
except ImportError:
    ONCHIP_FITTER_AVAILABLE = False
    onchip_lorentz_fitter = None

# Import eval system Lorentzian fitter
try:
    from evalsys_lorentz_fitter import fit_and_track_evalsys_sweeps
    EVALSYS_FITTER_AVAILABLE = True
except ImportError:
    EVALSYS_FITTER_AVAILABLE = False
    fit_and_track_evalsys_sweeps = None


def extract_temperature_from_csv(csv_path: str) -> Optional[np.ndarray]:
    """Extract temperature data from benchtop CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Temperature array or None if not found
    """
    try:
        with open(csv_path, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            
            label = parts[0].lower()
            
            # Check for temperature row
            if 'temperature' in label or 'temp' in label:
                # Extract numeric values from the rest of the row
                temp_vals = []
                for x in parts[1:]:
                    if x:
                        try:
                            temp_vals.append(float(x))
                        except ValueError:
                            continue
                
                if len(temp_vals) > 0:
                    temp_array = np.array(temp_vals)
                    # Filter out zeros
                    temp_array = temp_array[temp_array != 0]
                    if len(temp_array) > 0:
                        return temp_array
        
        return None
    except Exception as e:
        return None


# Optional interactive dependencies: pyqtgraph and PySide6. These are not required
# for non-interactive usage. Wrap imports so the script can be used in headless
# environments and add small inline ignores so static analyzers can be configured
# by the user (installing the packages is the preferred fix).
try:
    import pyqtgraph as pg  # type: ignore[reportMissingImports]
    from PySide6 import QtWidgets  # type: ignore[reportMissingImports]
    _HAS_PYQT = True
except Exception:
    pg = None  # type: ignore[assignment]
    QtWidgets = None  # type: ignore[assignment]
    _HAS_PYQT = False
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("plot_spectrograms")

# ============================================================================
# PLOT FORMATTING CONFIGURATION - Modify font sizes here to change all plots
# ============================================================================
PLOT_FONT_AXIS_LABEL = 25  # Font size for axis labels (xlabel, ylabel)
PLOT_FONT_AXIS_TICKS = 22  # Font size for axis tick labels
PLOT_FONT_TITLE = 22       # Font size for plot titles
PLOT_FONT_LEGEND = 18      # Font size for legend text
PLOT_FONT_TEXT = 9         # Font size for text annotations (e.g., statistics)
# ============================================================================

# Backwards-compatible aliases used in other scripts
AXIS_FONT_SIZE = PLOT_FONT_AXIS_LABEL
TICK_FONT_SIZE = PLOT_FONT_AXIS_TICKS
LEGEND_FONT_SIZE = PLOT_FONT_LEGEND
TITLE_FONT_SIZE = PLOT_FONT_TITLE


CANDIDATE_WAVELENGTH_KEYS = [
    "wavelength",
    "wavelengths",
    "wl",
    "lambda",
    "Lambda",
    "x",
    "w",
    "Wavelength",
]

CANDIDATE_POWER_KEYS = [
    "power",
    "powers",
    "P",
    "Power",
    "POWER",
    "data",
    "y",
    "Y",
    "power_data",
]


def find_candidate_key(mat: dict, candidates: List[str]) -> Optional[str]:
    """Return the first key in mat that matches candidates (case-sensitive) or None."""
    for c in candidates:
        if c in mat:
            return c
    # try case-insensitive
    lower = {k.lower(): k for k in mat.keys()}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def mat_to_array(obj) -> np.ndarray:
    """Convert various MATLAB-loaded objects into a numpy array and squeeze."""
    try:
        arr = np.array(obj)
    except Exception:
        # fallback: try to access .__array__ if present
        try:
            arr = np.asarray(obj)
        except Exception:
            raise
    arr = np.squeeze(arr)
    return arr


def load_mat_guess(path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load a .mat file and attempt to return (powers, wavelength).

    powers: 2D array (channels x wavelength) OR 1D array (wavelength,) for single channel
    wavelength: 1D array with length matching spectral dimension
    """
    logger.info(f"Loading {path}")
    mat = loadmat(path, squeeze_me=True, struct_as_record=False)

    # filter out matlab meta keys
    keys = [k for k in mat.keys() if not k.startswith("__")]
    logger.debug(f"MAT keys: {keys}")

    # try explicit keys first
    wl_key = find_candidate_key(mat, CANDIDATE_WAVELENGTH_KEYS)
    pow_key = find_candidate_key(mat, CANDIDATE_POWER_KEYS)

    wavelength = None
    powers = None

    if wl_key is not None:
        try:
            wavelength = mat_to_array(mat[wl_key])
        except Exception:
            wavelength = None

    if pow_key is not None:
        try:
            powers = mat_to_array(mat[pow_key])
        except Exception:
            powers = None

    # Heuristics fallback: find a 1D numeric array that looks like wavelength
    if wavelength is None:
        for k in keys:
            try:
                arr = mat_to_array(mat[k])
            except Exception:
                continue
            if arr.ndim == 1 and arr.size > 5 and np.issubdtype(arr.dtype, np.number):
                # choose the longest 1D numeric array as wavelength candidate
                if wavelength is None or arr.size > wavelength.size:
                    wavelength = arr

    # Heuristics fallback for powers: find a 1D or 2D numeric array with second dim == len(wavelength)
    if powers is None:
        candidates = []
        for k in keys:
            try:
                arr = mat_to_array(mat[k])
            except Exception:
                continue
            if not np.issubdtype(arr.dtype, np.number):
                continue
            if arr.ndim == 2:
                candidates.append((k, arr))
            elif arr.ndim == 1 and wavelength is not None and arr.size == wavelength.size:
                # single-channel sweep
                candidates.append((k, arr))
        # prefer 2D arrays
        chosen = None
        for k, arr in candidates:
            if arr.ndim == 2:
                chosen = arr
                break
        if chosen is None and candidates:
            chosen = candidates[0][1]
        powers = chosen

    # Final checks
    if powers is None:
        raise KeyError(
            f"No power-like variable found in {os.path.basename(path)}. Keys available: {keys}"
        )

    if wavelength is None:
        # if powers is 2D, assume the spectral axis is axis 1 and synthesize a wavelength index
        if powers.ndim == 2:
            wl = np.arange(powers.shape[1])
            logger.warning(f"No wavelength-like variable found in {os.path.basename(path)}; using integer indices as wavelength.")
            wavelength = wl
        elif powers.ndim == 1:
            wavelength = np.arange(powers.size)
            logger.warning(f"No wavelength-like variable found in {os.path.basename(path)}; using integer indices as wavelength.")
        else:
            raise KeyError(f"Cannot infer wavelength for file {path}")

    # Normalize shapes: we want powers as 2D: (channels, wavelength)
    if powers.ndim == 1:
        powers = powers[np.newaxis, :]
    elif powers.ndim == 2:
        # keep as-is (channels x wavelength) or (wavelength x channels) ?
        # Heuristic: if first dim equals wavelength length (and second is small), transpose
        if powers.shape[0] == wavelength.size and powers.shape[1] != wavelength.size:
            logger.debug("Transposing powers array to make shape (channels, wavelength)")
            powers = powers.T

    # ensure wavelength is 1D
    wavelength = np.asarray(wavelength).astype(float).squeeze()

    return powers.astype(float), wavelength.astype(float)


def build_spectrograms(files: List[str], invert: bool = False, start: int = 0, stop: Optional[int] = None, step: int = 1):
    """Load files and build spectrogram arrays per channel.

    Returns:
        spectrograms: list of 2D arrays (time x wavelength) for each channel
        wavelength: 1D array
    """
    files = files[start:stop:step]
    if len(files) == 0:
        raise RuntimeError("No files to process")

    all_powers = []
    wavelength = None
    for f in files:
        p, wl = load_mat_guess(f)
        if wavelength is None:
            wavelength = wl
        else:
            # if lengths differ, warn and adapt to shortest/longest by interpolation? for now require same
            if wl.size != wavelength.size:
                logger.warning(f"Wavelength length mismatch for {os.path.basename(f)} (found {wl.size} vs {wavelength.size}). Using the wavelength from the first file.")
        if invert:
            p = -p
        all_powers.append(p)

    # Determine number of channels from first file
    first = all_powers[0]
    channels = first.shape[0]
    time = len(all_powers)
    spec_per_channel = []
    for ch in range(channels):
        rows = []
        for p in all_powers:
            if p.shape[0] <= ch:
                # missing channel in this file: pad with NaNs
                rows.append(np.full(wavelength.size, np.nan))
            else:
                rows.append(p[ch])
        spec = np.vstack(rows)  # shape (time, wavelength)
        spec_per_channel.append(spec)

    return spec_per_channel, wavelength


def plot_and_save(spec: np.ndarray, wavelength: np.ndarray, out_png: str, title: str = None, cmap: str = "inferno"):
    """Plot spec (time x wavelength) and save as PNG."""
    time = spec.shape[0]
    fig, ax = plt.subplots(figsize=(10, 6))
    # imshow expects (Ny, Nx) -> pass spec.T so y->wavelength, x->time
    # extent: [x_min, x_max, y_min, y_max]. If user passed numeric time axis as 1D array
    # we expect it to be provided via 'title' or caller can remap labels; keep simple here.
    im = ax.imshow(spec.T, aspect="auto", origin="lower", cmap=cmap,
                   extent=[0, time - 1, wavelength.min(), wavelength.max()])
    ax.set_xlabel("Sweep index / Time (min)")
    ax.set_ylabel("Wavelength")
    # Ensure full numeric wavelength ticks (no scientific offset)
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter(useOffset=False))
    ax.ticklabel_format(style='plain', axis='y')
    if title:
        ax.set_title(title)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Power (mW)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    logger.info(f"Saved {out_png}")


def overlay_peak_traces_on_spectrogram(spec: np.ndarray, wavelength: np.ndarray, times: np.ndarray,
                                       all_peak_traces: list, out_png: str, title: str = None, 
                                       cmap: str = "inferno"):
    """Plot spectrogram with multi-peak traces overlaid (RA-style).
    
    Args:
        spec: 2D array (time x wavelength)
        wavelength: 1D array
        times: 1D array (time in minutes)
        all_peak_traces: list of dicts with 'centers' arrays
        out_png: output filename
        title: optional title
        cmap: colormap for spectrogram
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Plot spectrogram - use actual wavelength array order (not min/max)
    extent = [times.min(), times.max(), wavelength[0], wavelength[-1]]
    im = ax.imshow(spec.T, aspect="auto", origin="lower", cmap=cmap, extent=extent)
    
    # Overlay peak traces
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_peak_traces)))
    
    for idx, trace in enumerate(all_peak_traces):
        # Trim trace to match time dimension
        centers = trace['centers'][:len(times)]
        valid_mask = np.isfinite(centers)
        if np.any(valid_mask):
            ax.plot(times[valid_mask], centers[valid_mask],
                   'o-', linewidth=1.5, markersize=2, color=colors[idx], alpha=0.9,
                   label=f"Peak {idx+1}: {np.nanmean(centers):.3f} nm")
    
    ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_ylabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
    if title:
        ax.set_title(title, fontsize=PLOT_FONT_TITLE)
    
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL)
    try:
        cbar.ax.yaxis.set_major_formatter(mticker.ScalarFormatter(useOffset=False))
        cbar.ax.ticklabel_format(style='plain', axis='y')
    except Exception:
        pass
    
    if len(all_peak_traces) > 0:
        ax.legend(fontsize=PLOT_FONT_LEGEND, loc='upper right', ncol=2)
    
    fig.tight_layout()
    fig.savefig(out_png, dpi=300)
    plt.close(fig)
    logger.info(f"Saved multi-peak spectrogram with traces to {out_png}")


def quantify_fluctuations(spec: np.ndarray, wavelength: np.ndarray, times: np.ndarray,
                         output_dir: str, prefix: str = "spectrogram",
                         wl_roi: Optional[Tuple[float, float]] = None,
                         peak_mode: str = "dominant",
                         target_wavelength: Optional[float] = None,
                         prominence_threshold: float = 0.1,
                         data_type: str = "dbm",
                         temperature_data: Optional[np.ndarray] = None,
                         **kwargs):
    """Quantify power and wavelength fluctuations over time.
    
    Args:
        spec: 2D array (time x wavelength) of power values
        wavelength: 1D array of wavelength values
        times: 1D array of relative time values in minutes
        output_dir: Directory to save output plots and statistics
        prefix: Prefix for output filenames
        wl_roi: Optional tuple (wl_min, wl_max) to define region of interest for analysis
        peak_mode: How to select peaks:
            - "dominant": Track the global maximum (single highest peak)
            - "nearest": Track the peak nearest to target_wavelength
            - "all": Track all significant peaks (creates separate stats for each)
            - "lorentz"/"lorentz_seeded": Use multi-peak Lorentzian fitter
        target_wavelength: For peak_mode="nearest", the wavelength to track near (nm)
        prominence_threshold: For peak detection, minimum prominence relative to max power
        data_type: Type of power data:
            - "linear": Benchtop mW data (uses benchtop_lorentz_fitter)
            - "onchip": On-chip LIV mW data (uses onchip_lorentz_fitter)
            - "evalsys": Eval system inverted/normalized data (uses evalsys_lorentz_fitter)
            - "dbm": OSA dBm data (uses RA Dijkstra tracker)
        temperature_data: Optional array of temperature values (one per time point)
        **kwargs: Additional parameters passed to peak tracking (e.g., gaussian_filter_sigma, auto_flip)
    
    Returns:
        dict: Dictionary containing calculated statistics
    """
    logger.info(f"Quantifying fluctuations for {prefix} (peak_mode={peak_mode})...")
    
    # Filter to ROI if specified
    if wl_roi is not None:
        wl_min, wl_max = wl_roi
        wl_mask = (wavelength >= wl_min) & (wavelength <= wl_max)
        wavelength_roi = wavelength[wl_mask]
        spec_roi = spec[:, wl_mask]
    else:
        wavelength_roi = wavelength
        spec_roi = spec
    
    # Track peak wavelength over time based on selected mode
    peak_wavelengths = []
    peak_powers = []
    avg_powers = []
    all_peaks_per_time = []  # For "all" mode
    
    # For Lorentz-based tracking we call the appropriate adapter
    if peak_mode in ("lorentz", "lorentz_seeded"):
        try:
            # Choose fitter based on data type
            if data_type == "linear" and BENCHTOP_FITTER_AVAILABLE:
                # Use benchtop-specific fitter with baseline correction
                logger.info("Using benchtop_lorentz_fitter for linear power data")
                fit_results = fit_and_track_benchtop_sweeps(
                    spec_roi,
                    wavelength_roi,
                    **kwargs  # Pass through gaussian_filter_sigma, prominence_scaler, etc.
                )
            elif data_type == "onchip" and ONCHIP_FITTER_AVAILABLE:
                # Use on-chip fitter for LIV data (linear mW)
                logger.info("Using onchip_lorentz_fitter for on-chip LIV power data")
                fit_results = fit_and_track_onchip_sweeps(
                    spec_roi,
                    wavelength_roi,
                    **kwargs  # Pass through gaussian_filter_sigma, prominence_scaler, etc.
                )
            elif data_type == "evalsys" and EVALSYS_FITTER_AVAILABLE:
                # Use eval system fitter for pre-inverted/normalized data
                logger.info("Using evalsys_lorentz_fitter for eval system power data")
                fit_results = fit_and_track_evalsys_sweeps(
                    spec_roi,
                    wavelength_roi,
                    **kwargs  # Pass through gaussian_filter_sigma, prominence_scaler, etc.
                )
            else:
                # Use RA fitter for dBm data
                if data_type in ["linear", "onchip", "evalsys"]:
                    logger.warning(f"{data_type} fitter not available, using RA fitter (may produce poor fits)")
                
                from peak_tracking_ra import fit_and_track_sweeps
                fit_results = fit_and_track_sweeps(
                    spec_roi,
                    wavelength_roi,
                    peak_mode=peak_mode,
                    data_type=data_type,
                    **kwargs
                )

            peak_wavelengths = np.asarray(fit_results["centers"])
            
            # Check if any peaks were found
            if len(peak_wavelengths) == 0 or not np.any(np.isfinite(peak_wavelengths)):
                logger.warning("No valid peaks found with lorentz mode, falling back to dominant")
                raise ValueError("No peaks detected")
            
            peak_powers = np.asarray(fit_results.get("peak_powers", np.full_like(peak_wavelengths, np.nan)))
            
            # Store all peak traces for multi-peak analysis
            all_peak_traces = fit_results.get("all_peak_traces", [])
            fsr_stats = fit_results.get("fsr_stats", {})
            
            # Calculate avg powers AFTER successful fit (spatial average per sweep)
            for t in range(spec_roi.shape[0]):
                avg_powers.append(np.mean(spec_roi[t]))
            
            # For compatibility, continue with single peak for basic plots
            all_peaks_per_time = []
            
        except Exception as exc:
            logger.exception("Lorentz-based peak tracking failed, falling back to dominant mode: %s", exc)
            peak_mode = "dominant"
            # Reset variables to empty lists for fallback processing
            peak_wavelengths = []
            peak_powers = []
            avg_powers = []  # Also reset avg_powers!
            all_peak_traces = []
            fsr_stats = {}
            # Continue to process with dominant mode below

    if peak_mode != "lorentz" and peak_mode != "lorentz_seeded":
        # Process non-lorentz modes
        for t in range(spec_roi.shape[0]):
            spectrum = spec_roi[t]

            # Calculate average power in ROI
            avg_powers.append(np.mean(spectrum))

            if peak_mode == "dominant":
                # Simple global maximum
                peak_idx = np.argmax(spectrum)
                peak_wavelengths.append(wavelength_roi[peak_idx])
                peak_powers.append(spectrum[peak_idx])

            elif peak_mode == "nearest":
                # Find all peaks, then select nearest to target wavelength
                if target_wavelength is None:
                    raise ValueError("peak_mode='nearest' requires target_wavelength to be specified")

                # Detect all peaks
                max_power = np.max(spectrum)
                peaks, properties = find_peaks(spectrum, prominence=prominence_threshold * max_power)

                if len(peaks) > 0:
                    # Find peak nearest to target wavelength
                    peak_wls = wavelength_roi[peaks]
                    distances = np.abs(peak_wls - target_wavelength)
                    nearest_idx = np.argmin(distances)
                    selected_peak_idx = peaks[nearest_idx]

                    peak_wavelengths.append(wavelength_roi[selected_peak_idx])
                    peak_powers.append(spectrum[selected_peak_idx])
                else:
                    # Fallback to global max if no peaks detected
                    peak_idx = np.argmax(spectrum)
                    peak_wavelengths.append(wavelength_roi[peak_idx])
                    peak_powers.append(spectrum[peak_idx])
                    logger.warning(f"No peaks detected at t={t}, using global max")

            elif peak_mode == "all":
                # Detect all significant peaks
                max_power = np.max(spectrum)
                peaks, properties = find_peaks(spectrum, prominence=prominence_threshold * max_power)

                if len(peaks) > 0:
                    peak_data = {
                        'wavelengths': wavelength_roi[peaks],
                        'powers': spectrum[peaks],
                        'prominences': properties['prominences']
                    }
                    all_peaks_per_time.append(peak_data)

                    # For single-value tracking, use the most prominent peak
                    most_prominent_idx = np.argmax(properties['prominences'])
                    selected_peak_idx = peaks[most_prominent_idx]
                    peak_wavelengths.append(wavelength_roi[selected_peak_idx])
                    peak_powers.append(spectrum[selected_peak_idx])
                else:
                    # Fallback to global max
                    peak_idx = np.argmax(spectrum)
                    peak_wavelengths.append(wavelength_roi[peak_idx])
                    peak_powers.append(spectrum[peak_idx])
                    all_peaks_per_time.append({
                        'wavelengths': np.array([wavelength_roi[peak_idx]]),
                        'powers': np.array([spectrum[peak_idx]]),
                        'prominences': np.array([spectrum[peak_idx]])
                    })
            else:
                raise ValueError(f"Unknown peak_mode: {peak_mode}")
    
    peak_wavelengths = np.array(peak_wavelengths)
    peak_powers = np.array(peak_powers)
    avg_powers = np.array(avg_powers)
    ra_delta_step_nm: Optional[np.ndarray] = None
    ra_delta_cumulative_nm: Optional[np.ndarray] = None

    if peak_mode in ("lorentz", "lorentz_seeded") and len(all_peak_traces) > 0 and len(times) > 0:
        num_points = len(times)
        ra_delta_step_nm = np.full(num_points, np.nan, dtype=float)
        ra_delta_cumulative_nm = np.zeros(num_points, dtype=float)
        ra_delta_step_nm[0] = 0.0
        ra_delta_cumulative_nm[0] = 0.0
        cumulative_shift = 0.0

        for idx_time in range(1, num_points):
            step_values = []
            for trace in all_peak_traces:
                centers_arr = np.asarray(trace.get('centers', []), dtype=float)
                if centers_arr.size == 0:
                    continue
                centers_arr = centers_arr[:num_points]
                if idx_time < centers_arr.size and np.isfinite(centers_arr[idx_time]) and np.isfinite(centers_arr[idx_time - 1]):
                    step_values.append(centers_arr[idx_time] - centers_arr[idx_time - 1])

            if step_values:
                step_mean = float(np.mean(step_values))
                ra_delta_step_nm[idx_time] = step_mean
                cumulative_shift += step_mean

            ra_delta_cumulative_nm[idx_time] = cumulative_shift

        valid_step_mask = np.isfinite(ra_delta_step_nm[1:])
        if np.any(valid_step_mask):
            mean_step_pm = np.mean(ra_delta_step_nm[1:][valid_step_mask]) * 1000.0
            logger.info("RA-style drift: averaged %d step transitions (mean %.3f pm)",
                        int(np.count_nonzero(valid_step_mask)), mean_step_pm)
    
    # Calculate statistics
    # First calculate delta wavelength from initial value (for statistics file)
    initial_wavelength = peak_wavelengths[0]
    if ra_delta_cumulative_nm is not None:
        delta_wavelength_pm = ra_delta_cumulative_nm * 1000  # Convert nm to pm
    else:
        delta_wavelength_pm = (peak_wavelengths - initial_wavelength) * 1000  # Convert nm to pm
    
    # Calculate drift rate (pm/min) using linear fit
    if len(times) > 1 and len(delta_wavelength_pm) == len(times):
        finite_mask = np.isfinite(times) & np.isfinite(delta_wavelength_pm)
        if np.count_nonzero(finite_mask) >= 2:
            slope_pm_per_min, intercept = np.polyfit(times[finite_mask], delta_wavelength_pm[finite_mask], 1)
            drift_rate_pm_per_min = slope_pm_per_min
        else:
            drift_rate_pm_per_min = np.nan
    else:
        drift_rate_pm_per_min = np.nan
    
    if ra_delta_cumulative_nm is not None:
        finite_cumulative = ra_delta_cumulative_nm[np.isfinite(ra_delta_cumulative_nm)]
        overall_drift_nm = float(finite_cumulative[-1]) if finite_cumulative.size > 0 else np.nan
    else:
        overall_drift_nm = peak_wavelengths[-1] - peak_wavelengths[0]

    stats = {
        # Metadata
        'peak_mode': peak_mode,
        'target_wavelength': target_wavelength,
        'prominence_threshold': prominence_threshold,
        
        # Peak wavelength statistics
        'peak_wl_mean': np.mean(peak_wavelengths),
        'peak_wl_std': np.std(peak_wavelengths),
        'peak_wl_min': np.min(peak_wavelengths),
        'peak_wl_max': np.max(peak_wavelengths),
        'peak_wl_range': np.max(peak_wavelengths) - np.min(peak_wavelengths),
        'peak_wl_drift': overall_drift_nm,
        
        # Delta wavelength statistics (from initial value in pm)
        'initial_wavelength': initial_wavelength,
        'delta_wl_std_pm': np.std(delta_wavelength_pm),
        'delta_wl_max_abs_pm': np.max(np.abs(delta_wavelength_pm)),
        'delta_wl_final_pm': delta_wavelength_pm[-1],
        'drift_rate_pm_per_min': drift_rate_pm_per_min,
        'peak_wl_drift_pm': overall_drift_nm * 1000,
        'peak_wl_drift_direct_pm': (peak_wavelengths[-1] - peak_wavelengths[0]) * 1000,
        
        # Peak power statistics
        'peak_power_mean': np.mean(peak_powers),
        'peak_power_std': np.std(peak_powers),
        'peak_power_min': np.min(peak_powers),
        'peak_power_max': np.max(peak_powers),
        'peak_power_range': np.max(peak_powers) - np.min(peak_powers),
        'peak_power_cv': (np.std(peak_powers) / np.mean(peak_powers)) * 100,  # Coefficient of variation in %
        
        # Average power statistics
        'avg_power_mean': np.mean(avg_powers),
        'avg_power_std': np.std(avg_powers),
        'avg_power_min': np.min(avg_powers),
        'avg_power_max': np.max(avg_powers),
        'avg_power_range': np.max(avg_powers) - np.min(avg_powers),
        'avg_power_cv': (np.std(avg_powers) / np.mean(avg_powers)) * 100,  # Coefficient of variation in %
    }

    if ra_delta_step_nm is not None and ra_delta_cumulative_nm is not None:
        stats['ra_delta_step_nm'] = ra_delta_step_nm.tolist()
        stats['ra_delta_cumulative_nm'] = ra_delta_cumulative_nm.tolist()
        stats['ra_delta_step_pm'] = (ra_delta_step_nm * 1000).tolist()
        stats['ra_delta_cumulative_pm'] = (ra_delta_cumulative_nm * 1000).tolist()
    
    # For "all" mode, add statistics about number of peaks detected
    if peak_mode == "all" and len(all_peaks_per_time) > 0:
        num_peaks_per_time = [len(p['wavelengths']) for p in all_peaks_per_time]
        stats['num_peaks_mean'] = np.mean(num_peaks_per_time)
        stats['num_peaks_std'] = np.std(num_peaks_per_time)
        stats['num_peaks_min'] = np.min(num_peaks_per_time)
        stats['num_peaks_max'] = np.max(num_peaks_per_time)
    
    # For "lorentz" mode with multi-peak tracking, add RA-style statistics
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals() and len(all_peak_traces) > 0:
        stats['num_tracked_peaks'] = len(all_peak_traces)
        if 'fsr_stats' in locals() and fsr_stats.get('mean'):
            stats['fsr_mean_pm'] = fsr_stats['mean'] * 1000  # Convert to pm
            stats['fsr_std_pm'] = fsr_stats['std'] * 1000
        
        # Compute per-peak statistics
        for idx, trace in enumerate(all_peak_traces):
            # Trim trace arrays to match time dimension
            centers = trace['centers'][:len(times)]
            Q_factors = trace['Q_factors'][:len(times)]
            R_squared = trace['R_squared'][:len(times)]
            FWHM = trace['FWHM'][:len(times)]
            
            valid_mask = np.isfinite(centers)
            if not np.any(valid_mask):
                continue
            
            valid_centers = centers[valid_mask]
            valid_times = times[valid_mask]
            
            # Drift rate for this peak
            if len(valid_times) > 1:
                delta_wl_trace = (valid_centers - valid_centers[0]) * 1000  # pm
                slope_trace, _ = np.polyfit(valid_times, delta_wl_trace, 1)
                trace_drift_rate = slope_trace
            else:
                trace_drift_rate = np.nan
            
            stats[f'peak{idx+1}_mean_wl_nm'] = np.nanmean(centers)
            stats[f'peak{idx+1}_drift_rate_pm_per_min'] = trace_drift_rate
            stats[f'peak{idx+1}_mean_Q'] = np.nanmean(Q_factors)
            stats[f'peak{idx+1}_mean_R2'] = np.nanmean(R_squared)
            stats[f'peak{idx+1}_mean_FWHM_pm'] = np.nanmean(FWHM) * 1000
    
    
    # Save statistics to text file
    stats_file = os.path.join(output_dir, f"{prefix}_fluctuation_statistics.txt")
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write(f"FLUCTUATION ANALYSIS STATISTICS\n")
        f.write(f"{'='*60}\n\n")
        
        f.write(f"ANALYSIS SETTINGS:\n")
        f.write(f"  Peak Detection Mode: {peak_mode}\n")
        if peak_mode == "nearest":
            f.write(f"  Target Wavelength:   {target_wavelength:.3f} nm\n")
        if peak_mode in ["nearest", "all"]:
            f.write(f"  Prominence Threshold: {prominence_threshold*100:.1f}% of max power\n")
        if wl_roi is not None:
            f.write(f"  Analysis Region:     {wl_roi[0]:.3f} - {wl_roi[1]:.3f} nm\n")
        f.write("\n")
        
        if peak_mode == "all" and 'num_peaks_mean' in stats:
            f.write(f"MULTI-PEAK DETECTION SUMMARY:\n")
            f.write(f"  Average # of peaks:  {stats['num_peaks_mean']:.1f}\n")
            f.write(f"  Std Dev # of peaks:  {stats['num_peaks_std']:.2f}\n")
            f.write(f"  Min # of peaks:      {int(stats['num_peaks_min'])}\n")
            f.write(f"  Max # of peaks:      {int(stats['num_peaks_max'])}\n")
            f.write(f"  (Statistics below are for most prominent peak at each time)\n\n")
        
        f.write(f"PEAK WAVELENGTH STATISTICS:\n")
        f.write(f"  Mean:              {stats['peak_wl_mean']:.6f} nm\n")
        f.write(f"  Std Deviation:     {stats['peak_wl_std']:.6f} nm\n")
        f.write(f"  Min:               {stats['peak_wl_min']:.6f} nm\n")
        f.write(f"  Max:               {stats['peak_wl_max']:.6f} nm\n")
        f.write(f"  Range:             {stats['peak_wl_range']:.6f} nm\n")
        f.write(f"  Total Drift:       {stats['peak_wl_drift']:.6f} nm\n")
        f.write(f"  Direct Δλ (final-initial): {(stats['peak_wl_drift_direct_pm']/1000):.6f} nm\n\n")

        f.write(f"WAVELENGTH DRIFT FROM INITIAL (Δλ):\n")
        f.write(f"  Initial λ:         {stats['initial_wavelength']:.6f} nm\n")
        f.write(f"  Std Deviation:     {stats['delta_wl_std_pm']:.3f} pm\n")
        f.write(f"  Max |Δλ|:          {stats['delta_wl_max_abs_pm']:.3f} pm\n")
        f.write(f"  Final Δλ:          {stats['delta_wl_final_pm']:.3f} pm\n")
        if not np.isnan(stats['drift_rate_pm_per_min']):
            f.write(f"  Drift Rate:        {stats['drift_rate_pm_per_min']:.3f} pm/min\n")
        if 'ra_delta_step_pm' in stats:
            ra_steps = np.array(stats['ra_delta_step_pm'][1:], dtype=float)
            ra_steps = ra_steps[np.isfinite(ra_steps)]
            if ra_steps.size > 0:
                f.write(f"  Avg Δλ per sweep:  {np.mean(ra_steps):.3f} pm\n")
                f.write(f"  Std Δλ per sweep:  {np.std(ra_steps):.3f} pm\n")
        f.write(f"  (Note: Positive = red shift, Negative = blue shift)\n\n")
        
        # Multi-peak tracking summary (RA-style)
        if 'num_tracked_peaks' in stats and stats['num_tracked_peaks'] > 0:
            f.write(f"MULTI-PEAK TRACKING SUMMARY (Lorentzian Fits):\n")
            f.write(f"  Number of Peaks Tracked: {stats['num_tracked_peaks']}\n")
            if 'fsr_mean_pm' in stats:
                f.write(f"  FSR:                     {stats['fsr_mean_pm']:.2f} ± {stats['fsr_std_pm']:.2f} pm\n")
            f.write(f"\n")
            
            for idx in range(stats['num_tracked_peaks']):
                if f'peak{idx+1}_mean_wl_nm' in stats:
                    f.write(f"  Peak {idx+1}:\n")
                    f.write(f"    Mean Wavelength:  {stats[f'peak{idx+1}_mean_wl_nm']:.6f} nm\n")
                    if not np.isnan(stats.get(f'peak{idx+1}_drift_rate_pm_per_min', np.nan)):
                        f.write(f"    Drift Rate:       {stats[f'peak{idx+1}_drift_rate_pm_per_min']:.3f} pm/min\n")
                    f.write(f"    Mean Q-factor:    {stats[f'peak{idx+1}_mean_Q']:.0f}\n")
                    f.write(f"    Mean R²:          {stats[f'peak{idx+1}_mean_R2']:.3f}\n")
                    f.write(f"    Mean FWHM:        {stats[f'peak{idx+1}_mean_FWHM_pm']:.2f} pm\n")
            f.write(f"\n")
        
        f.write(f"PEAK POWER STATISTICS:\n")
        f.write(f"  Mean:              {stats['peak_power_mean']:.6f} mW\n")
        f.write(f"  Std Deviation:     {stats['peak_power_std']:.6f} mW\n")
        f.write(f"  Min:               {stats['peak_power_min']:.6f} mW\n")
        f.write(f"  Max:               {stats['peak_power_max']:.6f} mW\n")
        f.write(f"  Range:             {stats['peak_power_range']:.6f} mW\n")
        f.write(f"  CV (Coeff. Var.):  {stats['peak_power_cv']:.3f} %\n\n")
        
        f.write(f"AVERAGE POWER STATISTICS:\n")
        f.write(f"  Mean:              {stats['avg_power_mean']:.6f} mW\n")
        f.write(f"  Std Deviation:     {stats['avg_power_std']:.6f} mW\n")
        f.write(f"  Min:               {stats['avg_power_min']:.6f} mW\n")
        f.write(f"  Max:               {stats['avg_power_max']:.6f} mW\n")
        f.write(f"  Range:             {stats['avg_power_range']:.6f} mW\n")
        f.write(f"  CV (Coeff. Var.):  {stats['avg_power_cv']:.3f} %\n")
    
    logger.info(f"Saved statistics to {stats_file}")
    
    # Determine mode description for labels
    if peak_mode == "dominant":
        mode_desc = "Dominant Peak"
    elif peak_mode == "nearest" and target_wavelength is not None:
        mode_desc = f"Peak near {target_wavelength:.2f} nm"
    elif peak_mode == "all":
        mode_desc = "Most Prominent Peak"
    else:
        mode_desc = peak_mode
    
    # Create figure for wavelength drift (with optional temperature subplot)
    has_temp = temperature_data is not None and len(temperature_data) == len(times)
    if has_temp:
        fig_wl, axes_wl = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        ax_wl = axes_wl[0]
        ax_temp = axes_wl[1]
    else:
        fig_wl, ax_wl = plt.subplots(1, 1, figsize=(12, 4))
    
    # Plot wavelength drift (no label for single peak, will show in legend only for multi-peak)
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals() and len(all_peak_traces) > 1:
        # Multi-peak mode: plot all peaks with labels
        colors = plt.cm.tab10(np.linspace(0, 1, len(all_peak_traces)))
        for idx, trace in enumerate(all_peak_traces):
            # Trim trace to match time dimension
            centers = trace['centers'][:len(times)]
            valid_mask = np.isfinite(centers)
            if np.any(valid_mask):
                # Get drift rate for this peak
                drift_rate = stats.get(f'peak{idx+1}_drift_rate_pm_per_min', np.nan)
                if not np.isnan(drift_rate):
                    label = f"Peak {idx+1}: {drift_rate:+.2f} pm/min"
                else:
                    label = f"Peak {idx+1}"
                ax_wl.plot(times[valid_mask], centers[valid_mask], 
                        'o-', linewidth=1.2, markersize=3, color=colors[idx], alpha=0.6,
                        label=label)
        ax_wl.legend(fontsize=PLOT_FONT_LEGEND-1, ncol=2)
    else:
        # Single peak mode: no label (clean plot)
        ax_wl.plot(times, peak_wavelengths, 'o-', linewidth=1.5, markersize=4, color='darkblue', alpha=0.7)
    
    # If "all" mode, overlay all detected peaks
    if peak_mode == "all" and len(all_peaks_per_time) > 0:
        for t_idx, peak_data in enumerate(all_peaks_per_time):
            if len(peak_data['wavelengths']) > 1:  # Only show if there are additional peaks
                # Plot other peaks (not the tracked one) as small dots
                other_peaks = peak_data['wavelengths']
                ax_wl.plot([times[t_idx]] * len(other_peaks), other_peaks, 'x', 
                        markersize=3, color='gray', alpha=0.3)
    
    # Show mean line and std band but without labels (visual reference only)
    ax_wl.axhline(stats['peak_wl_mean'], color='gray', linestyle='--', linewidth=1, alpha=0.4)
    ax_wl.fill_between(times, 
                      stats['peak_wl_mean'] - stats['peak_wl_std'], 
                      stats['peak_wl_mean'] + stats['peak_wl_std'],
                      alpha=0.1, color='gray')
    if has_temp:
        ax_wl.set_ylabel("Peak Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
    else:
        ax_wl.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_wl.set_ylabel("Peak Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
    
    # Build title with drift rate info
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals() and len(all_peak_traces) > 1:
        title_str = f"Peak Wavelength vs Time ({len(all_peak_traces)} peaks tracked)\n"
        title_str += f"Span: {stats['peak_wl_range']*1000:.1f} pm, Net Shift: {stats['peak_wl_drift']*1000:+.1f} pm"
    else:
        drift_rate = stats.get('drift_rate_pm_per_min', np.nan)
        if not np.isnan(drift_rate):
            title_str = f"Peak Wavelength vs Time\n"
            title_str += f"Span: {stats['peak_wl_range']*1000:.1f} pm, Net Shift: {stats['peak_wl_drift']*1000:+.1f} pm, Rate: {drift_rate:+.2f} pm/min"
        else:
            title_str = f"Peak Wavelength vs Time\n"
            title_str += f"Span: {stats['peak_wl_range']*1000:.1f} pm, Net Shift: {stats['peak_wl_drift']*1000:+.1f} pm"
    
    ax_wl.set_title(title_str, fontsize=PLOT_FONT_TITLE)
    ax_wl.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    ax_wl.grid(True, alpha=0.3, linestyle='--')
    
    # Plot temperature if available
    if has_temp:
        temp_mean = np.mean(temperature_data)
        temp_std = np.std(temperature_data)
        temp_range = np.max(temperature_data) - np.min(temperature_data)
        
        ax_temp.plot(times, temperature_data, 'o-', linewidth=1.5, markersize=4, color='darkred', alpha=0.7)
        ax_temp.axhline(temp_mean, color='blue', linestyle='--', linewidth=1.5, 
                    label=f"Mean: {temp_mean:.2f} °C", alpha=0.7)
        ax_temp.fill_between(times, 
                          temp_mean - temp_std, 
                          temp_mean + temp_std,
                          alpha=0.2, color='blue', label=f"±1σ: {temp_std:.2f} °C")
        ax_temp.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_temp.set_ylabel("Temperature (°C)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_temp.set_title(f"Temperature Fluctuations\nRange: {temp_range:.2f} °C", 
                      fontsize=PLOT_FONT_TITLE)
        ax_temp.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
        ax_temp.grid(True, alpha=0.3, linestyle='--')
        ax_temp.legend(fontsize=PLOT_FONT_LEGEND)
    
    # Save wavelength (+ temperature) figure
    fig_wl.tight_layout()
    out_png_wl = os.path.join(output_dir, f"{prefix}_wavelength_analysis.png")
    fig_wl.savefig(out_png_wl, dpi=300)
    plt.close(fig_wl)
    logger.info(f"Saved wavelength analysis plot to {out_png_wl}")
    
    # Create separate figure for power fluctuations (2 subplots)
    fig_power, axes_power = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Plot peak power vs time
    ax_peak = axes_power[0]
    
    # Determine label based on peak mode
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals() and len(all_peak_traces) > 1:
        peak_label = f'Primary Peak (of {len(all_peak_traces)} tracked)'
    elif peak_mode == "dominant":
        peak_label = 'Dominant Peak'
    elif peak_mode == "nearest":
        peak_label = f'Nearest to {target_wavelength:.3f} nm'
    elif peak_mode == "all":
        peak_label = 'Most Prominent Peak'
    else:
        peak_label = 'Tracked Peak'
    
    ax_peak.plot(times, peak_powers, 'o-', linewidth=1.5, markersize=4, color='darkgreen', alpha=0.7,
             label=peak_label)
    
    # If Lorentz multi-peak mode, overlay all tracked peak powers
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals() and len(all_peak_traces) > 1:
        colors = plt.cm.tab10(np.linspace(0, 1, len(all_peak_traces)))
        for idx, trace in enumerate(all_peak_traces):
            powers = trace.get('powers', trace.get('peak_powers', []))[:len(times)]
            valid_mask = np.isfinite(powers)
            if np.any(valid_mask):
                ax_peak.plot(times[valid_mask], powers[valid_mask], 'o-', linewidth=1, markersize=3, 
                        color=colors[idx], alpha=0.5, label=f'Peak {idx+1}')
    
    # If "all" mode, overlay all detected peak powers
    elif peak_mode == "all" and len(all_peaks_per_time) > 0:
        for t_idx, peak_data in enumerate(all_peaks_per_time):
            if len(peak_data['powers']) > 1:  # Only show if there are additional peaks
                other_powers = peak_data['powers']
                ax_peak.plot([times[t_idx]] * len(other_powers), other_powers, 'x', 
                        markersize=3, color='gray', alpha=0.3)
    
    ax_peak.axhline(stats['peak_power_mean'], color='red', linestyle='--', linewidth=1.5, 
                label=f"Mean: {stats['peak_power_mean']:.4f} mW", alpha=0.7)
    ax_peak.fill_between(times, 
                      stats['peak_power_mean'] - stats['peak_power_std'], 
                      stats['peak_power_mean'] + stats['peak_power_std'],
                      alpha=0.2, color='red', label=f"±1σ: {stats['peak_power_std']:.4f} mW")
    ax_peak.set_ylabel("Peak Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax_peak.set_title(f"Peak Power Fluctuations\nRange: {stats['peak_power_range']:.4f} mW, CV: {stats['peak_power_cv']:.2f}%", 
                  fontsize=PLOT_FONT_TITLE)
    ax_peak.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    ax_peak.grid(True, alpha=0.3, linestyle='--')
    ax_peak.legend(fontsize=PLOT_FONT_LEGEND)
    
    # Plot average power vs time
    ax_avg = axes_power[1]
    ax_avg.plot(times, avg_powers, 'o-', linewidth=1.5, markersize=4, color='darkorange', alpha=0.7)
    ax_avg.axhline(stats['avg_power_mean'], color='red', linestyle='--', linewidth=1.5, 
                label=f"Mean: {stats['avg_power_mean']:.4f} mW", alpha=0.7)
    ax_avg.fill_between(times, 
                      stats['avg_power_mean'] - stats['avg_power_std'], 
                      stats['avg_power_mean'] + stats['avg_power_std'],
                      alpha=0.2, color='red', label=f"±1σ: {stats['avg_power_std']:.4f} mW")
    ax_avg.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax_avg.set_ylabel("Average Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax_avg.set_title(f"Average Power Fluctuations\nRange: {stats['avg_power_range']:.4f} mW, CV: {stats['avg_power_cv']:.2f}%", 
                  fontsize=PLOT_FONT_TITLE)
    ax_avg.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    ax_avg.grid(True, alpha=0.3, linestyle='--')
    ax_avg.legend(fontsize=PLOT_FONT_LEGEND)
    
    fig_power.tight_layout()
    
    # Save power figure
    out_png_power = os.path.join(output_dir, f"{prefix}_power_analysis.png")
    fig_power.savefig(out_png_power, dpi=300)
    plt.close(fig_power)
    logger.info(f"Saved power analysis plot to {out_png_power}")
    
    # Create additional plot: Delta wavelength (pm) vs time
    # Use pre-calculated values from stats
    initial_wavelength = stats['initial_wavelength']
    if 'ra_delta_cumulative_pm' in stats:
        delta_wavelength_pm = np.array(stats['ra_delta_cumulative_pm'], dtype=float)
    else:
        delta_wavelength_pm = (peak_wavelengths - initial_wavelength) * 1000  # Convert nm to pm
    delta_wl_std = stats['delta_wl_std_pm']
    delta_wl_max = stats['delta_wl_max_abs_pm']
    
    # Create delta wavelength plot
    fig_delta, ax_delta = plt.subplots(figsize=(12, 6))
    
    ax_delta.plot(times, delta_wavelength_pm, 'o-', linewidth=1.5, markersize=4, 
                  color='darkviolet', alpha=0.7, label='Wavelength Drift')
    ax_delta.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax_delta.fill_between(times, -delta_wl_std, delta_wl_std,
                          alpha=0.2, color='red', label=f'±1σ: {delta_wl_std:.2f} pm')
    
    # If "all" mode, overlay all detected peaks
    if peak_mode == "all" and len(all_peaks_per_time) > 0:
        for t_idx, peak_data in enumerate(all_peaks_per_time):
            if len(peak_data['wavelengths']) > 1:
                # Calculate delta for all peaks at this time
                other_deltas = (peak_data['wavelengths'] - initial_wavelength) * 1000
                ax_delta.plot([times[t_idx]] * len(other_deltas), other_deltas, 'x', 
                            markersize=3, color='gray', alpha=0.3)
    
    ax_delta.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax_delta.set_ylabel("Δλ from initial (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
    
    if peak_mode == "dominant":
        mode_desc = "Dominant Peak"
    elif peak_mode == "nearest" and target_wavelength is not None:
        mode_desc = f"Peak near {target_wavelength:.2f} nm"
    elif peak_mode == "all":
        mode_desc = "Most Prominent Peak"
    else:
        mode_desc = peak_mode
    
    drift_caption = "avg Δλ across matched peaks" if 'ra_delta_cumulative_pm' in stats else "single-trace Δλ"
    ax_delta.set_title(f"Wavelength Drift from Initial Value ({mode_desc}, {drift_caption})\n" + 
                      f"Initial λ: {initial_wavelength:.6f} nm, Std: {delta_wl_std:.2f} pm, Max |Δλ|: {delta_wl_max:.2f} pm", 
                      fontsize=PLOT_FONT_TITLE)
    ax_delta.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    ax_delta.grid(True, alpha=0.3, linestyle='--')
    ax_delta.legend(fontsize=PLOT_FONT_LEGEND)
    
    fig_delta.tight_layout()
    
    # Save delta wavelength figure
    out_delta_png = os.path.join(output_dir, f"{prefix}_wavelength_drift_pm.png")
    fig_delta.savefig(out_delta_png, dpi=300)
    plt.close(fig_delta)
    logger.info(f"Saved wavelength drift (pm) plot to {out_delta_png}")
    
    # Create multi-peak collated offset plot (RA-style) if lorentz mode
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals() and len(all_peak_traces) > 0:
        fig_collated, ax_collated = plt.subplots(figsize=(12, 6))
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(all_peak_traces)))
        
        for idx, trace in enumerate(all_peak_traces):
            # Trim trace to match time dimension
            centers = trace['centers'][:len(times)]
            valid_mask = np.isfinite(centers)
            if np.any(valid_mask):
                # Calculate offset from initial wavelength
                initial_wl = centers[valid_mask][0]
                offset_pm = (centers - initial_wl) * 1000  # nm to pm
                
                ax_collated.plot(times[valid_mask], offset_pm[valid_mask], 
                               'o-', linewidth=1.5, markersize=3, color=colors[idx], alpha=0.7,
                               label=f"Peak {idx+1}: λ₀={initial_wl:.4f} nm")
        
        ax_collated.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
        ax_collated.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_collated.set_ylabel("Wavelength Shift (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_collated.set_title(f"Multi-Peak Wavelength Drift (Lorentzian Fit)\n{len(all_peak_traces)} peaks tracked", 
                             fontsize=PLOT_FONT_TITLE)
        ax_collated.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
        ax_collated.grid(True, alpha=0.3, linestyle='--')
        ax_collated.legend(fontsize=PLOT_FONT_LEGEND-1, ncol=2)
        fig_collated.tight_layout()
        
        out_collated_png = os.path.join(output_dir, f"{prefix}_multi_peak_collated.png")
        fig_collated.savefig(out_collated_png, dpi=300)
        plt.close(fig_collated)
        logger.info(f"Saved multi-peak collated offset plot to {out_collated_png}")

    
    # Calculate FSR, ER, and Q statistics for multi-peak mode (RA-style analysis)
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals() and len(all_peak_traces) > 1:
        try:
            # Calculate FSR (Free Spectral Range) = spacing between adjacent peaks
            # For each time point, calculate FSR from all valid peaks
            fsr_vs_time = []
            er_vs_time_per_peak = {f'peak{i+1}': [] for i in range(len(all_peak_traces))}
            q_vs_time_per_peak = {f'peak{i+1}': [] for i in range(len(all_peak_traces))}
            
            for t_idx in range(len(times)):
                # Collect wavelengths from all peaks at this time
                wls_at_t = []
                for trace in all_peak_traces:
                    if t_idx < len(trace['centers']):
                        wl = trace['centers'][t_idx]
                        if np.isfinite(wl):
                            wls_at_t.append(wl)
                
                # Calculate FSR as mean spacing between adjacent peaks
                if len(wls_at_t) >= 2:
                    wls_sorted = np.sort(wls_at_t)
                    spacings = np.diff(wls_sorted)
                    fsr_vs_time.append(np.mean(spacings))
                else:
                    fsr_vs_time.append(np.nan)
                
                # Collect ER and Q for each peak
                for idx, trace in enumerate(all_peak_traces):
                    peak_key = f'peak{idx+1}'
                    if t_idx < len(trace.get('Q_factors', [])):
                        q_vs_time_per_peak[peak_key].append(trace['Q_factors'][t_idx])
                    else:
                        q_vs_time_per_peak[peak_key].append(np.nan)
                    
                    # Calculate ER from spectrum if available (extinction ratio: peak power / baseline power)
                    # For now, use placeholder or skip ER calculation for benchtop data
                    # RA calculates ER from the fitted parameters, but benchtop fitter doesn't have this yet
                    er_vs_time_per_peak[peak_key].append(np.nan)
            
            fsr_array = np.array(fsr_vs_time)
            valid_fsr = fsr_array[np.isfinite(fsr_array)]
            
            if len(valid_fsr) > 0:
                fsr_stats = {
                    'mean': np.mean(valid_fsr),
                    'std': np.std(valid_fsr),
                    'min': np.min(valid_fsr),
                    'max': np.max(valid_fsr)
                }
                logger.info(f"FSR statistics: mean={fsr_stats['mean']:.4f} nm, std={fsr_stats['std']:.4f} nm")
                
                # Plot FSR/ER/Q vs time (RA-style)
                fig_metrics, axes_metrics = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
                
                # Plot 1: FSR vs time
                ax_fsr = axes_metrics[0]
                ax_fsr.plot(times, fsr_array, 'o-', linewidth=1.5, markersize=4, color='purple', alpha=0.7)
                ax_fsr.axhline(fsr_stats['mean'], color='red', linestyle='--', linewidth=1.5,
                              label=f"Mean: {fsr_stats['mean']:.4f} nm", alpha=0.7)
                ax_fsr.fill_between(times,
                                    fsr_stats['mean'] - fsr_stats['std'],
                                    fsr_stats['mean'] + fsr_stats['std'],
                                    alpha=0.2, color='red', label=f"±1σ: {fsr_stats['std']:.4f} nm")
                ax_fsr.set_ylabel("FSR (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
                ax_fsr.set_title(f"Free Spectral Range\nMean: {fsr_stats['mean']:.4f} nm, Range: {fsr_stats['max']-fsr_stats['min']:.4f} nm",
                                fontsize=PLOT_FONT_TITLE)
                ax_fsr.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
                ax_fsr.grid(True, alpha=0.3, linestyle='--')
                ax_fsr.legend(fontsize=PLOT_FONT_LEGEND)
                
                # Plot 2: Q-factor vs time (all peaks)
                ax_q = axes_metrics[1]
                colors_q = plt.cm.tab10(np.linspace(0, 1, len(all_peak_traces)))
                for idx, (peak_key, q_values) in enumerate(q_vs_time_per_peak.items()):
                    q_arr = np.array(q_values)
                    valid_mask = np.isfinite(q_arr)
                    if np.any(valid_mask):
                        ax_q.plot(times[valid_mask], q_arr[valid_mask], 'o-', linewidth=1, markersize=3,
                                 color=colors_q[idx], alpha=0.6, label=peak_key)
                ax_q.set_ylabel("Q-factor", fontsize=PLOT_FONT_AXIS_LABEL)
                ax_q.set_title("Q-factor vs Time (All Peaks)", fontsize=PLOT_FONT_TITLE)
                ax_q.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
                ax_q.grid(True, alpha=0.3, linestyle='--')
                ax_q.legend(fontsize=PLOT_FONT_LEGEND-2, ncol=2)
                
                # Plot 3: FWHM vs time (all peaks) - use FWHM as proxy since ER not available for benchtop
                ax_fwhm = axes_metrics[2]
                colors_fwhm = plt.cm.tab10(np.linspace(0, 1, len(all_peak_traces)))
                for idx, trace in enumerate(all_peak_traces):
                    fwhm_arr = np.array(trace.get('FWHM', []))[:len(times)]
                    valid_mask = np.isfinite(fwhm_arr)
                    if np.any(valid_mask):
                        ax_fwhm.plot(times[valid_mask], fwhm_arr[valid_mask], 'o-', linewidth=1, markersize=3,
                                    color=colors_fwhm[idx], alpha=0.6, label=f'Peak {idx+1}')
                ax_fwhm.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
                ax_fwhm.set_ylabel("FWHM (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
                ax_fwhm.set_title("Linewidth (FWHM) vs Time (All Peaks)", fontsize=PLOT_FONT_TITLE)
                ax_fwhm.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
                ax_fwhm.grid(True, alpha=0.3, linestyle='--')
                ax_fwhm.legend(fontsize=PLOT_FONT_LEGEND-2, ncol=2)
                
                fig_metrics.tight_layout()
                out_png_metrics = os.path.join(output_dir, f"{prefix}_fsr_q_fwhm_analysis.png")
                fig_metrics.savefig(out_png_metrics, dpi=300)
                plt.close(fig_metrics)
                logger.info(f"Saved FSR/Q/FWHM analysis plot to {out_png_metrics}")
            
        except Exception as e:
            logger.warning(f"Failed to calculate FSR/Q statistics: {e}")
            fsr_stats = {}
    
    # Save multi-peak data to MAT files (RA-style) if using lorentz mode
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals() and len(all_peak_traces) > 0:
        try:
            import scipy.io
            
            # Create RA_result subfolder
            ra_result_dir = os.path.join(output_dir, "RA_result")
            os.makedirs(ra_result_dir, exist_ok=True)
            
            # Save peak_shift.mat (wavelength traces vs time)
            peak_shift_dict = {'t_array': times}
            for idx, trace in enumerate(all_peak_traces):
                # Trim trace to match time dimension
                centers = trace['centers'][:len(times)]
                # Save absolute wavelengths (following traces)
                peak_shift_dict[f'peak{idx+1}_wl_trace'] = centers
                # Also save delta from initial (like RA does with "offset")
                valid_mask = np.isfinite(centers)
                if np.any(valid_mask):
                    initial_wl = centers[valid_mask][0]
                    peak_shift_dict[f'peak{idx+1}_wl_shift_nm'] = centers - initial_wl
            
            # Save RA-style aggregate drift arrays for cross-platform comparisons
            if 'ra_delta_cumulative_nm' in stats:
                peak_shift_dict['ra_delta_cumulative_nm'] = np.asarray(stats['ra_delta_cumulative_nm'], dtype=float)
                peak_shift_dict['ra_delta_cumulative_pm'] = np.asarray(stats['ra_delta_cumulative_pm'], dtype=float)
            if 'ra_delta_step_nm' in stats:
                peak_shift_dict['ra_delta_step_nm'] = np.asarray(stats['ra_delta_step_nm'], dtype=float)
                peak_shift_dict['ra_delta_step_pm'] = np.asarray(stats['ra_delta_step_pm'], dtype=float)

            scipy.io.savemat(os.path.join(ra_result_dir, f'{prefix}_peak_shift.mat'), peak_shift_dict)
            
            # Save fsr_er_q.mat (quality metrics per peak)
            fsr_er_q_dict = {'t_array': times}
            for idx, trace in enumerate(all_peak_traces):
                # Trim all trace arrays to match time dimension
                fsr_er_q_dict[f'peak{idx+1}_Q'] = trace['Q_factors'][:len(times)]
                fsr_er_q_dict[f'peak{idx+1}_FWHM_nm'] = trace['FWHM'][:len(times)]
                fsr_er_q_dict[f'peak{idx+1}_R2'] = trace['R_squared'][:len(times)]
                fsr_er_q_dict[f'peak{idx+1}_wavelength_nm'] = trace['centers'][:len(times)]
                fsr_er_q_dict[f'peak{idx+1}_power'] = trace.get('powers', trace.get('peak_powers', np.full(len(times), np.nan)))[:len(times)]
            
            # Save FSR data if calculated
            if 'fsr_stats' in locals() and fsr_stats.get('mean'):
                fsr_er_q_dict['FSR_mean_nm'] = fsr_stats['mean']
                fsr_er_q_dict['FSR_std_nm'] = fsr_stats['std']
                if 'fsr_array' in locals():
                    fsr_er_q_dict['FSR_vs_time'] = fsr_array

            scipy.io.savemat(os.path.join(ra_result_dir, f'{prefix}_fsr_er_q.mat'), fsr_er_q_dict)
            
            logger.info(f"Saved multi-peak RA-style MAT files to {ra_result_dir}")
            
        except Exception as e:
            logger.warning(f"Failed to save multi-peak MAT files: {e}")
    
    # Return stats and all_peak_traces for optional overlay plotting
    if peak_mode in ("lorentz", "lorentz_seeded") and 'all_peak_traces' in locals():
        return stats, all_peak_traces
    else:
        return stats, None


def find_csv_files_recursive(parent: str) -> List[str]:
    """Return list of CSV files under parent directory (recursively)."""
    p = Path(parent)
    files = [str(fp) for fp in p.rglob("*.csv")]
    return sorted(files)


def parse_timestamp_from_filename(fname: str) -> Optional[float]:
    """Try to parse a timestamp from the filename using common patterns.

    Returns epoch seconds or None.
    """
    base = Path(fname).stem
    # common ISO-ish patterns: 2025-10-30_23-50-59 or 20251030_235059
    patterns = [r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})[T_ ]?(\d{2})[-_:]?(\d{2})[-_:]?(\d{2})",
                r"(\d{4})(\d{2})(\d{2})[_-]?(\d{2})(\d{2})(\d{2})"]
    for pat in patterns:
        m = re.search(pat, base)
        if m:
            try:
                parts = [int(x) for x in m.groups()]
                dt = datetime(parts[0], parts[1], parts[2], parts[3], parts[4], parts[5])
                return dt.timestamp()
            except Exception:
                continue
    return None


def get_file_timestamp(path: str) -> float:
    """Get file timestamp in epoch seconds: prefer parsed filename, fallback to mtime."""
    t = parse_timestamp_from_filename(path)
    if t is not None:
        return t
    try:
        return os.path.getmtime(path)
    except Exception:
        return datetime.now().timestamp()


def process_benchtop_folder(parent: str, output_dir: str, wl_min: Optional[float], wl_max: Optional[float], save_mat: bool = True, mat_save_path: Optional[str] = None):
    """Process a benchtop folder: read CSVs, build spectrogram, save mat and PNG.
    
    Args:
        parent: Parent directory to search for CSV files
        output_dir: Directory to save PNG outputs
        wl_min: Minimum wavelength to include (optional filter)
        wl_max: Maximum wavelength to include (optional filter)
        save_mat: Whether to save a .mat file
        mat_save_path: Custom path to save .mat file (if None, uses default in output_dir)
    """
    if extract_wavelength_and_ch3 is None:
        logger.error("Required helper 'sweep_benchtop_continuous.extract_wavelength_and_ch3' could not be imported from repo.")
        return

    files = find_csv_files_recursive(parent)
    if not files:
        logger.error(f"No CSV files found under {parent}")
        return

    entries: List[Dict] = []
    for f in files:
        wl, ch3 = extract_wavelength_and_ch3(f)
        if wl is None or ch3 is None:
            logger.debug(f"Skipping {f}: couldn't extract wavelength/ch3")
            continue
        ts = get_file_timestamp(f)
        
        # Extract temperature
        temperature = extract_temperature_from_csv(f)
        if temperature is not None:
            logger.debug(f"Found temperature data in {os.path.basename(f)}: {len(temperature)} points")
        
        entries.append({
            "file": f, 
            "wavelength": wl.astype(float), 
            "power": ch3.astype(float), 
            "temperature": temperature,
            "ts": ts
        })

    if not entries:
        logger.error("No valid CSV traces with wavelength & channel data found")
        return

    # sort by timestamp
    entries.sort(key=lambda e: e["ts"])
    times = np.array([e["ts"] for e in entries])
    rel_seconds = times - times[0]
    rel_minutes = rel_seconds / 60.0

    # choose reference wavelength (from first entry)
    ref_wl = entries[0]["wavelength"]
    # optionally crop to wl_min/wl_max
    wl_mask = np.ones_like(ref_wl, dtype=bool)
    if wl_min is not None or wl_max is not None:
        if wl_min is None:
            wl_min = ref_wl.min()
        if wl_max is None:
            wl_max = ref_wl.max()
        wl_mask = (ref_wl >= wl_min) & (ref_wl <= wl_max)
        ref_wl = ref_wl[wl_mask]

    spec_rows = []
    fnames = []
    for e in entries:
        wl = e["wavelength"]
        power = e["power"]
        # interpolate onto ref_wl
        try:
            p_interp = np.interp(ref_wl, wl, power)
        except Exception:
            # if interpolation fails, try simple padding/truncation
            min_len = min(len(ref_wl), len(power))
            p_interp = np.zeros_like(ref_wl)
            p_interp[:min_len] = power[:min_len]
        spec_rows.append(p_interp)
        fnames.append(e["file"])

    spec = np.vstack(spec_rows)  # shape (time, wavelength)

    # Save .mat for later reuse
    if save_mat:
        # Use custom path if provided, otherwise default to output_dir
        if mat_save_path:
            mat_path = mat_save_path
        else:
            mat_path = os.path.join(output_dir, "benchtop_spectrogram.mat")
        
        try:
            savemat(mat_path, {"powers": spec, "wavelength": ref_wl, "times": times, "rel_seconds": rel_seconds, "rel_minutes": rel_minutes, "filenames": fnames})
            logger.info(f"Saved benchtop .mat to {mat_path}")
        except Exception as exc:
            logger.error(f"Failed to save .mat: {exc}")

    # Plot spectrogram with time in minutes on x-axis
    out_png = os.path.join(output_dir, "benchtop_spectrogram.png")
    # Use a simple plotting routine that maps x-axis to minutes
    fig, ax = plt.subplots(figsize=(10, 6))
    extent = [rel_minutes.min(), rel_minutes.max(), ref_wl[0], ref_wl[-1]]
    im = ax.imshow(spec.T, aspect="auto", origin="lower", cmap="inferno", extent=extent)
    ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_ylabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_title("Benchtop spectrogram", fontsize=PLOT_FONT_TITLE)
    ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    # Show full numeric wavelength ticks (no offset/scientific notation)
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter(useOffset=False))
    ax.ticklabel_format(style='plain', axis='y')
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL)
    cbar.ax.tick_params(labelsize=PLOT_FONT_AXIS_TICKS)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    logger.info(f"Saved benchtop spectrogram to {out_png}")
    
    # Extract temperature data for quantify_fluctuations (one value per time point)
    # Use the first temperature value from each file (since all points in a file share the same timestamp)
    temperature_per_sweep = []
    for e in entries:
        temp = e.get("temperature")
        if temp is not None and len(temp) > 0:
            temperature_per_sweep.append(np.mean(temp))  # Use mean temperature for each sweep
        else:
            temperature_per_sweep.append(np.nan)
    
    temperature_data = np.array(temperature_per_sweep) if any(np.isfinite(temperature_per_sweep)) else None
    
    # Quantify fluctuations
    wl_roi = (wl_min, wl_max) if wl_min is not None and wl_max is not None else None
    # Use "lorentz" mode to track ALL peaks with RA's Lorentzian fitter
    benchtop_stats, benchtop_traces = quantify_fluctuations(spec, ref_wl, rel_minutes, output_dir, 
                                          prefix="benchtop_spectrogram", wl_roi=wl_roi,
                                          peak_mode="lorentz", data_type="linear",
                                          temperature_data=temperature_data,
                                          gaussian_filter_sigma=8.0, prominence_scaler=0.1,
                                          r2_threshold=0.85)
    
    # Overlay multi-peak traces on spectrogram if available
    if benchtop_traces is not None and len(benchtop_traces) > 0:
        out_overlay_png = os.path.join(output_dir, "benchtop_spectrogram_with_traces.png")
        overlay_peak_traces_on_spectrogram(spec, ref_wl, rel_minutes, benchtop_traces, 
                                           out_overlay_png, title="Benchtop Spectrogram with Multi-Peak Tracking")
    
    # Generate separate cumulative and per-step RA drift plots with inferno colors
    if benchtop_stats and 'ra_delta_cumulative_pm' in benchtop_stats and 'ra_delta_step_pm' in benchtop_stats:
        logger.info("Generating benchtop RA-style drift plots (cumulative & per-step)")
        
        cumulative_pm = np.array(benchtop_stats['ra_delta_cumulative_pm'], dtype=float)
        step_pm = np.array(benchtop_stats['ra_delta_step_pm'], dtype=float)
        
        # Calculate drift rate
        def calc_drift_rate(times_arr, cumulative_arr):
            valid = np.isfinite(cumulative_arr) & np.isfinite(times_arr)
            if np.sum(valid) < 2:
                return 0.0
            coeffs = np.polyfit(times_arr[valid], cumulative_arr[valid], 1)
            return coeffs[0]
        
        drift_rate = calc_drift_rate(rel_minutes, cumulative_pm)
        
        # Cumulative drift plot
        fig_cum, ax_cum = plt.subplots(figsize=(10, 6))
        cmap = plt.cm.inferno
        color_benchtop = cmap(0.2)
        
        ax_cum.plot(rel_minutes, cumulative_pm, 'o-', 
                    label=f"Benchtop ({drift_rate:.2f} pm/min)", 
                    linewidth=1.8, color=color_benchtop, markersize=5)
        ax_cum.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_ylabel("Cumulative Δλ (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_title("Benchtop Cumulative Drift", fontsize=PLOT_FONT_TITLE)
        ax_cum.grid(True, linestyle="--", alpha=0.3)
        ax_cum.legend(fontsize=PLOT_FONT_LEGEND)
        ax_cum.tick_params(axis="both", which="major", labelsize=PLOT_FONT_AXIS_TICKS)
        fig_cum.tight_layout()
        
        out_cum_png = os.path.join(output_dir, "benchtop_drift_cumulative.png")
        fig_cum.savefig(out_cum_png, dpi=300)
        plt.close(fig_cum)
        logger.info(f"Saved benchtop cumulative drift plot to {out_cum_png}")
        
        # Per-step drift plot
        fig_step, ax_step = plt.subplots(figsize=(10, 6))
        ax_step.plot(rel_minutes, step_pm, 'o-', label="Benchtop", 
                     linewidth=1.5, color=color_benchtop, markersize=5)
        ax_step.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_ylabel("Δλ per sweep (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_title("Benchtop Per-sweep Drift", fontsize=PLOT_FONT_TITLE)
        ax_step.grid(True, linestyle="--", alpha=0.3)
        ax_step.legend(fontsize=PLOT_FONT_LEGEND)
        ax_step.tick_params(axis="both", which="major", labelsize=PLOT_FONT_AXIS_TICKS)
        fig_step.tight_layout()
        
        out_step_png = os.path.join(output_dir, "benchtop_drift_perstep.png")
        fig_step.savefig(out_step_png, dpi=300)
        plt.close(fig_step)
        logger.info(f"Saved benchtop per-step drift plot to {out_step_png}")
    
    # Plot temperature drift if available
    has_temp_data = any(e.get("temperature") is not None for e in entries)
    if has_temp_data:
        logger.info("Generating temperature drift plot for benchtop data")
        
        # Collect all temperature points with their timestamps
        all_temps = []
        all_times_list = []
        
        for e in entries:
            temp = e.get("temperature")
            if temp is not None and len(temp) > 0:
                # Use the file timestamp for all temperature points in this file
                file_time = e["ts"]
                all_temps.extend(temp)
                all_times_list.extend([file_time] * len(temp))
        
        if len(all_temps) > 0:
            all_temps = np.array(all_temps)
            all_times = np.array(all_times_list)
            
            # Convert to relative minutes (same timescale as spectrogram)
            temp_rel_minutes = (all_times - times[0]) / 60.0
            
            # Calculate statistics
            temp_mean = np.mean(all_temps)
            temp_std = np.std(all_temps)
            temp_min = np.min(all_temps)
            temp_max = np.max(all_temps)
            temp_range = temp_max - temp_min
            
            # Create temperature drift plot
            out_temp_png = os.path.join(output_dir, "benchtop_temperature_drift.png")
            fig_temp, ax = plt.subplots(figsize=(14, 6))
            
            # Plot temperature vs time (uses same timescale as spectrogram: rel_minutes)
            ax.plot(temp_rel_minutes, all_temps, '.', markersize=3, 
                     color='darkred', alpha=0.6, label='Temperature')
            
            # Add horizontal lines for statistics
            ax.axhline(temp_mean, color='blue', linestyle='--', linewidth=1.5, 
                        label=f'Mean: {temp_mean:.2f}°C', alpha=0.7)
            ax.axhline(temp_min, color='green', linestyle=':', linewidth=1, 
                        label=f'Min: {temp_min:.2f}°C', alpha=0.5)
            ax.axhline(temp_max, color='orange', linestyle=':', linewidth=1, 
                        label=f'Max: {temp_max:.2f}°C', alpha=0.5)
            
            ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax.set_ylabel("Temperature (°C)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax.set_title(f"Benchtop Temperature Drift Over Time\nRange: {temp_range:.2f}°C, Std: {temp_std:.2f}°C", 
                          fontsize=PLOT_FONT_TITLE)
            ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.legend(loc='upper right', fontsize=PLOT_FONT_LEGEND)
            
            # Add statistics box
            stats_text = f'Statistics:\n' \
                         f'Mean: {temp_mean:.2f}°C\n' \
                         f'Std Dev: {temp_std:.2f}°C\n' \
                         f'Min: {temp_min:.2f}°C\n' \
                         f'Max: {temp_max:.2f}°C\n' \
                         f'Range: {temp_range:.2f}°C\n' \
                         f'Points: {len(all_temps)}'
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                     fontsize=PLOT_FONT_TEXT, verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            fig_temp.tight_layout()
            fig_temp.savefig(out_temp_png, dpi=300)
            plt.close(fig_temp)
            logger.info(f"Saved benchtop temperature drift plot to {out_temp_png}")
            
            # Create delta temperature plot (ΔT from initial value)
            initial_temp = all_temps[0]
            delta_temp = all_temps - initial_temp
            delta_temp_std = np.std(delta_temp)
            delta_temp_max = np.max(np.abs(delta_temp))
            delta_temp_final = delta_temp[-1]
            
            out_delta_temp_png = os.path.join(output_dir, "benchtop_temperature_delta.png")
            fig_delta_temp, ax_dt = plt.subplots(figsize=(14, 6))
            
            # Plot ΔT vs time
            ax_dt.plot(temp_rel_minutes, delta_temp, '.', markersize=3, 
                       color='darkred', alpha=0.6, label='ΔT from initial')
            ax_dt.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
            ax_dt.fill_between([temp_rel_minutes.min(), temp_rel_minutes.max()], 
                              -delta_temp_std, delta_temp_std,
                              alpha=0.2, color='red', label=f'±1σ: {delta_temp_std:.3f}°C')
            
            ax_dt.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax_dt.set_ylabel("ΔT from initial (°C)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax_dt.set_title(f"Benchtop Temperature Drift from Initial Value\n" + 
                           f"Initial T: {initial_temp:.3f}°C, Std: {delta_temp_std:.3f}°C, Max |ΔT|: {delta_temp_max:.3f}°C", 
                           fontsize=PLOT_FONT_TITLE)
            ax_dt.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
            ax_dt.grid(True, alpha=0.3, linestyle='--')
            ax_dt.legend(loc='best', fontsize=PLOT_FONT_LEGEND)
            
            # Add statistics box
            delta_stats_text = f'ΔT Statistics:\n' \
                              f'Initial T: {initial_temp:.3f}°C\n' \
                              f'Std Dev: {delta_temp_std:.3f}°C\n' \
                              f'Max |ΔT|: {delta_temp_max:.3f}°C\n' \
                              f'Final ΔT: {delta_temp_final:.3f}°C\n' \
                              f'Points: {len(all_temps)}'
            
            ax_dt.text(0.02, 0.98, delta_stats_text, transform=ax_dt.transAxes,
                      fontsize=PLOT_FONT_TEXT, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            
            fig_delta_temp.tight_layout()
            fig_delta_temp.savefig(out_delta_temp_png, dpi=300)
            plt.close(fig_delta_temp)
            logger.info(f"Saved benchtop delta temperature plot to {out_delta_temp_png}")
        else:
            logger.warning("Temperature data found but all arrays are empty after filtering zeros")
    else:
        logger.info("No temperature data found in benchtop CSV files")

    # Generate overlay plots (power vs wavelength) similar to sweep_benchtop_continuous
    plot_benchtop_overlays(entries, output_dir, wl_min, wl_max)


def process_onchip_folder(osa_mat_path: str, liv_parent: str, output_dir: str, save_mat: bool = True):
    """Process on-chip data: load OSA polyfit, find LIV files, convert current→wavelength, generate plots.
    
    Args:
        osa_mat_path: Path to OSA .mat file containing polyfit coefficients
        liv_parent: Parent directory containing timestamped LIV .mat files
        output_dir: Where to save outputs
        save_mat: Whether to save a .mat file with the spectrogram data
    """
    import scipy.io as sio
    
    # Load OSA .mat file to get polynomial fit coefficients
    logger.info(f"Loading OSA file: {osa_mat_path}")
    try:
        osa_data = sio.loadmat(osa_mat_path, squeeze_me=True, struct_as_record=False)
    except Exception as e:
        logger.error(f"Failed to load OSA .mat file: {e}")
        return
    
    # Extract polyfit coefficients - try 3rd order first, fallback to 2nd order
    poly_coeffs = None
    poly_order = None
    
    # Try 3rd order first
    possible_keys_deg3 = ['polyfit_peakWL_vs_I_deg3_coeffs', 'poly_coeffs3']
    for key in possible_keys_deg3:
        if key in osa_data:
            poly_coeffs = np.array(osa_data[key]).flatten()
            if len(poly_coeffs) == 4:
                poly_order = 3
                logger.info(f"Found 3rd order polyfit coefficients under key '{key}': {poly_coeffs}")
                break
    
    # Fallback to 2nd order if 3rd not found
    if poly_coeffs is None:
        possible_keys_deg2 = ['polyfit_peakWL_vs_I_deg2_coeffs', 'poly_coeffs', 'coeffs']
        for key in possible_keys_deg2:
            if key in osa_data:
                poly_coeffs = np.array(osa_data[key]).flatten()
                if len(poly_coeffs) == 3:
                    poly_order = 2
                    logger.info(f"Found 2nd order polyfit coefficients under key '{key}': {poly_coeffs}")
                    break
    
    if poly_coeffs is None:
        # Try to compute from peak_wavelength and current_mA if available
        if 'peak_wavelength' in osa_data and 'current_mA' in osa_data:
            wl = np.array(osa_data['peak_wavelength']).flatten()
            curr = np.array(osa_data['current_mA']).flatten()
            if len(wl) >= 4 and len(curr) >= 4:
                poly_coeffs = np.polyfit(curr, wl, 3)
                poly_order = 3
                logger.info(f"Computed 3rd order polyfit from OSA data: {poly_coeffs}")
            elif len(wl) >= 3 and len(curr) >= 3:
                poly_coeffs = np.polyfit(curr, wl, 2)
                poly_order = 2
                logger.info(f"Computed 2nd order polyfit from OSA data: {poly_coeffs}")
            else:
                logger.error("Not enough data points in OSA file to compute polyfit")
                return
        else:
            logger.error(f"Could not find polyfit coefficients or raw data in OSA .mat file. Keys: {list(osa_data.keys())}")
            return
    
    # Log the polynomial equation
    if poly_order == 3:
        if len(poly_coeffs) < 4:
            logger.error(f"Invalid 3rd order polyfit coefficients (need 4): {poly_coeffs}")
            return
        a, b, c, d = poly_coeffs[0], poly_coeffs[1], poly_coeffs[2], poly_coeffs[3]
        logger.info(f"Using 3rd order polyfit: wavelength = {a:.3e}*I³ + {b:.3e}*I² + {c:.3e}*I + {d:.3f}")
    else:  # poly_order == 2
        if len(poly_coeffs) < 3:
            logger.error(f"Invalid 2nd order polyfit coefficients (need 3): {poly_coeffs}")
            return
        a, b, c = poly_coeffs[0], poly_coeffs[1], poly_coeffs[2]
        logger.info(f"Using 2nd order polyfit: wavelength = {a:.3e}*I² + {b:.3e}*I + {c:.3f}")
    
    # Find all LIV .mat files recursively
    logger.info(f"Searching for LIV .mat files under: {liv_parent}")
    liv_files = []
    for root, dirs, files in os.walk(liv_parent):
        for f in files:
            if f.endswith('.mat') and not f.startswith('.'):
                liv_files.append(os.path.join(root, f))
    
    if not liv_files:
        logger.error(f"No .mat files found under {liv_parent}")
        return
    
    logger.info(f"Found {len(liv_files)} LIV .mat files")
    
    # Process each LIV file
    entries: List[Dict] = []
    for liv_path in liv_files:
        try:
            liv_data = sio.loadmat(liv_path, squeeze_me=True, struct_as_record=False)
        except Exception as e:
            logger.warning(f"Failed to load {liv_path}: {e}")
            continue
        
        # Extract current and power (try multiple channel keys)
        current = None
        power = None
        
        # Try to find current
        for curr_key in ['current', 'Current', 'current_mA']:
            if curr_key in liv_data:
                current = np.array(liv_data[curr_key]).flatten()
                break
        
        # Try to find power (prefer channel_3, fallback to channel_0)
        for pow_key in ['channel_3', 'channel_0', 'power', 'Power']:
            if pow_key in liv_data:
                power = np.array(liv_data[pow_key]).flatten()
                break
        
        if current is None or power is None:
            logger.debug(f"Skipping {liv_path}: couldn't find current or power. Keys: {list(liv_data.keys())}")
            continue
        
        # Filter current >= 25 mA
        valid_idx = current >= 25.0
        if not np.any(valid_idx):
            logger.debug(f"Skipping {liv_path}: no current values >= 25 mA")
            continue
        
        current = current[valid_idx]
        power = power[valid_idx]
        
        # Extract temperature if available
        temperature = None
        for temp_key in ['temperature', 'Temperature', 'temp', 'Temp']:
            if temp_key in liv_data:
                temperature = np.array(liv_data[temp_key]).flatten()
                # Filter the same way as current/power
                temperature = temperature[valid_idx]
                # Remove zero values
                temperature = temperature[temperature != 0]
                if len(temperature) > 0:
                    logger.debug(f"Found temperature data in {os.path.basename(liv_path)}: {len(temperature)} points")
                    break
                else:
                    temperature = None
        
        # Get timestamp
        ts = get_file_timestamp(liv_path)
        
        # Convert current (mA) to wavelength (nm) using polyfit
        if poly_order == 3:
            wavelength = a * current**3 + b * current**2 + c * current + d
        else:  # poly_order == 2
            wavelength = a * current**2 + b * current + c
        
        # Debug: check first file to see wavelength vs current relationship
        if len(entries) == 0:
            logger.info(f"First LIV file wavelength range: {wavelength.min():.4f} to {wavelength.max():.4f} nm")
            logger.info(f"Corresponding current range: {current.min():.2f} to {current.max():.2f} mA")
            logger.info(f"Wavelength trend: {'INCREASING' if wavelength[-1] > wavelength[0] else 'DECREASING'} with current")
        
        entries.append({
            "file": liv_path,
            "current": current.astype(float),
            "wavelength": wavelength.astype(float),
            "power": power.astype(float),
            "temperature": temperature,
            "ts": ts
        })
    
    if not entries:
        logger.error("No valid LIV files with current & power found")
        return
    
    logger.info(f"Successfully processed {len(entries)} LIV files")
    
    # Sort by timestamp
    entries.sort(key=lambda e: e["ts"])
    times = np.array([e["ts"] for e in entries])
    rel_seconds = times - times[0]
    rel_minutes = rel_seconds / 60.0
    
    # Determine common wavelength grid from first entry (keep original order)
    ref_wl = entries[0]["wavelength"]
    
    # Interpolate all traces onto the reference wavelength grid
    spec_rows = []
    fnames = []
    for e in entries:
        wl = e["wavelength"]
        power = e["power"]
        
        # np.interp requires x values to be increasing, so check and handle both directions
        if ref_wl[0] < ref_wl[-1]:
            # ref_wl is increasing
            if wl[0] > wl[-1]:
                # wl is decreasing, reverse it for interpolation
                p_interp = np.interp(ref_wl, wl[::-1], power[::-1])
            else:
                # wl is increasing
                p_interp = np.interp(ref_wl, wl, power)
        else:
            # ref_wl is decreasing, reverse it for interpolation, then reverse result back
            if wl[0] > wl[-1]:
                # wl is decreasing
                p_interp = np.interp(ref_wl[::-1], wl[::-1], power[::-1])[::-1]
            else:
                # wl is increasing, reverse it for interpolation
                p_interp = np.interp(ref_wl[::-1], wl, power)[::-1]
        
        spec_rows.append(p_interp)
        fnames.append(e["file"])
    
    spec = np.vstack(spec_rows)  # shape (time, wavelength)
    
    logger.info(f"Spectrogram shape: {spec.shape}, ref_wl shape: {ref_wl.shape}")
    logger.info(f"ref_wl range: [{ref_wl[0]:.4f}, {ref_wl[-1]:.4f}] nm")
    logger.info(f"ref_wl is {'increasing' if ref_wl[-1] > ref_wl[0] else 'decreasing'}")
    
    # Find which wavelength index has maximum average power to verify alignment
    avg_power_per_wl = np.mean(spec, axis=0)
    max_power_idx = np.argmax(avg_power_per_wl)
    logger.info(f"Peak power at wavelength index {max_power_idx} = {ref_wl[max_power_idx]:.4f} nm")
    
    # Save .mat for later reuse
    if save_mat:
        mat_path = os.path.join(output_dir, "onchip_spectrogram.mat")
        try:
            savemat(mat_path, {
                "powers": spec,
                "wavelength": ref_wl,
                "times": times,
                "rel_seconds": rel_seconds,
                "rel_minutes": rel_minutes,
                "filenames": fnames,
                "polyfit_coeffs": poly_coeffs
            })
            logger.info(f"Saved on-chip .mat to {mat_path}")
        except Exception as exc:
            logger.error(f"Failed to save .mat: {exc}")
    
    # Plot spectrogram
    out_png = os.path.join(output_dir, "onchip_spectrogram.png")
    fig, ax = plt.subplots(figsize=(10, 6))
    # Use actual ref_wl[0] and ref_wl[-1] to match data order (not min/max)
    # With origin="lower", bottom of image (row 0) maps to extent[2], top (row -1) maps to extent[3]
    # spec.T has shape (wavelength, time), so row i corresponds to ref_wl[i]
    extent = [rel_minutes.min(), rel_minutes.max(), ref_wl[0], ref_wl[-1]]
    im = ax.imshow(spec.T, aspect="auto", origin="lower", cmap="inferno", extent=extent)
    
    logger.info(f"Plotting spectrogram with extent: time=[{rel_minutes.min():.2f}, {rel_minutes.max():.2f}], wl=[{ref_wl[0]:.4f}, {ref_wl[-1]:.4f}]")
    ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_ylabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_title("On-chip spectrogram - alternating sweeps", fontsize=PLOT_FONT_TITLE)
    ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    # Show full numeric wavelength ticks (no offset/scientific notation)
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter(useOffset=False))
    ax.ticklabel_format(style='plain', axis='y')
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL)
    cbar.ax.tick_params(labelsize=PLOT_FONT_AXIS_TICKS)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    logger.info(f"Saved on-chip spectrogram to {out_png}")
    
    # Extract temperature data (same as benchtop section)
    temperature_per_sweep = []
    for e in entries:
        temp = e.get("temperature")
        if temp is not None and len(temp) > 0:
            temperature_per_sweep.append(np.mean(temp))
        else:
            temperature_per_sweep.append(np.nan)
    
    temperature_data = np.array(temperature_per_sweep) if any(np.isfinite(temperature_per_sweep)) else None
    
    # Quantify fluctuations
    # Use "lorentz" mode to track ALL peaks with on-chip Lorentzian fitter
    onchip_stats, onchip_traces = quantify_fluctuations(spec, ref_wl, rel_minutes, output_dir, 
                                        prefix="onchip_spectrogram", wl_roi=None,
                                        peak_mode="lorentz", data_type="onchip",
                                        temperature_data=temperature_data,
                                        gaussian_filter_sigma=8.0, prominence_scaler=0.1,
                                        r2_threshold=0.85)
    
    # Overlay multi-peak traces on spectrogram if available
    if onchip_traces is not None and len(onchip_traces) > 0:
        # Debug: Check what values are in the centers
        logger.info(f"ref_wl before overlay: [{ref_wl[0]:.4f}, {ref_wl[-1]:.4f}] nm")
        for i, trace in enumerate(onchip_traces):
            centers = trace['centers']
            valid = ~np.isnan(centers)
            if valid.any():
                logger.info(f"Peak {i+1} centers range: [{np.nanmin(centers):.4f}, {np.nanmax(centers):.4f}] nm")
        
        out_overlay_png = os.path.join(output_dir, "onchip_spectrogram_with_traces.png")
        overlay_peak_traces_on_spectrogram(spec, ref_wl, rel_minutes, onchip_traces, 
                                           out_overlay_png, title="On-Chip Spectrogram with Multi-Peak Tracking")
    
    # Generate separate cumulative and per-step RA drift plots with inferno colors
    if onchip_stats and 'ra_delta_cumulative_pm' in onchip_stats and 'ra_delta_step_pm' in onchip_stats:
        logger.info("Generating on-chip RA-style drift plots (cumulative & per-step)")
        
        cumulative_pm = np.array(onchip_stats['ra_delta_cumulative_pm'], dtype=float)
        step_pm = np.array(onchip_stats['ra_delta_step_pm'], dtype=float)
        
        # Calculate drift rate
        def calc_drift_rate(times_arr, cumulative_arr):
            valid = np.isfinite(cumulative_arr) & np.isfinite(times_arr)
            if np.sum(valid) < 2:
                return 0.0
            coeffs = np.polyfit(times_arr[valid], cumulative_arr[valid], 1)
            return coeffs[0]
        
        drift_rate = calc_drift_rate(rel_minutes, cumulative_pm)
        
        # Cumulative drift plot
        fig_cum, ax_cum = plt.subplots(figsize=(10, 6))
        cmap = plt.cm.inferno
        color_onchip = cmap(0.8)
        
        ax_cum.plot(rel_minutes, cumulative_pm, 'o-', 
                    label=f"On-chip ({drift_rate:.2f} pm/min)", 
                    linewidth=1.8, color=color_onchip, markersize=5)
        ax_cum.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_ylabel("Cumulative Δλ (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_title("On-Chip Cumulative Drift", fontsize=PLOT_FONT_TITLE)
        ax_cum.grid(True, linestyle="--", alpha=0.3)
        ax_cum.legend(fontsize=PLOT_FONT_LEGEND)
        ax_cum.tick_params(axis="both", which="major", labelsize=PLOT_FONT_AXIS_TICKS)
        fig_cum.tight_layout()
        
        out_cum_png = os.path.join(output_dir, "onchip_drift_cumulative.png")
        fig_cum.savefig(out_cum_png, dpi=300)
        plt.close(fig_cum)
        logger.info(f"Saved on-chip cumulative drift plot to {out_cum_png}")
        
        # Per-step drift plot
        fig_step, ax_step = plt.subplots(figsize=(10, 6))
        ax_step.plot(rel_minutes, step_pm, 'o-', label="On-chip", 
                     linewidth=1.5, color=color_onchip, markersize=5)
        ax_step.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_ylabel("Δλ per sweep (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_title("On-Chip Per-sweep Drift", fontsize=PLOT_FONT_TITLE)
        ax_step.grid(True, linestyle="--", alpha=0.3)
        ax_step.legend(fontsize=PLOT_FONT_LEGEND)
        ax_step.tick_params(axis="both", which="major", labelsize=PLOT_FONT_AXIS_TICKS)
        fig_step.tight_layout()
        
        out_step_png = os.path.join(output_dir, "onchip_drift_perstep.png")
        fig_step.savefig(out_step_png, dpi=300)
        plt.close(fig_step)
        logger.info(f"Saved on-chip per-step drift plot to {out_step_png}")
    
    # Plot temperature drift if available
    has_temp_data = any(e.get("temperature") is not None for e in entries)
    if has_temp_data:
        logger.info("Generating temperature drift plot for on-chip data")
        
        # Collect all temperature points with their timestamps
        all_temps = []
        all_times_list = []
        
        for e in entries:
            temp = e.get("temperature")
            if temp is not None and len(temp) > 0:
                # Use the file timestamp for all temperature points in this file
                file_time = e["ts"]
                all_temps.extend(temp)
                all_times_list.extend([file_time] * len(temp))
        
        if len(all_temps) > 0:
            all_temps = np.array(all_temps)
            all_times = np.array(all_times_list)
            
            # Convert to relative minutes (same timescale as spectrogram)
            temp_rel_minutes = (all_times - times[0]) / 60.0
            
            # Calculate statistics
            temp_mean = np.mean(all_temps)
            temp_std = np.std(all_temps)
            temp_min = np.min(all_temps)
            temp_max = np.max(all_temps)
            temp_range = temp_max - temp_min
            
            # Create temperature drift plot
            out_temp_png = os.path.join(output_dir, "onchip_temperature_drift.png")
            fig_temp, ax = plt.subplots(figsize=(14, 6))
            
            # Plot temperature vs time (uses same timescale as spectrogram: rel_minutes)
            ax.plot(temp_rel_minutes, all_temps, '.', markersize=3, 
                     color='darkred', alpha=0.6, label='Temperature')
            
            # Add horizontal lines for statistics
            ax.axhline(temp_mean, color='blue', linestyle='--', linewidth=1.5, 
                        label=f'Mean: {temp_mean:.2f}°C', alpha=0.7)
            ax.axhline(temp_min, color='green', linestyle=':', linewidth=1, 
                        label=f'Min: {temp_min:.2f}°C', alpha=0.5)
            ax.axhline(temp_max, color='orange', linestyle=':', linewidth=1, 
                        label=f'Max: {temp_max:.2f}°C', alpha=0.5)
            
            ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax.set_ylabel("Temperature (°C)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax.set_title(f"On-Chip Temperature Drift Over Time\nRange: {temp_range:.2f}°C, Std: {temp_std:.2f}°C", 
                          fontsize=PLOT_FONT_TITLE)
            ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.legend(loc='upper right', fontsize=PLOT_FONT_LEGEND)
            
            # Add statistics box
            stats_text = f'Statistics:\n' \
                         f'Mean: {temp_mean:.2f}°C\n' \
                         f'Std Dev: {temp_std:.2f}°C\n' \
                         f'Min: {temp_min:.2f}°C\n' \
                         f'Max: {temp_max:.2f}°C\n' \
                         f'Range: {temp_range:.2f}°C\n' \
                         f'Points: {len(all_temps)}'
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                     fontsize=PLOT_FONT_TEXT, verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            fig_temp.tight_layout()
            fig_temp.savefig(out_temp_png, dpi=300)
            plt.close(fig_temp)
            logger.info(f"Saved on-chip temperature drift plot to {out_temp_png}")
            
            # Create delta temperature plot (ΔT from initial value)
            initial_temp = all_temps[0]
            delta_temp = all_temps - initial_temp
            delta_temp_std = np.std(delta_temp)
            delta_temp_max = np.max(np.abs(delta_temp))
            delta_temp_final = delta_temp[-1]
            
            out_delta_temp_png = os.path.join(output_dir, "onchip_temperature_delta.png")
            fig_delta_temp, ax_dt = plt.subplots(figsize=(14, 6))
            
            # Plot ΔT vs time
            ax_dt.plot(temp_rel_minutes, delta_temp, '.', markersize=3, 
                       color='darkred', alpha=0.6, label='ΔT from initial')
            ax_dt.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
            ax_dt.fill_between([temp_rel_minutes.min(), temp_rel_minutes.max()], 
                              -delta_temp_std, delta_temp_std,
                              alpha=0.2, color='red', label=f'±1σ: {delta_temp_std:.3f}°C')
            
            ax_dt.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax_dt.set_ylabel("ΔT from initial (°C)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax_dt.set_title(f"On-Chip Temperature Drift from Initial Value\n" + 
                           f"Initial T: {initial_temp:.3f}°C, Std: {delta_temp_std:.3f}°C, Max |ΔT|: {delta_temp_max:.3f}°C", 
                           fontsize=PLOT_FONT_TITLE)
            ax_dt.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
            ax_dt.grid(True, alpha=0.3, linestyle='--')
            ax_dt.legend(loc='best', fontsize=PLOT_FONT_LEGEND)
            
            # Add statistics box
            delta_stats_text = f'ΔT Statistics:\n' \
                              f'Initial T: {initial_temp:.3f}°C\n' \
                              f'Std Dev: {delta_temp_std:.3f}°C\n' \
                              f'Max |ΔT|: {delta_temp_max:.3f}°C\n' \
                              f'Final ΔT: {delta_temp_final:.3f}°C\n' \
                              f'Points: {len(all_temps)}'
            
            ax_dt.text(0.02, 0.98, delta_stats_text, transform=ax_dt.transAxes,
                      fontsize=PLOT_FONT_TEXT, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            
            fig_delta_temp.tight_layout()
            fig_delta_temp.savefig(out_delta_temp_png, dpi=300)
            plt.close(fig_delta_temp)
            logger.info(f"Saved on-chip delta temperature plot to {out_delta_temp_png}")
        else:
            logger.warning("Temperature data found but all arrays are empty after filtering zeros")
    else:
        logger.info("No temperature data found in on-chip LIV files")
    
    # Generate overlay plots
    plot_onchip_overlays(entries, output_dir, ref_wl.min(), ref_wl.max())


def process_evalsys_folder(osa_mat_path: str, evalsys_parent: str, output_dir: str, save_mat: bool = True):
    """Process eval system .mat files with end_time timestamps and inverted power4 data.
    
    Args:
        osa_mat_path: Path to OSA .mat file containing polyfit coefficients
        evalsys_parent: Parent directory containing eval system .mat files
        output_dir: Where to save outputs
        save_mat: Whether to save a .mat file with the spectrogram data
    """
    import scipy.io as sio
    from dateutil import parser as date_parser
    
    # Load OSA .mat file to get polynomial fit coefficients
    logger.info(f"Loading OSA file: {osa_mat_path}")
    try:
        osa_data = sio.loadmat(osa_mat_path, squeeze_me=True, struct_as_record=False)
    except Exception as e:
        logger.error(f"Failed to load OSA .mat file: {e}")
        return
    
    # Extract polyfit coefficients - try 3rd order first, fallback to 2nd order
    poly_coeffs = None
    poly_order = None
    
    # Try 3rd order first
    possible_keys_deg3 = ['polyfit_peakWL_vs_I_deg3_coeffs', 'poly_coeffs3']
    for key in possible_keys_deg3:
        if key in osa_data:
            poly_coeffs = np.array(osa_data[key]).flatten()
            if len(poly_coeffs) == 4:
                poly_order = 3
                logger.info(f"Found 3rd order polyfit coefficients under key '{key}': {poly_coeffs}")
                break
    
    # Fallback to 2nd order if 3rd not found
    if poly_coeffs is None:
        possible_keys_deg2 = ['polyfit_peakWL_vs_I_deg2_coeffs', 'poly_coeffs', 'coeffs']
        for key in possible_keys_deg2:
            if key in osa_data:
                poly_coeffs = np.array(osa_data[key]).flatten()
                if len(poly_coeffs) == 3:
                    poly_order = 2
                    logger.info(f"Found 2nd order polyfit coefficients under key '{key}': {poly_coeffs}")
                    break
    
    if poly_coeffs is None:
        logger.error(f"Could not find polyfit coefficients in OSA .mat file. Keys: {list(osa_data.keys())}")
        return
    
    # Log the polynomial equation
    if poly_order == 3:
        a, b, c, d = poly_coeffs[0], poly_coeffs[1], poly_coeffs[2], poly_coeffs[3]
        logger.info(f"Using 3rd order polyfit: wavelength = {a:.3e}*I³ + {b:.3e}*I² + {c:.3e}*I + {d:.3f}")
    else:  # poly_order == 2
        a, b, c = poly_coeffs[0], poly_coeffs[1], poly_coeffs[2]
        logger.info(f"Using 2nd order polyfit: wavelength = {a:.3e}*I² + {b:.3e}*I + {c:.3f}")
    
    # Find all eval system .mat files recursively
    logger.info(f"Searching for eval system .mat files under: {evalsys_parent}")
    evalsys_files = []
    for root, dirs, files in os.walk(evalsys_parent):
        for f in files:
            if f.endswith('.mat') and not f.startswith('.'):
                evalsys_files.append(os.path.join(root, f))
    
    if not evalsys_files:
        logger.error(f"No .mat files found under {evalsys_parent}")
        return
    
    logger.info(f"Found {len(evalsys_files)} eval system .mat files")
    
    # Process each eval system file
    entries: List[Dict] = []
    for eval_path in evalsys_files:
        try:
            eval_data = sio.loadmat(eval_path, squeeze_me=True, struct_as_record=False)
        except Exception as e:
            logger.warning(f"Failed to load {eval_path}: {e}")
            continue
        
        # Extract current and power4
        current = None
        power4 = None
        end_time = None
        srs_temps = None
        
        # Try to find current
        for curr_key in ['current', 'Current', 'current_mA']:
            if curr_key in eval_data:
                current = np.array(eval_data[curr_key]).flatten()
                break
        
        # Try to find temperature (srs_temps)
        for temp_key in ['srs_temps', 'temperature', 'Temperature', 'temp']:
            if temp_key in eval_data:
                srs_temps = np.array(eval_data[temp_key]).flatten()
                logger.debug(f"Found temperature data under key '{temp_key}' in {os.path.basename(eval_path)}: {len(srs_temps)} points")
                break
        
        # Try to find power channels (power2, power3, power4) and invert/normalize them
        power2 = None
        power3 = None
        power4 = None
        
        if 'power2' in eval_data:
            power2_raw = np.array(eval_data['power2']).flatten()
            # Invert and normalize
            power2_inverted = -power2_raw
            power2_min = np.min(power2_inverted)
            power2_max = np.max(power2_inverted)
            power2 = (power2_inverted - power2_min) / (power2_max - power2_min)
            logger.debug(f"Inverted and normalized power2 from {os.path.basename(eval_path)}")
        
        if 'power3' in eval_data:
            power3_raw = np.array(eval_data['power3']).flatten()
            # Invert and normalize
            power3_inverted = -power3_raw
            power3_min = np.min(power3_inverted)
            power3_max = np.max(power3_inverted)
            power3 = (power3_inverted - power3_min) / (power3_max - power3_min)
            logger.debug(f"Inverted and normalized power3 from {os.path.basename(eval_path)}")
        
        if 'power4' in eval_data:
            power4_raw = np.array(eval_data['power4']).flatten()
            # Invert and normalize (same as evalsys_vs_benchtopQ.py)
            power4_inverted = -power4_raw  # Flip the peaks
            power_min = np.min(power4_inverted)
            power_max = np.max(power4_inverted)
            power4 = (power4_inverted - power_min) / (power_max - power_min)  # Normalize to [0,1]
            logger.debug(f"Inverted and normalized power4 from {os.path.basename(eval_path)}")
        
        # Try to find end_time timestamp
        if 'end_time' in eval_data:
            try:
                time_str = eval_data['end_time']
                if isinstance(time_str, np.ndarray):
                    time_str = str(time_str.item())
                else:
                    time_str = str(time_str)
                
                # Parse timestamp
                dt = date_parser.parse(time_str)
                end_time = dt.timestamp()
                logger.debug(f"Parsed end_time: {time_str} -> {end_time}")
            except Exception as e:
                logger.warning(f"Failed to parse end_time in {eval_path}: {e}")
        
        if current is None or (power2 is None and power3 is None and power4 is None):
            logger.debug(f"Skipping {eval_path}: couldn't find current or any power channels. Keys: {list(eval_data.keys())}")
            continue
        
        # Filter current >= 40 mA (changed from 25 mA)
        valid_idx = current >= 35.0
        if not np.any(valid_idx):
            logger.debug(f"Skipping {eval_path}: no current values >= 40 mA")
            continue
        
        # Store original length before filtering
        original_len = len(current)
        
        current = current[valid_idx]
        
        # Filter all available power channels
        if power2 is not None:
            power2 = power2[valid_idx]
        if power3 is not None:
            power3 = power3[valid_idx]
        if power4 is not None:
            power4 = power4[valid_idx]
        
        # Interpolate temperature to match current/power4 length
        # Temperature is sampled at ~10x lower rate (e.g., 50 temps for 500 currents)
        temp_interpolated = None
        if srs_temps is not None and len(srs_temps) > 1:
            # Create indices for temperature (assume evenly spaced over the sweep)
            temp_indices = np.linspace(0, original_len - 1, len(srs_temps))
            # Create indices for current data
            current_indices = np.arange(original_len)
            
            # Interpolate temperature to current resolution
            temp_full = np.interp(current_indices, temp_indices, srs_temps)
            
            # Now filter to match valid_idx
            temp_interpolated = temp_full[valid_idx]
            logger.debug(f"Interpolated {len(srs_temps)} temp points to {len(temp_interpolated)} current points")
        
        # Use file timestamp as fallback if end time not found
        if end_time is None:
            end_time = get_file_timestamp(eval_path)
            logger.debug(f"Using file timestamp for end_time: {os.path.basename(eval_path)}")
        
        # Convert current (mA) to wavelength (nm) using polyfit
        if poly_order == 3:
            wavelength = a * current**3 + b * current**2 + c * current + d
        else:  # poly_order == 2
            wavelength = a * current**2 + b * current + c
        
        entries.append({
            "file": eval_path,
            "current": current.astype(float),
            "wavelength": wavelength.astype(float),
            "power2": power2.astype(float) if power2 is not None else None,
            "power3": power3.astype(float) if power3 is not None else None,
            "power4": power4.astype(float) if power4 is not None else None,
            "temperature": temp_interpolated,  # Array of temps for each wavelength point (or None)
            "ts": end_time  # File timestamp for sorting
        })
    
    if not entries:
        logger.error("No valid eval system files with current & power4 found")
        return
    
    logger.info(f"Successfully processed {len(entries)} eval system files")
    
    # Sort by timestamp
    entries.sort(key=lambda e: e["ts"])
    times = np.array([e["ts"] for e in entries])
    rel_seconds = times - times[0]
    rel_minutes = rel_seconds / 60.0
    
    # Collect all temperature and wavelength data for continuous plotting
    # Each file contributes its points sequentially at its file timestamp
    all_temps = []
    all_wavelengths = []
    all_times_per_file = []  # Use file timestamp for all points in that file
    
    for i, e in enumerate(entries):
        if e["temperature"] is not None:
            n_points = len(e["temperature"])
            all_temps.extend(e["temperature"])
            all_wavelengths.extend(e["wavelength"])
            # All points from this file get the same relative time (file timestamp)
            all_times_per_file.extend([rel_minutes[i]] * n_points)
    
    has_temp_data = len(all_temps) > 0 and not np.all(np.isnan(all_temps))
    
    # Determine common wavelength grid from first entry
    ref_wl = entries[0]["wavelength"]
    
    # Interpolate all traces onto the reference wavelength grid for each power channel
    spec_rows_power2 = []
    spec_rows_power3 = []
    spec_rows_power4 = []
    fnames = []
    
    for e in entries:
        wl = e["wavelength"]
        fnames.append(e["file"])
        
        # Process power2
        if e["power2"] is not None:
            power = e["power2"]
            try:
                p_interp = np.interp(ref_wl, wl, power)
            except Exception:
                min_len = min(len(ref_wl), len(power))
                p_interp = np.zeros_like(ref_wl)
                p_interp[:min_len] = power[:min_len]
            spec_rows_power2.append(p_interp)
        else:
            spec_rows_power2.append(np.zeros_like(ref_wl))
        
        # Process power3
        if e["power3"] is not None:
            power = e["power3"]
            try:
                p_interp = np.interp(ref_wl, wl, power)
            except Exception:
                min_len = min(len(ref_wl), len(power))
                p_interp = np.zeros_like(ref_wl)
                p_interp[:min_len] = power[:min_len]
            spec_rows_power3.append(p_interp)
        else:
            spec_rows_power3.append(np.zeros_like(ref_wl))
        
        # Process power4
        if e["power4"] is not None:
            power = e["power4"]
            try:
                p_interp = np.interp(ref_wl, wl, power)
            except Exception:
                min_len = min(len(ref_wl), len(power))
                p_interp = np.zeros_like(ref_wl)
                p_interp[:min_len] = power[:min_len]
            spec_rows_power4.append(p_interp)
        else:
            spec_rows_power4.append(np.zeros_like(ref_wl))
    
    spec_power2 = np.vstack(spec_rows_power2)  # shape (time, wavelength)
    spec_power3 = np.vstack(spec_rows_power3)  # shape (time, wavelength)
    spec_power4 = np.vstack(spec_rows_power4)  # shape (time, wavelength)
    
    # Save .mat for later reuse
    if save_mat:
        mat_path = os.path.join(output_dir, "evalsys_spectrogram.mat")
        try:
            mat_dict = {
                "powers_power2": spec_power2,
                "powers_power3": spec_power3,
                "powers_power4": spec_power4,
                "wavelength": ref_wl,
                "times": times,
                "rel_seconds": rel_seconds,
                "rel_minutes": rel_minutes,
                "filenames": fnames,
                "polyfit_coeffs": poly_coeffs
            }
            if has_temp_data:
                mat_dict["all_temperatures"] = np.array(all_temps)
                mat_dict["all_wavelengths"] = np.array(all_wavelengths)
                mat_dict["all_times_per_file"] = np.array(all_times_per_file)
            savemat(mat_path, mat_dict)
            logger.info(f"Saved eval system .mat to {mat_path}")
        except Exception as exc:
            logger.error(f"Failed to save .mat: {exc}")
    
    # Plot spectrograms for power2, power3, and power4
    extent = [rel_minutes.min(), rel_minutes.max(), ref_wl.min(), ref_wl.max()]
    
    # Power2 spectrogram
    out_png_power2 = os.path.join(output_dir, "evalsys_spectrogram_power2.png")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(spec_power2.T, aspect="auto", origin="lower", cmap="inferno", extent=extent)
    ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_ylabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_title("Eval System Spectrogram - Power2 (Inverted)", fontsize=PLOT_FONT_TITLE)
    ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Normalized Power", fontsize=PLOT_FONT_AXIS_LABEL)
    cbar.ax.tick_params(labelsize=PLOT_FONT_AXIS_TICKS)
    fig.tight_layout()
    fig.savefig(out_png_power2, dpi=200)
    plt.close(fig)
    logger.info(f"Saved power2 spectrogram to {out_png_power2}")
    
    # Quantify fluctuations for power2
    # Use "lorentz" mode to track ALL peaks with Lorentzian fitter
    power2_stats, power2_traces = quantify_fluctuations(spec_power2, ref_wl, rel_minutes, output_dir, 
                                        prefix="evalsys_power2", wl_roi=None,
                                        peak_mode="lorentz", data_type="linear",
                                        gaussian_filter_sigma=6.0, prominence_scaler=0.12,
                                        r2_threshold=0.85)
    
    # Overlay multi-peak traces on power2 spectrogram if available
    if power2_traces is not None and len(power2_traces) > 0:
        out_overlay_png = os.path.join(output_dir, "evalsys_power2_spectrogram_with_traces.png")
        overlay_peak_traces_on_spectrogram(spec_power2, ref_wl, rel_minutes, power2_traces, 
                                           out_overlay_png, title="Eval System Power2 - Multi-Peak Tracking")
    
    # Generate separate cumulative and per-step RA drift plots for power2
    if power2_stats and 'ra_delta_cumulative_pm' in power2_stats and 'ra_delta_step_pm' in power2_stats:
        logger.info("Generating eval system power2 RA-style drift plots (cumulative & per-step)")
        
        cumulative_pm = np.array(power2_stats['ra_delta_cumulative_pm'], dtype=float)
        step_pm = np.array(power2_stats['ra_delta_step_pm'], dtype=float)
        
        def calc_drift_rate(times_arr, cumulative_arr):
            valid = np.isfinite(cumulative_arr) & np.isfinite(times_arr)
            if np.sum(valid) < 2:
                return 0.0
            coeffs = np.polyfit(times_arr[valid], cumulative_arr[valid], 1)
            return coeffs[0]
        
        drift_rate = calc_drift_rate(rel_minutes, cumulative_pm)
        cmap = plt.cm.inferno
        color_eval = cmap(0.5)
        
        fig_cum, ax_cum = plt.subplots(figsize=(10, 6))
        ax_cum.plot(rel_minutes, cumulative_pm, 'o-', 
                    label=f"Eval System Power2 ({drift_rate:.2f} pm/min)", 
                    linewidth=1.8, color=color_eval, markersize=5)
        ax_cum.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_ylabel("Cumulative Δλ (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_title("Eval System Power2 Cumulative Drift", fontsize=PLOT_FONT_TITLE)
        ax_cum.grid(True, linestyle="--", alpha=0.3)
        ax_cum.legend(fontsize=PLOT_FONT_LEGEND)
        ax_cum.tick_params(axis="both", which="major", labelsize=14)
        fig_cum.tight_layout()
        out_cum_png = os.path.join(output_dir, "evalsys_power2_drift_cumulative.png")
        fig_cum.savefig(out_cum_png, dpi=300)
        plt.close(fig_cum)
        logger.info(f"Saved eval system power2 cumulative drift plot to {out_cum_png}")
        
        fig_step, ax_step = plt.subplots(figsize=(10, 6))
        ax_step.plot(rel_minutes, step_pm, 'o-', label="Eval System Power2", 
                     linewidth=1.5, color=color_eval, markersize=5)
        ax_step.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_ylabel("Δλ per sweep (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_title("Eval System Power2 Per-sweep Drift", fontsize=PLOT_FONT_TITLE)
        ax_step.grid(True, linestyle="--", alpha=0.3)
        ax_step.legend(fontsize=PLOT_FONT_LEGEND)
        ax_step.tick_params(axis="both", which="major", labelsize=14)
        fig_step.tight_layout()
        out_step_png = os.path.join(output_dir, "evalsys_power2_drift_perstep.png")
        fig_step.savefig(out_step_png, dpi=300)
        plt.close(fig_step)
        logger.info(f"Saved eval system power2 per-step drift plot to {out_step_png}")
    
    # Power3 spectrogram
    out_png_power3 = os.path.join(output_dir, "evalsys_spectrogram_power3.png")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(spec_power3.T, aspect="auto", origin="lower", cmap="inferno", extent=extent)
    ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_ylabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_title("Eval System Spectrogram - Power3 (Inverted)", fontsize=PLOT_FONT_TITLE)
    ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Normalized Power", fontsize=PLOT_FONT_AXIS_LABEL)
    cbar.ax.tick_params(labelsize=PLOT_FONT_AXIS_TICKS)
    fig.tight_layout()
    fig.savefig(out_png_power3, dpi=200)
    plt.close(fig)
    logger.info(f"Saved power3 spectrogram to {out_png_power3}")
    
    # Quantify fluctuations for power3
    # Use "lorentz" mode to track ALL peaks with Lorentzian fitter
    power3_stats, power3_traces = quantify_fluctuations(spec_power3, ref_wl, rel_minutes, output_dir, 
                                        prefix="evalsys_power3", wl_roi=None,
                                        peak_mode="lorentz", data_type="linear",
                                        gaussian_filter_sigma=6.0, prominence_scaler=0.12,
                                        r2_threshold=0.85)
    
    # Overlay multi-peak traces on power3 spectrogram if available
    if power3_traces is not None and len(power3_traces) > 0:
        out_overlay_png = os.path.join(output_dir, "evalsys_power3_spectrogram_with_traces.png")
        overlay_peak_traces_on_spectrogram(spec_power3, ref_wl, rel_minutes, power3_traces, 
                                           out_overlay_png, title="Eval System Power3 - Multi-Peak Tracking")
    
    # Generate separate cumulative and per-step RA drift plots for power3
    if power3_stats and 'ra_delta_cumulative_pm' in power3_stats and 'ra_delta_step_pm' in power3_stats:
        logger.info("Generating eval system power3 RA-style drift plots (cumulative & per-step)")
        
        cumulative_pm = np.array(power3_stats['ra_delta_cumulative_pm'], dtype=float)
        step_pm = np.array(power3_stats['ra_delta_step_pm'], dtype=float)
        
        def calc_drift_rate(times_arr, cumulative_arr):
            valid = np.isfinite(cumulative_arr) & np.isfinite(times_arr)
            if np.sum(valid) < 2:
                return 0.0
            coeffs = np.polyfit(times_arr[valid], cumulative_arr[valid], 1)
            return coeffs[0]
        
        drift_rate = calc_drift_rate(rel_minutes, cumulative_pm)
        cmap = plt.cm.inferno
        color_eval = cmap(0.5)
        
        fig_cum, ax_cum = plt.subplots(figsize=(10, 6))
        ax_cum.plot(rel_minutes, cumulative_pm, 'o-', 
                    label=f"Eval System Power3 ({drift_rate:.2f} pm/min)", 
                    linewidth=1.8, color=color_eval, markersize=5)
        ax_cum.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_ylabel("Cumulative Δλ (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_title("Eval System Power3 Cumulative Drift", fontsize=PLOT_FONT_TITLE)
        ax_cum.grid(True, linestyle="--", alpha=0.3)
        ax_cum.legend(fontsize=PLOT_FONT_LEGEND)
        ax_cum.tick_params(axis="both", which="major", labelsize=14)
        fig_cum.tight_layout()
        out_cum_png = os.path.join(output_dir, "evalsys_power3_drift_cumulative.png")
        fig_cum.savefig(out_cum_png, dpi=300)
        plt.close(fig_cum)
        logger.info(f"Saved eval system power3 cumulative drift plot to {out_cum_png}")
        
        fig_step, ax_step = plt.subplots(figsize=(10, 6))
        ax_step.plot(rel_minutes, step_pm, 'o-', label="Eval System Power3", 
                     linewidth=1.5, color=color_eval, markersize=5)
        ax_step.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_ylabel("Δλ per sweep (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_title("Eval System Power3 Per-sweep Drift", fontsize=PLOT_FONT_TITLE)
        ax_step.grid(True, linestyle="--", alpha=0.3)
        ax_step.legend(fontsize=PLOT_FONT_LEGEND)
        ax_step.tick_params(axis="both", which="major", labelsize=14)
        fig_step.tight_layout()
        out_step_png = os.path.join(output_dir, "evalsys_power3_drift_perstep.png")
        fig_step.savefig(out_step_png, dpi=300)
        plt.close(fig_step)
        logger.info(f"Saved eval system power3 per-step drift plot to {out_step_png}")
    
    # Power4 spectrogram
    out_png_power4 = os.path.join(output_dir, "evalsys_spectrogram_power4.png")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(spec_power4.T, aspect="auto", origin="lower", cmap="inferno", extent=extent)
    ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_ylabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_title("Eval System Spectrogram - Power4 (Inverted)", fontsize=PLOT_FONT_TITLE)
    ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Normalized Power", fontsize=PLOT_FONT_AXIS_LABEL)
    cbar.ax.tick_params(labelsize=PLOT_FONT_AXIS_TICKS)
    fig.tight_layout()
    fig.savefig(out_png_power4, dpi=200)
    plt.close(fig)
    logger.info(f"Saved power4 spectrogram to {out_png_power4}")
    
    # Quantify fluctuations for power4
    # Use "lorentz" mode with evalsys fitter (data already inverted during preprocessing)
    power4_stats, power4_traces = quantify_fluctuations(spec_power4, ref_wl, rel_minutes, output_dir, 
                                        prefix="evalsys_power4", wl_roi=None,
                                        peak_mode="lorentz", data_type="evalsys",
                                        gaussian_filter_sigma=6.0, prominence_scaler=0.12,
                                        r2_threshold=0.85,
                                        left_baseline_window=10, right_baseline_window=10,
                                        peak_window=15, poly_order=1)
    
    # Overlay multi-peak traces on power4 spectrogram if available
    if power4_traces is not None and len(power4_traces) > 0:
        out_overlay_png = os.path.join(output_dir, "evalsys_power4_spectrogram_with_traces.png")
        overlay_peak_traces_on_spectrogram(spec_power4, ref_wl, rel_minutes, power4_traces, 
                                           out_overlay_png, title="Eval System Power4 - Multi-Peak Tracking (Auto-Flipped)")
    
    # Generate separate cumulative and per-step RA drift plots for power4
    if power4_stats and 'ra_delta_cumulative_pm' in power4_stats and 'ra_delta_step_pm' in power4_stats:
        logger.info("Generating eval system power4 RA-style drift plots (cumulative & per-step)")
        
        cumulative_pm = np.array(power4_stats['ra_delta_cumulative_pm'], dtype=float)
        step_pm = np.array(power4_stats['ra_delta_step_pm'], dtype=float)
        
        def calc_drift_rate(times_arr, cumulative_arr):
            valid = np.isfinite(cumulative_arr) & np.isfinite(times_arr)
            if np.sum(valid) < 2:
                return 0.0
            coeffs = np.polyfit(times_arr[valid], cumulative_arr[valid], 1)
            return coeffs[0]
        
        drift_rate = calc_drift_rate(rel_minutes, cumulative_pm)
        cmap = plt.cm.inferno
        color_eval = cmap(0.5)
        
        fig_cum, ax_cum = plt.subplots(figsize=(10, 6))
        ax_cum.plot(rel_minutes, cumulative_pm, 'o-', 
                    label=f"Eval System Power4 ({drift_rate:.2f} pm/min)", 
                    linewidth=1.8, color=color_eval, markersize=5)
        ax_cum.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_ylabel("Cumulative Δλ (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_cum.set_title("Eval System Power4 Cumulative Drift", fontsize=PLOT_FONT_TITLE)
        ax_cum.grid(True, linestyle="--", alpha=0.3)
        ax_cum.legend(fontsize=PLOT_FONT_LEGEND)
        ax_cum.tick_params(axis="both", which="major", labelsize=14)
        fig_cum.tight_layout()
        out_cum_png = os.path.join(output_dir, "evalsys_power4_drift_cumulative.png")
        fig_cum.savefig(out_cum_png, dpi=300)
        plt.close(fig_cum)
        logger.info(f"Saved eval system power4 cumulative drift plot to {out_cum_png}")
        
        fig_step, ax_step = plt.subplots(figsize=(10, 6))
        ax_step.plot(rel_minutes, step_pm, 'o-', label="Eval System Power4", 
                     linewidth=1.5, color=color_eval, markersize=5)
        ax_step.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_ylabel("Δλ per sweep (pm)", fontsize=PLOT_FONT_AXIS_LABEL)
        ax_step.set_title("Eval System Power4 Per-sweep Drift", fontsize=PLOT_FONT_TITLE)
        ax_step.grid(True, linestyle="--", alpha=0.3)
        ax_step.legend(fontsize=PLOT_FONT_LEGEND)
        ax_step.tick_params(axis="both", which="major", labelsize=14)
        fig_step.tight_layout()
        out_step_png = os.path.join(output_dir, "evalsys_power4_drift_perstep.png")
        fig_step.savefig(out_step_png, dpi=300)
        plt.close(fig_step)
        logger.info(f"Saved eval system power4 per-step drift plot to {out_step_png}")
    
    # Plot temperature vs time if temperature data is available
    if has_temp_data:
        logger.info("Plotting temperature drift over time...")
        
        # Convert to numpy arrays
        all_temps_arr = np.array(all_temps)
        all_times_arr = np.array(all_times_per_file)
        
        # Remove NaN values
        valid_mask = ~np.isnan(all_temps_arr)
        all_temps_arr = all_temps_arr[valid_mask]
        all_times_arr = all_times_arr[valid_mask]
        
        if len(all_temps_arr) > 0:
            # Calculate statistics
            temp_mean = np.mean(all_temps_arr)
            temp_std = np.std(all_temps_arr)
            temp_min = np.min(all_temps_arr)
            temp_max = np.max(all_temps_arr)
            temp_range = temp_max - temp_min
            
            # Create single plot: Temperature vs Time
            fig_temp, ax = plt.subplots(figsize=(14, 6))
            
            # Plot temperature vs time (uses same timescale as spectrogram: rel_minutes)
            ax.plot(all_times_arr, all_temps_arr, '.', markersize=3, 
                     color='darkred', alpha=0.6, label='Temperature')
            
            # Add horizontal lines for statistics
            ax.axhline(temp_mean, color='blue', linestyle='--', linewidth=1.5, 
                        label=f'Mean: {temp_mean:.2f}°C', alpha=0.7)
            ax.axhline(temp_min, color='green', linestyle=':', linewidth=1, 
                        label=f'Min: {temp_min:.2f}°C', alpha=0.5)
            ax.axhline(temp_max, color='orange', linestyle=':', linewidth=1, 
                        label=f'Max: {temp_max:.2f}°C', alpha=0.5)
            
            ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax.set_ylabel("Temperature (°C)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax.set_title(f"Eval System Temperature Drift Over Time\nRange: {temp_range:.2f}°C, Std: {temp_std:.2f}°C", 
                          fontsize=PLOT_FONT_TITLE)
            ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.legend(loc='upper right', fontsize=PLOT_FONT_LEGEND)
            
            # Add statistics box
            stats_text = f'Statistics:\n' \
                         f'Mean: {temp_mean:.2f}°C\n' \
                         f'Std Dev: {temp_std:.2f}°C\n' \
                         f'Min: {temp_min:.2f}°C\n' \
                         f'Max: {temp_max:.2f}°C\n' \
                         f'Range: {temp_range:.2f}°C\n' \
                         f'Points: {len(all_temps_arr)}'
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                     fontsize=PLOT_FONT_TEXT, verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            fig_temp.tight_layout()
            out_temp_png = os.path.join(output_dir, "evalsys_temperature_drift.png")
            fig_temp.savefig(out_temp_png, dpi=300)
            plt.close(fig_temp)
            logger.info(f"Saved temperature drift plot to {out_temp_png}")
            
            # Create delta temperature plot (ΔT from initial value)
            initial_temp = all_temps_arr[0]
            delta_temp = all_temps_arr - initial_temp
            delta_temp_std = np.std(delta_temp)
            delta_temp_max = np.max(np.abs(delta_temp))
            delta_temp_final = delta_temp[-1]
            
            out_delta_temp_png = os.path.join(output_dir, "evalsys_temperature_delta.png")
            fig_delta_temp, ax_dt = plt.subplots(figsize=(14, 6))
            
            # Plot ΔT vs time
            ax_dt.plot(all_times_arr, delta_temp, '.', markersize=3, 
                       color='darkred', alpha=0.6, label='ΔT from initial')
            ax_dt.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
            ax_dt.fill_between([all_times_arr.min(), all_times_arr.max()], 
                              -delta_temp_std, delta_temp_std,
                              alpha=0.2, color='red', label=f'±1σ: {delta_temp_std:.3f}°C')
            
            ax_dt.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax_dt.set_ylabel("ΔT from initial (°C)", fontsize=PLOT_FONT_AXIS_LABEL)
            ax_dt.set_title(f"Eval System Temperature Drift from Initial Value\n" + 
                           f"Initial T: {initial_temp:.3f}°C, Std: {delta_temp_std:.3f}°C, Max |ΔT|: {delta_temp_max:.3f}°C", 
                           fontsize=PLOT_FONT_TITLE)
            ax_dt.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
            ax_dt.grid(True, alpha=0.3, linestyle='--')
            ax_dt.legend(loc='best', fontsize=PLOT_FONT_LEGEND)
            
            # Add statistics box
            delta_stats_text = f'ΔT Statistics:\n' \
                              f'Initial T: {initial_temp:.3f}°C\n' \
                              f'Std Dev: {delta_temp_std:.3f}°C\n' \
                              f'Max |ΔT|: {delta_temp_max:.3f}°C\n' \
                              f'Final ΔT: {delta_temp_final:.3f}°C\n' \
                              f'Points: {len(all_temps_arr)}'
            
            ax_dt.text(0.02, 0.98, delta_stats_text, transform=ax_dt.transAxes,
                      fontsize=PLOT_FONT_TEXT, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            
            fig_delta_temp.tight_layout()
            fig_delta_temp.savefig(out_delta_temp_png, dpi=300)
            plt.close(fig_delta_temp)
            logger.info(f"Saved eval system delta temperature plot to {out_delta_temp_png}")
        else:
            logger.warning("No valid temperature data after filtering NaNs")
    else:
        logger.warning("No temperature data available - skipping temperature drift plot")
    
    # Generate overlay plots for each power channel
    plot_evalsys_overlays(entries, output_dir, ref_wl.min(), ref_wl.max())


def plot_evalsys_overlays(entries: List[Dict], output_dir: str, wl_min: float, wl_max: float):
    """Generate overlay plots of power vs wavelength for eval system data (power2, power3, power4)."""
    if not entries:
        return
    
    # Process each power channel separately
    for power_channel in ['power2', 'power3', 'power4']:
        traces = []
        for e in entries:
            wl = e["wavelength"]
            power = e.get(power_channel)
            if power is None:
                continue
            fname = e["file"]
            
            # Filter to wavelength range
            mask = (wl >= wl_min) & (wl <= wl_max)
            wl_filtered = wl[mask]
            power_filtered = power[mask]
            
            if len(wl_filtered) == 0:
                continue
            
            traces.append((wl_filtered, power_filtered, fname))
        
        if not traces:
            logger.warning(f"No traces in range {wl_min:.2f}-{wl_max:.2f} nm for {power_channel} overlay plots")
            continue
        
        # Get inferno colormap
        cmap = plt.get_cmap('inferno')
        colors = cmap(np.linspace(0.2, 0.9, len(traces)))
        
        # Plot 1: All traces with gradient, only first/last labeled
        fig1, ax1 = plt.subplots(figsize=(12, 7))
        for idx, (wl, power, fname) in enumerate(traces):
            if idx == 0:
                label = f"First: {Path(fname).stem}"
            elif idx == len(traces) - 1:
                label = f"Last: {Path(fname).stem}"
            else:
                label = None
            ax1.plot(wl, power, linewidth=1.2, label=label, color=colors[idx])
        
        ax1.set_xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
        ax1.set_ylabel(f"{power_channel.upper()} (Normalized)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
        ax1.set_title(f"Eval System {power_channel.upper()} vs Wavelength ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
        ax1.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
        fig1.tight_layout()
        
        out_png1 = os.path.join(output_dir, f"EvalSys_{power_channel}_vs_Wavelength_{wl_min:.2f}_{wl_max:.2f}nm.png")
        fig1.savefig(out_png1, dpi=300, bbox_inches='tight')
        logger.info(f"Saved {power_channel} overlay plot to {out_png1}")
        plt.close(fig1)
        
        # Plot 2: All traces with markers if <= 10, else first/last only
        fig2, ax2 = plt.subplots(figsize=(12, 7))
        
        if len(traces) <= 10:
            # Show all traces with full legends
            for idx, (wl, power, fname) in enumerate(traces):
                ax2.plot(wl, power, marker='o', linewidth=1.2, label=Path(fname).stem, color=colors[idx])
            
            ax2.set_title(f"Eval System {power_channel.upper()} vs Wavelength - All Sweeps ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
            out_png2 = os.path.join(output_dir, f"EvalSys_{power_channel}_vs_Wavelength_AllSweeps_{wl_min:.2f}_{wl_max:.2f}nm.png")
        else:
            # Plot only first and last trace
            wl_first, power_first, fname_first = traces[0]
            ax2.plot(wl_first, power_first, marker='o', linewidth=1.2, label=f"First: {Path(fname_first).stem}", color=colors[0])
            
            wl_last, power_last, fname_last = traces[-1]
            ax2.plot(wl_last, power_last, marker='o', linewidth=1.2, label=f"Last: {Path(fname_last).stem}", color=colors[-1])
            
            ax2.set_title(f"Eval System {power_channel.upper()} vs Wavelength - First & Last Sweep ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
            out_png2 = os.path.join(output_dir, f"EvalSys_{power_channel}_vs_Wavelength_FirstLast_{wl_min:.2f}_{wl_max:.2f}nm.png")
        
        ax2.set_xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
        ax2.set_ylabel(f"{power_channel.upper()} (Normalized)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
        ax2.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
        fig2.tight_layout()
        
        fig2.savefig(out_png2, dpi=300, bbox_inches='tight')
        logger.info(f"Saved {power_channel} detailed overlay plot to {out_png2}")
        plt.close(fig2)


def plot_onchip_overlays(entries: List[Dict], output_dir: str, wl_min: float, wl_max: float):
    """Generate overlay plots of power vs wavelength for on-chip data."""
    if not entries:
        return
    
    traces = []
    for e in entries:
        wl = e["wavelength"]
        power = e["power"]
        fname = e["file"]
        
        # Filter to wavelength range
        mask = (wl >= wl_min) & (wl <= wl_max)
        wl_filtered = wl[mask]
        power_filtered = power[mask]
        
        if len(wl_filtered) == 0:
            continue
        
        traces.append((wl_filtered, power_filtered, fname))
    
    if not traces:
        logger.warning(f"No traces in range {wl_min:.2f}-{wl_max:.2f} nm for overlay plots")
        return
    
    # Get inferno colormap
    cmap = plt.get_cmap('inferno')
    colors = cmap(np.linspace(0.2, 0.9, len(traces)))
    
    # Plot 1: All traces with gradient, only first/last labeled
    fig1, ax1 = plt.subplots(figsize=(12, 7))
    for idx, (wl, power, fname) in enumerate(traces):
        if idx == 0:
            label = f"First: {Path(fname).stem}"
        elif idx == len(traces) - 1:
            label = f"Last: {Path(fname).stem}"
        else:
            label = None
        ax1.plot(wl, power, linewidth=1.2, label=label, color=colors[idx])
    
    ax1.set_xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax1.set_ylabel("Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax1.set_title(f"On-Chip Power vs Wavelength ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
    ax1.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
    fig1.tight_layout()
    
    out_png1 = os.path.join(output_dir, f"OnChip_Power_vs_Wavelength_{wl_min:.2f}_{wl_max:.2f}nm.png")
    fig1.savefig(out_png1, dpi=300, bbox_inches='tight')
    logger.info(f"Saved on-chip overlay plot to {out_png1}")
    plt.close(fig1)
    
    # Plot 2: All traces with markers if <= 10, else first/last only
    fig2, ax2 = plt.subplots(figsize=(12, 7))
    
    if len(traces) <= 10:
        # Show all traces with full legends
        for idx, (wl, power, fname) in enumerate(traces):
            ax2.plot(wl, power, marker='o', linewidth=1.2, label=Path(fname).stem, color=colors[idx])
        
        ax2.set_title(f"On-Chip Power vs Wavelength - All Sweeps ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
        out_png2 = os.path.join(output_dir, f"OnChip_Power_vs_Wavelength_AllSweeps_{wl_min:.2f}_{wl_max:.2f}nm.png")
    else:
        # Plot only first and last trace
        wl_first, power_first, fname_first = traces[0]
        ax2.plot(wl_first, power_first, marker='o', linewidth=1.2, label=f"First: {Path(fname_first).stem}", color=colors[0])
        
        wl_last, power_last, fname_last = traces[-1]
        ax2.plot(wl_last, power_last, marker='o', linewidth=1.2, label=f"Last: {Path(fname_last).stem}", color=colors[-1])
        
        ax2.set_title(f"On-Chip Power vs Wavelength - First & Last Sweep ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
        out_png2 = os.path.join(output_dir, f"OnChip_Power_vs_Wavelength_FirstLast_{wl_min:.2f}_{wl_max:.2f}nm.png")
    
    ax2.set_xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax2.set_ylabel("Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
    ax2.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
    fig2.tight_layout()
    
    fig2.savefig(out_png2, dpi=300, bbox_inches='tight')
    logger.info(f"Saved on-chip detailed overlay plot to {out_png2}")
    plt.close(fig2)


def plot_benchtop_overlays(entries: List[Dict], output_dir: str, wl_min: float, wl_max: float):
    """Generate overlay plots of power vs wavelength for all sweeps.
    
    Creates two plots:
    1. All traces overlaid with inferno colormap (only first/last labeled)
    2. First and last traces with markers (or all traces if <= 10)
    """
    if not entries:
        return
    
    traces = []
    for e in entries:
        wl = e["wavelength"]
        power = e["power"]
        fname = e["file"]
        
        # Filter to wavelength range
        mask = (wl >= wl_min) & (wl <= wl_max)
        wl_filtered = wl[mask]
        power_filtered = power[mask]
        
        if len(wl_filtered) == 0:
            continue
        
        traces.append((wl_filtered, power_filtered, fname))
    
    if not traces:
        logger.warning(f"No traces in range {wl_min}-{wl_max} nm for overlay plots")
        return
    
    # Get inferno colormap
    cmap = plt.get_cmap('inferno')
    colors = cmap(np.linspace(0.2, 0.9, len(traces)))
    
    # Plot 1: All traces with gradient, only first/last labeled
    fig1, ax1 = plt.subplots(figsize=(12, 7))
    for idx, (wl, power, fname) in enumerate(traces):
        if idx == 0:
            label = f"First: {Path(fname).stem}"
        elif idx == len(traces) - 1:
            label = f"Last: {Path(fname).stem}"
        else:
            label = None
        ax1.plot(wl, power, linewidth=1.2, label=label, color=colors[idx])
    
    ax1.set_xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax1.set_ylabel("Channel 3 Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax1.set_title(f"Channel 3 vs Wavelength ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
    ax1.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
    fig1.tight_layout()
    
    out_png1 = os.path.join(output_dir, f"Channel3_vs_Wavelength_{wl_min:.2f}_{wl_max:.2f}nm.png")
    fig1.savefig(out_png1, dpi=300, bbox_inches='tight')
    logger.info(f"Saved overlay plot to {out_png1}")
    plt.close(fig1)
    
    # Plot 2: All traces with markers if <= 10, else first/last only
    fig2, ax2 = plt.subplots(figsize=(12, 7))
    
    if len(traces) <= 10:
        # Show all traces with full legends
        for idx, (wl, power, fname) in enumerate(traces):
            ax2.plot(wl, power, marker='o', linewidth=1.2, label=Path(fname).stem, color=colors[idx])
        
        ax2.set_title(f"Channel 3 vs Wavelength - All Sweeps ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
        out_png2 = os.path.join(output_dir, f"Channel3_vs_Wavelength_AllSweeps_{wl_min:.2f}_{wl_max:.2f}nm.png")
    else:
        # Plot only first and last trace
        wl_first, power_first, fname_first = traces[0]
        ax2.plot(wl_first, power_first, marker='o', linewidth=1.2, label=f"First: {Path(fname_first).stem}", color=colors[0])
        
        wl_last, power_last, fname_last = traces[-1]
        ax2.plot(wl_last, power_last, marker='o', linewidth=1.2, label=f"Last: {Path(fname_last).stem}", color=colors[-1])
        
        ax2.set_title(f"Channel 3 vs Wavelength - First & Last Sweep ({wl_min:.2f}-{wl_max:.2f} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
        out_png2 = os.path.join(output_dir, f"Channel3_vs_Wavelength_FirstLast_{wl_min:.2f}_{wl_max:.2f}nm.png")
    
    ax2.set_xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax2.set_ylabel("Channel 3 Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
    ax2.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
    fig2.tight_layout()
    
    fig2.savefig(out_png2, dpi=300, bbox_inches='tight')
    logger.info(f"Saved detailed overlay plot to {out_png2}")
    plt.close(fig2)


def main():
    p = argparse.ArgumentParser(description="Plot spectrograms from a directory of .mat sweep files")
    p.add_argument("-i", "--input-dir", required=False, help="Directory containing .mat files or CSVs (will prompt if not provided)")
    p.add_argument("-o", "--output-dir", required=False, help="Where to save PNGs and .npz (defaults to input dir)")
    p.add_argument("--pattern", default="*.mat", help="Filename glob pattern (default: *.mat)")
    p.add_argument("--invert", action="store_true", help="Invert sign of power values (useful for dips/inverted peaks)")
    p.add_argument("--start", type=int, default=0, help="Start index into the sorted file list (default 0)")
    p.add_argument("--stop", type=int, default=None, help="Stop index into file list (python slicing semantics)")
    p.add_argument("--step", type=int, default=1, help="Step between files (default 1)")
    p.add_argument("--cmap", default="inferno", help="Matplotlib colormap name (default: inferno)")
    p.add_argument("--save-npz", action="store_true", help="Save stacked spectrograms as spectrograms.npz")
    p.add_argument("--benchtop", action="store_true", help="Run benchtop CSV -> spectrogram workflow")
    p.add_argument("--onchip", action="store_true", help="Run on-chip LIV+OSA -> spectrogram workflow")
    p.add_argument("--osa-file", type=str, default=None, help="Path to OSA .mat file (on-chip workflow)")
    p.add_argument("--liv-dir", type=str, default=None, help="Path to LIV directory (on-chip workflow)")
    p.add_argument("--wl-min", type=float, default=None, help="Minimum wavelength to include (benchtop)")
    p.add_argument("--wl-max", type=float, default=None, help="Maximum wavelength to include (benchtop)")
    p.add_argument("--save-mat", action="store_true", help="Save a .mat with stacked benchtop spectrogram data")
    p.add_argument("--interactive", action="store_true", help="Open an interactive pyqtgraph viewer for spectrograms")
    p.add_argument("--peak-overlay", action="store_true", help="Detect peaks per sweep and overlay them on the interactive viewer")
    args = p.parse_args()

    input_dir = os.path.abspath(args.input_dir) if args.input_dir else None
    # Determine output_dir safely: prefer explicit arg, else use input_dir, else cwd
    if args.output_dir:
        output_dir = os.path.abspath(args.output_dir)
    else:
        output_dir = os.path.abspath(input_dir) if input_dir else os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    # If no input or mode specified, prompt the user to choose a workflow so the script
    # can be used interactively without command-line flags.
    if not args.benchtop and not args.onchip and input_dir is None:
        root = tk.Tk()
        root.withdraw()
        
        print("\n" + "="*60)
        print("IMPORTANT: A dialog window is about to appear!")
        print("Please check your taskbar or alt-tab if you don't see it.")
        print("="*60 + "\n")
        
        # Create dialog for analysis type selection
        def ask_analysis_type(parent):
            try:
                parent.deiconify()
                parent.lift()
                parent.focus_force()
                parent.attributes('-topmost', True)
                parent.update()
            except Exception:
                pass

            dialog = tk.Toplevel(parent)
            dialog.title('Select data type to analyse')
            dialog.transient(parent)
            dialog.attributes('-topmost', True)
            dialog.lift()
            dialog.focus_force()
            dialog.update()
            dialog.minsize(300, 200)
            dialog.grab_set()

            var = tk.StringVar(value='benchtop')

            tk.Label(dialog, text='Which data type would you like to analyse?').pack(padx=12, pady=(12, 4))
            rb_frame = tk.Frame(dialog)
            rb_frame.pack(padx=12, pady=4)
            tk.Radiobutton(rb_frame, text='Benchtop CSVs', variable=var, value='benchtop').pack(anchor='w')
            tk.Radiobutton(rb_frame, text='On-chip (LIV + OSA)', variable=var, value='onchip').pack(anchor='w')
            tk.Radiobutton(rb_frame, text='Eval System MAT files (power4 + end_time)', variable=var, value='mat').pack(anchor='w')

            btn_frame = tk.Frame(dialog)
            btn_frame.pack(padx=12, pady=(8, 12))

            def on_ok():
                dialog.selected = var.get()
                dialog.destroy()

            def on_cancel():
                dialog.selected = None
                dialog.destroy()

            tk.Button(btn_frame, text='OK', width=10, command=on_ok).pack(side='left', padx=6)
            tk.Button(btn_frame, text='Cancel', width=10, command=on_cancel).pack(side='left')

            # Center the dialog on screen
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'+{x}+{y}')

            def reminder():
                if dialog.winfo_exists():
                    print("\n>>> The data type selection dialog is waiting for your input! <<<")
                    print(">>> Check your taskbar or press Alt+Tab to find it <<<\n")
                    dialog.after(5000, reminder)
            
            dialog.after(5000, reminder)
            parent.wait_window(dialog)
            selected = getattr(dialog, 'selected', None)
            
            # Console fallback
            if not selected:
                print('\n' + '='*60)
                print('Data Type Selection')
                print('='*60)
                print('No GUI selection detected. Please select data type:')
                print('  1) Benchtop CSVs')
                print('  2) On-chip (not implemented)')
                print('  3) MAT files')
                try:
                    choice = input('Enter choice (1, 2, 3): ')
                    if choice in ('1', 'benchtop'):
                        return 'benchtop'
                    elif choice in ('2', 'onchip'):
                        return 'onchip'
                    elif choice in ('3', 'mat'):
                        return 'mat'
                except Exception:
                    pass
                return None
            
            return selected

        choice = ask_analysis_type(root)
        
        if choice == 'benchtop':
            args.benchtop = True
            input_dir = filedialog.askdirectory(title="Select Parent Directory for Benchtop CSVs")
            if not input_dir:
                logger.error("No input directory provided. Exiting.")
                root.destroy()
                sys.exit(1)
            
            # Ask for wavelength range
            wl_min_str = simpledialog.askstring("Wavelength Range", "Enter minimum wavelength (nm):", initialvalue="1330.28")
            wl_max_str = simpledialog.askstring("Wavelength Range", "Enter maximum wavelength (nm):", initialvalue="1330.92")
            
            try:
                args.wl_min = float(wl_min_str) if wl_min_str else None
                args.wl_max = float(wl_max_str) if wl_max_str else None
            except ValueError:
                logger.error("Invalid wavelength values. Using defaults.")
                args.wl_min = 1330.28
                args.wl_max = 1330.92
            
            # Ask if user wants to save .mat
            args.save_mat = messagebox.askyesno("Save MAT File", "Do you want to save a .mat file with the spectrogram data?")
            
            # If yes, ask where to save it
            if args.save_mat:
                args.mat_save_path = filedialog.asksaveasfilename(
                    title="Save Benchtop Spectrogram MAT File",
                    defaultextension=".mat",
                    filetypes=[("MAT files", "*.mat"), ("All files", "*.*")],
                    initialfile="benchtop_spectrogram.mat"
                )
                if not args.mat_save_path:
                    logger.warning("No save path selected. Will use default location in output directory.")
                    args.mat_save_path = None
            else:
                args.mat_save_path = None
            
        elif choice == 'onchip':
            # On-chip workflow
            osa_file = filedialog.askopenfilename(title="Select OSA .mat File", filetypes=[("MAT files", "*.mat"), ("All files", "*.*")])
            if not osa_file:
                logger.error("No OSA file selected. Exiting.")
                root.destroy()
                sys.exit(1)
            
            liv_dir = filedialog.askdirectory(title="Select Parent Directory for LIV .mat Files")
            if not liv_dir:
                logger.error("No LIV directory selected. Exiting.")
                root.destroy()
                sys.exit(1)
            
            # Ask if user wants to save .mat
            save_mat_onchip = messagebox.askyesno("Save MAT File", "Do you want to save a .mat file with the spectrogram data?")
            
            # Set output directory
            output_dir = filedialog.askdirectory(title="Select Output Directory (or cancel for default)")
            if not output_dir:
                output_dir = os.path.dirname(osa_file)
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Process on-chip data
            process_onchip_folder(osa_file, liv_dir, output_dir, save_mat=save_mat_onchip)
            logger.info("Done (on-chip)")
            root.destroy()
            sys.exit(0)
            
        elif choice == 'mat':
            # Eval system workflow with end_time timestamps and inverted power4
            osa_file = filedialog.askopenfilename(
                title="Select OSA .mat File", 
                filetypes=[("MAT files", "*.mat"), ("All files", "*.*")]
            )
            if not osa_file:
                logger.error("No OSA file selected. Exiting.")
                root.destroy()
                sys.exit(1)
            
            evalsys_dir = filedialog.askdirectory(
                title="Select Parent Directory for Eval System .mat Files"
            )
            if not evalsys_dir:
                logger.error("No eval system directory selected. Exiting.")
                root.destroy()
                sys.exit(1)
            
            # Ask if user wants to save .mat
            save_mat_evalsys = messagebox.askyesno(
                "Save MAT File", 
                "Do you want to save a .mat file with the spectrogram data?"
            )
            
            # Set output directory
            output_dir = filedialog.askdirectory(
                title="Select Output Directory (or cancel for default)"
            )
            if not output_dir:
                output_dir = os.path.dirname(osa_file)
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Process eval system data
            process_evalsys_folder(osa_file, evalsys_dir, output_dir, save_mat=save_mat_evalsys)
            logger.info("Done (eval system)")
            root.destroy()
            sys.exit(0)
            
        else:
            logger.error("No data type selected. Exiting.")
            root.destroy()
            sys.exit(1)
        
        root.destroy()

    # On-chip workflow
    if args.onchip:
        if args.osa_file is None:
            root = tk.Tk()
            root.withdraw()
            args.osa_file = filedialog.askopenfilename(title="Select OSA .mat File", filetypes=[("MAT files", "*.mat"), ("All files", "*.*")])
            if not args.osa_file:
                logger.error("No OSA file selected. Exiting.")
                root.destroy()
                sys.exit(1)
            root.destroy()
        
        if args.liv_dir is None:
            root = tk.Tk()
            root.withdraw()
            args.liv_dir = filedialog.askdirectory(title="Select Parent Directory for LIV .mat Files")
            if not args.liv_dir:
                logger.error("No LIV directory selected. Exiting.")
                root.destroy()
                sys.exit(1)
            root.destroy()
        
        output_dir = os.path.abspath(args.output_dir) if args.output_dir else os.path.dirname(args.osa_file)
        os.makedirs(output_dir, exist_ok=True)
        process_onchip_folder(args.osa_file, args.liv_dir, output_dir, save_mat=args.save_mat)
        logger.info("Done (on-chip)")
        return

    # Benchtop workflow
    if args.benchtop:
        if input_dir is None:
            root = tk.Tk()
            root.withdraw()
            input_dir = filedialog.askdirectory(title="Select Parent Directory for Benchtop CSVs")
            if not input_dir:
                logger.error("No input directory provided. Exiting.")
                root.destroy()
                sys.exit(1)
            
            # Ask for wavelength range if not provided via CLI
            if args.wl_min is None:
                wl_min_str = simpledialog.askstring("Wavelength Range", "Enter minimum wavelength (nm):", initialvalue="1330.28")
                try:
                    args.wl_min = float(wl_min_str) if wl_min_str else 1330.28
                except ValueError:
                    args.wl_min = 1330.28
            
            if args.wl_max is None:
                wl_max_str = simpledialog.askstring("Wavelength Range", "Enter maximum wavelength (nm):", initialvalue="1330.92")
                try:
                    args.wl_max = float(wl_max_str) if wl_max_str else 1330.92
                except ValueError:
                    args.wl_max = 1330.92
            
            # Ask if user wants to save .mat if not specified via CLI
            if not args.save_mat:
                args.save_mat = messagebox.askyesno("Save MAT File", "Do you want to save a .mat file with the spectrogram data?")
            
            # If yes, ask where to save it
            if args.save_mat and not hasattr(args, 'mat_save_path'):
                args.mat_save_path = filedialog.asksaveasfilename(
                    title="Save Benchtop Spectrogram MAT File",
                    defaultextension=".mat",
                    filetypes=[("MAT files", "*.mat"), ("All files", "*.*")],
                    initialfile="benchtop_spectrogram.mat"
                )
                if not args.mat_save_path:
                    logger.warning("No save path selected. Will use default location in output directory.")
                    args.mat_save_path = None
            
            root.destroy()
            
        output_dir = os.path.abspath(args.output_dir) if args.output_dir else os.path.abspath(input_dir)
        
        # If user provided a custom mat_save_path, use its directory as output_dir for all plots
        mat_path = getattr(args, 'mat_save_path', None)
        if mat_path:
            output_dir = os.path.dirname(os.path.abspath(mat_path))
            logger.info(f"Using directory of .mat file as output directory: {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        process_benchtop_folder(input_dir, output_dir, args.wl_min, args.wl_max, save_mat=args.save_mat, mat_save_path=mat_path)
        logger.info("Done (benchtop)")
        return

    # collect files
    if input_dir is None:
        logger.error("Input directory must be provided (use -i/--input-dir) unless --benchtop is used")
        sys.exit(1)
    files = [os.path.join(input_dir, f) for f in sorted(os.listdir(input_dir)) if f.lower().endswith(args.pattern.replace("*","")) or f.lower().endswith('.mat')]
    # more robust: use glob
    if not files:
        import glob
        files = glob.glob(os.path.join(input_dir, args.pattern))
        files = sorted(files)

    if not files:
        logger.error("No .mat files found in input dir")
        sys.exit(1)

    logger.info(f"Found {len(files)} files, using start={args.start}, stop={args.stop}, step={args.step}")

    spec_list, wavelength = build_spectrograms(files, invert=args.invert, start=args.start, stop=args.stop, step=args.step)

    # Save per-channel PNGs
    for i, spec in enumerate(spec_list):
        out_png = os.path.join(output_dir, f"spectrogram_channel_{i+1}.png")
        plot_and_save(spec, wavelength, out_png, title=f"Channel {i+1}", cmap=args.cmap)

    # Optionally save npz
    if args.save_npz:
        npz_path = os.path.join(output_dir, "spectrograms.npz")
        # stack spectrograms into array shape (channels, time, wavelength)
        stacked = np.stack(spec_list, axis=0)
        np.savez_compressed(npz_path, spectrograms=stacked, wavelength=wavelength)
        logger.info(f"Saved spectrograms npz to {npz_path}")

    # Interactive viewer
    if args.interactive:
        if not _HAS_PYQT:
            logger.error(
                "Interactive mode requested but pyqtgraph/PySide6 are not installed.\n"
                "Install them in your environment with: python -m pip install pyqtgraph PySide6"
            )
            sys.exit(1)

        def show_interactive(spec_list, wavelength, cmap=args.cmap, peak_overlay=args.peak_overlay, invert=args.invert):
            app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            win = QtWidgets.QMainWindow()
            win.setWindowTitle("Spectrogram Viewer")
            central = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout()
            central.setLayout(layout)
            tabs = pg.QtWidgets.QTabWidget()
            layout.addWidget(tabs)

            for i, spec in enumerate(spec_list):
                # Create pyqtgraph ImageView
                plot = pg.PlotItem()
                plot.setLabels(left=("Wavelength", ""), bottom=("Sweep index", ""))
                img = pg.ImageView(view=plot)
                img.ui.roiBtn.hide()
                img.ui.menuBtn.hide()
                img.getView().invertY(False)
                img.getView().setAspectLocked(False)
                img.setColorMap(pg.colormap.getFromMatplotlib(cmap))
                # setImage expects (rows=x, cols=y) -> we pass spec (time x wavelength)
                img.setImage(spec)

                # add peak overlay if requested
                if peak_overlay:
                    scatter = pg.ScatterPlotItem(size=6, pen=pg.mkPen('w'), brush=pg.mkBrush(255,255,255,120))
                    tabs_widget = QtWidgets.QWidget()
                    vlayout = QtWidgets.QVBoxLayout()
                    tabs_widget.setLayout(vlayout)
                    vlayout.addWidget(img)

                    # detect peaks per time slice
                    for t in range(spec.shape[0]):
                        spectrum = spec[t]
                        arr = -spectrum if invert else spectrum
                        try:
                            peaks, _ = find_peaks(arr)
                        except Exception:
                            peaks = []
                        if len(peaks) > 0:
                            xs = [t] * len(peaks)
                            ys = wavelength[peaks]
                            pts = [{'x': x, 'y': y} for x, y in zip(xs, ys)]
                            scatter.addPoints(pts)
                    img.view.addItem(scatter)
                    tabs.addTab(tabs_widget, f"Channel {i+1}")
                else:
                    tabs.addTab(img, f"Channel {i+1}")

            win.setCentralWidget(central)
            win.resize(1000, 800)
            win.show()
            app.exec()

        show_interactive(spec_list, wavelength)

    logger.info("Done")

if __name__ == "__main__":
    main()
#%%
# ============================================================================
# SECTION: Plot Normalized Spectrogram from Saved .mat File
# ============================================================================

def create_white_to_colormap(color_name: str = 'red'):
    """Create a colormap that starts from white and transitions to a target color.
    
    Args:
        color_name: Name of the target color ('red', 'orange', 'yellow', 'purple', 'blue', 'green')
    
    Returns:
        matplotlib colormap
    """
    from matplotlib.colors import LinearSegmentedColormap
    
    # Define custom colormaps that start from white
    if color_name == 'red':
        cdict = {
            'red': [(0.0, 1.0, 1.0), (0.5, 1.0, 1.0), (1.0, 0.8, 0.8)],
            'green': [(0.0, 1.0, 1.0), (0.5, 0.7, 0.7), (1.0, 0.0, 0.0)],
            'blue': [(0.0, 1.0, 1.0), (0.5, 0.7, 0.7), (1.0, 0.0, 0.0)]
        }
    elif color_name == 'orange':
        cdict = {
            'red': [(0.0, 1.0, 1.0), (0.5, 1.0, 1.0), (1.0, 0.8, 0.8)],
            'green': [(0.0, 1.0, 1.0), (0.5, 0.8, 0.8), (1.0, 0.4, 0.4)],
            'blue': [(0.0, 1.0, 1.0), (0.5, 0.5, 0.5), (1.0, 0.0, 0.0)]
        }
    elif color_name == 'yellow':
        cdict = {
            'red': [(0.0, 1.0, 1.0), (1.0, 1.0, 1.0)],
            'green': [(0.0, 1.0, 1.0), (1.0, 0.8, 0.8)],
            'blue': [(0.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
        }
    elif color_name == 'purple':
        cdict = {
            'red': [(0.0, 1.0, 1.0), (0.5, 0.9, 0.9), (1.0, 0.5, 0.5)],
            'green': [(0.0, 1.0, 1.0), (0.5, 0.7, 0.7), (1.0, 0.0, 0.0)],
            'blue': [(0.0, 1.0, 1.0), (0.5, 1.0, 1.0), (1.0, 0.8, 0.8)]
        }
    else:  # blue
        cdict = {
            'red': [(0.0, 1.0, 1.0), (1.0, 0.0, 0.0)],
            'green': [(0.0, 1.0, 1.0), (1.0, 0.5, 0.5)],
            'blue': [(0.0, 1.0, 1.0), (1.0, 1.0, 1.0)]
        }
    
    return LinearSegmentedColormap('white_to_' + color_name, cdict)


def plot_normalized_spectrogram_from_mat(
    mat_path: str,
    output_path: str,
    wl_min: Optional[float] = None,
    wl_max: Optional[float] = None,
    title: str = "Normalized Spectrogram",
    cmap: str = "YlOrRd"
):
    """Load a saved spectrogram .mat file and plot with normalized power axis.
    
    This function loads a previously saved spectrogram .mat file and creates
    a new plot with power normalized to [0, 1] range. The plot uses the same
    font sizes as other spectrograms in this script.
    
    Args:
        mat_path: Path to the .mat file containing spectrogram data
        output_path: Path where the output PNG will be saved
        wl_min: Minimum wavelength for plotting range (optional, uses data min if None)
        wl_max: Maximum wavelength for plotting range (optional, uses data max if None)
        title: Title for the plot
        cmap: Colormap name. Use 'white_to_red', 'white_to_orange', 'white_to_blue', 'white_to_purple', 
              'white_to_yellow', 'white_to_green' for custom white-based colormaps.
              Or use standard matplotlib names like 'YlOrRd', 'YlOrBr', 'Blues', 'Greys', 'Oranges', etc.
    
    Example usage:
        # With custom white-to-red colormap
        plot_normalized_spectrogram_from_mat(
            mat_path=r"C:\path\to\benchtop_spectrogram.mat",
            output_path=r"C:\path\to\output.png",
            cmap='white_to_red'
        )
            wl_max=1330.9,
            title="On-chip Normalized Spectrogram"
        )
    """
    logger.info(f"Loading spectrogram from: {mat_path}")
    
    # Load the .mat file
    try:
        data = loadmat(mat_path, squeeze_me=True, struct_as_record=False)
    except Exception as e:
        logger.error(f"Failed to load .mat file: {e}")
        return
    
    # Extract power data (try multiple possible keys)
    powers = None
    for key in ['powers', 'spec', 'power', 'data']:
        if key in data:
            powers = np.array(data[key])
            logger.info(f"Found power data under key '{key}'")
            break
    
    if powers is None:
        logger.error(f"Could not find power data in .mat file. Available keys: {list(data.keys())}")
        return
    
    # Extract wavelength data
    wavelength = None
    for key in ['wavelength', 'ref_wl', 'wl', 'lambda']:
        if key in data:
            wavelength = np.array(data[key]).flatten()
            logger.info(f"Found wavelength data under key '{key}'")
            break
    
    if wavelength is None:
        logger.error(f"Could not find wavelength data in .mat file. Available keys: {list(data.keys())}")
        return
    
    # Extract time data
    rel_minutes = None
    for key in ['rel_minutes', 'times', 'time', 'rel_seconds']:
        if key in data:
            times_data = np.array(data[key]).flatten()
            if key == 'rel_seconds':
                rel_minutes = times_data / 60.0
            else:
                rel_minutes = times_data
            logger.info(f"Found time data under key '{key}'")
            break
    
    if rel_minutes is None:
        logger.warning("Could not find time data, using sweep indices instead")
        rel_minutes = np.arange(powers.shape[0])
    
    logger.info(f"Loaded spectrogram: shape={powers.shape}, wavelength range=[{wavelength.min():.4f}, {wavelength.max():.4f}] nm")
    
    # Apply wavelength range filter if specified
    if wl_min is not None or wl_max is not None:
        wl_min_use = wl_min if wl_min is not None else wavelength.min()
        wl_max_use = wl_max if wl_max is not None else wavelength.max()
        
        # Find indices within the specified range
        wl_mask = (wavelength >= wl_min_use) & (wavelength <= wl_max_use)
        wavelength = wavelength[wl_mask]
        powers = powers[:, wl_mask]
        
        logger.info(f"Filtered to wavelength range [{wl_min_use:.4f}, {wl_max_use:.4f}] nm")
        logger.info(f"New shape: {powers.shape}")
    
    # Normalize power to [0, 1] range
    power_min = np.min(powers)
    power_max = np.max(powers)
    powers_normalized = (powers - power_min) / (power_max - power_min)
    
    logger.info(f"Normalized power from [{power_min:.6f}, {power_max:.6f}] to [0.0, 1.0]")
    
    # Create the plot with white background
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
    ax.set_facecolor('white')
    
    # Set up extent for imshow
    # With origin="lower", bottom of image (row 0) maps to extent[2], top (row -1) maps to extent[3]
    extent = [rel_minutes.min(), rel_minutes.max(), wavelength[0], wavelength[-1]]
    
    # Use custom white-based colormap if requested, otherwise use standard matplotlib colormap
    if cmap.startswith('white_to_'):
        color_name = cmap.replace('white_to_', '')
        cmap_obj = create_white_to_colormap(color_name)
    else:
        cmap_obj = cmap
    
    # Plot the normalized spectrogram
    im = ax.imshow(powers_normalized.T, aspect="auto", origin="lower", cmap=cmap_obj, extent=extent)
    
    ax.set_xlabel("Time (min)", fontsize=PLOT_FONT_AXIS_LABEL, color='black')
    ax.set_ylabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, color='black')
    ax.set_title(title, fontsize=PLOT_FONT_TITLE, color='black')
    ax.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS, colors='black')
    
    # Set spine colors to black for better contrast
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1.0)
    
    # Show full numeric wavelength ticks (no offset/scientific notation)
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter(useOffset=False))
    ax.ticklabel_format(style='plain', axis='y')
    
    # Add colorbar with normalized scale
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Normalized Power", fontsize=PLOT_FONT_AXIS_LABEL)
    cbar.ax.tick_params(labelsize=PLOT_FONT_AXIS_TICKS)
    cbar.ax.set_facecolor('white')
    
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    
    logger.info(f"Saved normalized spectrogram to: {output_path}")


if __name__ == "__main__":
    main()

# %%
# ============================================================================
# Example Usage: Plot Normalized Spectrogram from Saved .mat File
# ============================================================================

import importlib
import sys

# Force reload of the module to ensure latest changes are used
if 'plot_spectrograms' in sys.modules:
    importlib.reload(sys.modules['plot_spectrograms'])

from plot_spectrograms import plot_normalized_spectrogram_from_mat

# Example 1: Using custom white-to-red colormap (starts white, ends dark red)
plot_normalized_spectrogram_from_mat(
    mat_path=r"C:\Users\jsheri1\Desktop\20251107_SiEPICfab_Shuksan_24_02_RepeatedSweeps\Final Stability\New RA_analysis\Trial01\benchtop_spectrogram.mat",
    output_path=r"C:\Users\jsheri1\Desktop\Analysis\normalized_benchtop_spectrogram.png",
   # wl_min=1330.3,
    #wl_max=1330.9,
    title="Benchtop spectrogram - standalone sweeps",
    cmap='YlOrBr'  # Custom colormap: white → orange
)

# Example 2: Using custom white-to-orange colormap
# plot_normalized_spectrogram_from_mat(
#     mat_path=r"...",
#     output_path=r"...",
#     cmap='white_to_orange'
# )

# Example 3: Using standard matplotlib colormap (YlOrRd)
# plot_normalized_spectrogram_from_mat(
#     mat_path=r"...",
#     output_path=r"...",
#     cmap='YlOrRd'

# %%
