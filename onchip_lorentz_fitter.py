"""
On-Chip Lorentzian Peak Fitter
Similar to benchtop_lorentz_fitter.py but adapted for on-chip LIV data.

On-chip data characteristics:
- X-axis: Current (mA) - converted to wavelength via polynomial from OSA
- Y-axis: Power (mW) - linear scale from LIV measurements
- Uses same baseline correction approach as benchtop

Author: AI Assistant
Date: 2025-11-12
"""

import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d

logger = logging.getLogger(__name__)

try:
    from lorentzfit import lorentzfit
    LORENTZFIT_AVAILABLE = True
except ImportError:
    LORENTZFIT_AVAILABLE = False
    logger.warning("lorentzfit not available - Lorentzian fitting will not work")


def fit_single_peak_onchip_style(wavelength: np.ndarray,
                                  power: np.ndarray,
                                  peak_idx: int,
                                  window: int = 15) -> Optional[Dict]:
    """
    Fit a single peak using on-chip baseline correction approach.
    Same methodology as benchtop but adapted for on-chip data structure.
    
    Args:
        wavelength: Wavelength array [nm] (derived from current via polynomial)
        power: Power array [mW] (linear scale from LIV)
        peak_idx: Index of peak center
        window: Number of points on each side of peak
        
    Returns:
        Dictionary with fit results or None if fit fails
    """
    if not LORENTZFIT_AVAILABLE:
        logger.error("lorentzfit module not available")
        return None
    
    # Extract peak region
    left = max(0, peak_idx - window)
    right = min(len(wavelength), peak_idx + window + 1)
    peak_x = wavelength[left:right]
    peak_y = power[left:right]
    
    if len(peak_x) < 8:
        logger.warning(f"Peak region too small: {len(peak_x)} points")
        return None
    
    # Step 1: Linear baseline from endpoints
    slope = (peak_y[-1] - peak_y[0]) / (peak_x[-1] - peak_x[0])
    baseline = slope * (peak_x - peak_x[0]) + peak_y[0]
    
    # Step 2: Subtract baseline
    baseline_corrected = peak_y - baseline
    
    # Step 3: Normalize to [0, 1] for Lorentzian fitting (keeping peaks pointing UP)
    ymin = np.min(baseline_corrected)
    ymax = np.max(baseline_corrected)
    
    if (ymax - ymin) <= 0:
        logger.warning(f"Peak at idx={peak_idx} has zero range after baseline correction")
        return None
    
    normalized_curve_lin = (baseline_corrected - ymin) / (ymax - ymin)
    
    # Step 4: Fit Lorentzian (upward peak)
    try:
        p0_guess = [
            np.max(normalized_curve_lin) - np.min(normalized_curve_lin),  # A (amplitude)
            peak_x[np.argmax(normalized_curve_lin)],  # x0 (center wavelength)
            (peak_x[-1] - peak_x[0]) / 10,  # gamma (width parameter)
            np.min(normalized_curve_lin)  # C (baseline offset)
        ]
        
        yfit, params, resnorm, residual = lorentzfit(
            peak_x, normalized_curve_lin, p0=p0_guess, nparams='3c'
        )
    except Exception as e:
        logger.warning(f"Lorentzian fit failed for peak at λ={wavelength[peak_idx]:.4f} nm: {e}")
        return None
    
    # Extract fit parameters
    x0 = params[1]  # Peak center wavelength
    gamma = np.sqrt(abs(params[2])) * 2  # FWHM = 2*sqrt(gamma)
    Q_factor = x0 / gamma if gamma != 0 else np.nan
    R_sq = 1 - np.var(normalized_curve_lin - yfit) / np.var(normalized_curve_lin)
    
    return {
        'wavelength': x0,
        'power': power[peak_idx],  # Original peak power (not normalized)
        'Q': Q_factor,
        'R2': R_sq,
        'FWHM': gamma,
        'params': params  # [A, x0, gamma, C]
    }


def fit_all_peaks_onchip_style(wavelength: np.ndarray,
                                power: np.ndarray,
                                gaussian_filter_sigma: float = 8.0,
                                prominence_scaler: float = 0.1,
                                r2_threshold: float = 0.85,
                                window: int = 15) -> List[Dict]:
    """
    Detect and fit all peaks in a single on-chip sweep using baseline approach.
    
    Args:
        wavelength: Wavelength array [nm]
        power: Power array [mW] (linear scale)
        gaussian_filter_sigma: Sigma for Gaussian smoothing
        prominence_scaler: Minimum prominence as fraction of max power
        r2_threshold: Minimum R² to accept fit
        window: Window size for peak fitting
        
    Returns:
        List of fit result dictionaries
    """
    if len(wavelength) != len(power):
        raise ValueError(f"Wavelength and power arrays must have same length: {len(wavelength)} vs {len(power)}")
    
    # Smooth for peak detection
    power_smoothed = gaussian_filter1d(power, sigma=gaussian_filter_sigma)
    
    # Find peaks (upward peaks in linear power data)
    min_prominence = prominence_scaler * (np.max(power_smoothed) - np.min(power_smoothed))
    peak_indices, properties = find_peaks(
        power_smoothed,
        prominence=min_prominence,
        width=1
    )
    
    logger.info(f"Found {len(peak_indices)} peaks in on-chip sweep")
    
    # Fit each peak
    results = []
    for peak_idx in peak_indices:
        fit_result = fit_single_peak_onchip_style(wavelength, power, peak_idx, window)
        
        if fit_result is not None and fit_result['R2'] >= r2_threshold:
            results.append(fit_result)
            logger.debug(f"  Peak at λ={fit_result['wavelength']:.4f} nm: Q={fit_result['Q']:.1f}, R²={fit_result['R2']:.3f}")
        elif fit_result is not None:
            logger.debug(f"  Rejected peak at λ={fit_result['wavelength']:.4f} nm: R²={fit_result['R2']:.3f} < {r2_threshold}")
    
    logger.info(f"Accepted {len(results)}/{len(peak_indices)} on-chip peaks (R² >= {r2_threshold})")
    
    return results


def fit_and_track_onchip_sweeps(spec: np.ndarray,
                                 wavelength: np.ndarray,
                                 gaussian_filter_sigma: float = 8.0,
                                 prominence_scaler: float = 0.1,
                                 r2_threshold: float = 0.85,
                                 window: int = 15,
                                min_trace_length: int = 10) -> Dict:
    """
    Fit and track peaks across multiple on-chip sweeps.
    
    This matches the benchtop_lorentz_fitter approach but for on-chip LIV data.
    
    Args:
        spec: 2D array (time x wavelength) of LINEAR power values [mW]
        wavelength: 1D wavelength array [nm]
        gaussian_filter_sigma: Smoothing parameter
        prominence_scaler: Peak prominence threshold
        r2_threshold: Minimum R² to accept fit
        window: Baseline fitting window size
        min_trace_length: Minimum consecutive points to keep a trace
    
    Returns:
        Dict with:
            - 'centers': 1D array of primary peak wavelengths per sweep
            - 'all_peak_traces': List of trace dicts for multi-peak tracking
            - 'fsr_stats': FSR statistics dict
    """
    n_sweeps = spec.shape[0]
    
    # Fit all peaks for each sweep
    all_sweep_peaks: List[List[Dict]] = []
    n_peaks_per_sweep = []
    
    for sweep_idx in range(n_sweeps):
        power = spec[sweep_idx, :]
        peaks = fit_all_peaks_onchip_style(
            wavelength, power,
            gaussian_filter_sigma=gaussian_filter_sigma,
            prominence_scaler=prominence_scaler,
            r2_threshold=r2_threshold,
            window=window
        )
        all_sweep_peaks.append(peaks)
        n_peaks_per_sweep.append(len(peaks))
    
    logger.info(f"On-chip peak counts per sweep: min={min(n_peaks_per_sweep) if n_peaks_per_sweep else 0}, "
                f"max={max(n_peaks_per_sweep) if n_peaks_per_sweep else 0}, "
                f"mean={np.mean(n_peaks_per_sweep):.1f}")
    
    # Get all unique wavelengths across all sweeps
    all_wavelengths = []
    for peaks in all_sweep_peaks:
        all_wavelengths.extend([p['wavelength'] for p in peaks])
    
    if len(all_wavelengths) == 0:
        logger.warning("No peaks found in any sweep")
        return {
            'centers': np.full(n_sweeps, np.nan),
            'all_peak_traces': [],
            'fsr_stats': {'mean': None, 'std': None}
        }
    
    # Estimate FSR from first sweep
    if len(all_sweep_peaks[0]) > 1:
        first_sweep_wls = sorted([p['wavelength'] for p in all_sweep_peaks[0]])
        estimated_fsr = np.median(np.diff(first_sweep_wls))
    else:
        all_wavelengths_sorted = sorted(all_wavelengths)
        estimated_fsr = np.median(np.diff(all_wavelengths_sorted)) if len(all_wavelengths_sorted) > 1 else 0.0001
    
    # Clustering threshold: FSR/4 allows jitter while preventing mixing adjacent peaks
    cluster_threshold = estimated_fsr / 4.0
    logger.info(f"Estimated FSR: {estimated_fsr*1000:.1f} pm, cluster threshold: {cluster_threshold*1000:.1f} pm")
    
    # Identify stable peak positions by clustering all wavelengths
    all_wavelengths_sorted = sorted(all_wavelengths)
    peak_clusters = []
    
    current_cluster = [all_wavelengths_sorted[0]]
    for wl in all_wavelengths_sorted[1:]:
        if wl - current_cluster[-1] < cluster_threshold:
            current_cluster.append(wl)
        else:
            peak_clusters.append(np.mean(current_cluster))
            current_cluster = [wl]
    peak_clusters.append(np.mean(current_cluster))
    
    logger.info(f"Identified {len(peak_clusters)} stable peak positions")
    
    # Track each stable peak across all sweeps
    peak_traces = []
    for cluster_wl in peak_clusters:
        trace_wavelengths = [np.nan] * n_sweeps
        trace_powers = [np.nan] * n_sweeps
        trace_Q = [np.nan] * n_sweeps
        trace_R2 = [np.nan] * n_sweeps
        trace_FWHM = [np.nan] * n_sweeps
        
        # Find closest peak to cluster center in each sweep
        for sweep_idx in range(n_sweeps):
            if len(all_sweep_peaks[sweep_idx]) == 0:
                continue
            
            min_dist = float('inf')
            best_peak = None
            
            for peak in all_sweep_peaks[sweep_idx]:
                dist = abs(peak['wavelength'] - cluster_wl)
                if dist < cluster_threshold and dist < min_dist:
                    min_dist = dist
                    best_peak = peak
            
            if best_peak is not None:
                trace_wavelengths[sweep_idx] = best_peak['wavelength']
                trace_powers[sweep_idx] = best_peak['power']
                trace_Q[sweep_idx] = best_peak['Q']
                trace_R2[sweep_idx] = best_peak['R2']
                trace_FWHM[sweep_idx] = best_peak['FWHM']
        
        # Filter by minimum trace length
        valid_count = sum(1 for w in trace_wavelengths if not np.isnan(w))
        if valid_count >= min_trace_length:
            peak_traces.append({
                'centers': np.array(trace_wavelengths),
                'powers': np.array(trace_powers),
                'Q_factors': np.array(trace_Q),
                'R_squared': np.array(trace_R2),
                'FWHM': np.array(trace_FWHM)
            })
    
    logger.info(f"Tracked {len(peak_traces)} on-chip peak traces (min_length={min_trace_length})")
    
    # Calculate FSR statistics
    fsr_values = []
    for trace in peak_traces:
        valid_wls = trace['centers'][~np.isnan(trace['centers'])]
        if len(valid_wls) > 0:
            median_wl = np.median(valid_wls)
            fsr_values.append(median_wl)
    
    if len(fsr_values) > 1:
        fsr_values = sorted(fsr_values)
        fsr_diffs = np.diff(fsr_values) * 1e3  # Convert to pm
        fsr_stats = {
            'mean': np.mean(fsr_diffs),
            'std': np.std(fsr_diffs)
        }
    else:
        fsr_stats = {'mean': None, 'std': None}
    
    # Select "best" trace for primary output
    if len(peak_traces) > 0:
        best_trace = max(peak_traces, key=lambda t: np.sum(~np.isnan(t['centers'])))
        centers = best_trace['centers']
    else:
        centers = np.full(n_sweeps, np.nan)
    
    return {
        'centers': centers,
        'all_peak_traces': peak_traces,
        'fsr_stats': fsr_stats
    }
