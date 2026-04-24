"""
Eval System Lorentzian Peak Fitter

This module implements the fitting approach from evalsys_vs_benchtopQ.py
for automated batch processing of eval system power4 data.

Key differences from benchtop/on-chip:
- Data is ALREADY INVERTED (peaks pointing up)
- Data is ALREADY NORMALIZED to [0, 1]
- Uses polynomial baseline correction (like interactive mode)
- More aggressive smoothing for noisy eval system data

Author: Derived from evalsys_vs_benchtopQ.py baseline correction
Date: 2025-11-13
"""

import numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Try to import lorentzfit
try:
    from lorentzfit import lorentzfit
    LORENTZFIT_AVAILABLE = True
except ImportError:
    LORENTZFIT_AVAILABLE = False
    logger.warning("lorentzfit module not available - Lorentzian fitting will fail")


def fit_single_peak_evalsys_style(wavelength: np.ndarray,
                                   power: np.ndarray,
                                   peak_idx: int,
                                   left_baseline_window: int = 10,
                                   right_baseline_window: int = 10,
                                   peak_window: int = 15,
                                   poly_order: int = 1) -> Optional[Dict]:
    """
    Fit a single peak using eval system baseline correction approach.
    
    This implements the approach from analyze_peak_with_adjustable_baseline()
    in evalsys_vs_benchtopQ.py:
    1. Define peak region window
    2. Use points OUTSIDE peak window for baseline (left/right wings)
    3. Fit polynomial to baseline points
    4. Subtract baseline from peak region
    5. Normalize to [0, 1]
    6. Fit Lorentzian
    
    Args:
        wavelength: Full wavelength array [nm]
        power: Full power array (already inverted and normalized to [0,1])
        peak_idx: Index of peak center
        left_baseline_window: Points to use for left baseline (OUTSIDE peak)
        right_baseline_window: Points to use for right baseline (OUTSIDE peak)
        peak_window: Half-width of peak region (points on each side of peak)
        poly_order: Polynomial order for baseline (1=linear, 2=quadratic)
    
    Returns:
        Dict with fit results or None if fit fails
    """
    if not LORENTZFIT_AVAILABLE:
        logger.error("lorentzfit not available")
        return None
    
    # Define peak region
    left_idx = max(0, peak_idx - peak_window)
    right_idx = min(len(wavelength), peak_idx + peak_window + 1)
    peak_x = wavelength[left_idx:right_idx]
    peak_y = power[left_idx:right_idx]
    
    if len(peak_x) < 5:
        logger.warning(f"Peak region too small: {len(peak_x)} points")
        return None
    
    # Define baseline regions OUTSIDE the peak window
    baseline_left_start = max(0, left_idx - left_baseline_window)
    baseline_left_end = left_idx
    baseline_right_start = right_idx
    baseline_right_end = min(len(wavelength), right_idx + right_baseline_window)
    
    # Collect baseline points from wings
    baseline_x_left = wavelength[baseline_left_start:baseline_left_end]
    baseline_y_left = power[baseline_left_start:baseline_left_end]
    baseline_x_right = wavelength[baseline_right_start:baseline_right_end]
    baseline_y_right = power[baseline_right_start:baseline_right_end]
    
    # Combine left and right baseline points
    baseline_x = np.concatenate([baseline_x_left, baseline_x_right])
    baseline_y = np.concatenate([baseline_y_left, baseline_y_right])
    
    # Fit baseline polynomial
    if len(baseline_x) >= poly_order + 1:
        try:
            p = np.polyfit(baseline_x, baseline_y, poly_order)
            baseline_peak = np.polyval(p, peak_x)
        except np.linalg.LinAlgError:
            # Fallback to linear baseline using peak endpoints
            logger.debug(f"Polynomial baseline failed, using linear fallback for peak at idx={peak_idx}")
            slope = (peak_y[-1] - peak_y[0]) / (peak_x[-1] - peak_x[0])
            baseline_peak = slope * (peak_x - peak_x[0]) + peak_y[0]
    else:
        # Not enough baseline points, use linear fallback
        logger.debug(f"Not enough baseline points ({len(baseline_x)}), using linear fallback")
        slope = (peak_y[-1] - peak_y[0]) / (peak_x[-1] - peak_x[0])
        baseline_peak = slope * (peak_x - peak_x[0]) + peak_y[0]
    
    # Subtract baseline
    normalized_curve = peak_y - baseline_peak
    
    # Normalize to [0, 1] with peaks pointing UP
    ymin = np.min(normalized_curve)
    ymax = np.max(normalized_curve)
    
    if (ymax - ymin) <= 1e-9:
        logger.warning(f"Peak at λ={wavelength[peak_idx]:.4f} nm has zero range after baseline correction")
        return None
    
    normalized_curve_lin = (normalized_curve - ymin) / (ymax - ymin)
    
    # Fit Lorentzian
    try:
        # Initial guess (upward peak)
        peak_height = np.max(normalized_curve_lin) - np.min(normalized_curve_lin)
        peak_center = peak_x[np.argmax(normalized_curve_lin)]
        peak_width = (peak_x[-1] - peak_x[0]) / 10
        baseline_level = np.min(normalized_curve_lin)
        
        p0_guess = [peak_height, peak_center, peak_width**2, baseline_level]
        
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
        'power': power[peak_idx],  # Original peak power
        'Q': Q_factor,
        'R2': R_sq,
        'FWHM': gamma,
        'params': params  # [A, x0, gamma, C]
    }


def fit_all_peaks_evalsys_style(wavelength: np.ndarray,
                                 power: np.ndarray,
                                 gaussian_filter_sigma: float = 6.0,
                                 prominence_scaler: float = 0.12,
                                 r2_threshold: float = 0.85,
                                 left_baseline_window: int = 10,
                                 right_baseline_window: int = 10,
                                 peak_window: int = 15,
                                 poly_order: int = 1) -> List[Dict]:
    """
    Detect and fit all peaks in a single eval system sweep.
    
    Args:
        wavelength: Wavelength array [nm]
        power: Power array (already inverted & normalized to [0,1])
        gaussian_filter_sigma: Smoothing for peak detection
        prominence_scaler: Minimum peak prominence relative to range
        r2_threshold: Minimum R² to accept a fit
        left_baseline_window: Points for left baseline wing
        right_baseline_window: Points for right baseline wing
        peak_window: Half-width of peak region
        poly_order: Baseline polynomial order
    
    Returns:
        List of fit result dicts for valid peaks
    """
    if not LORENTZFIT_AVAILABLE:
        logger.error("lorentzfit not available")
        return []
    
    # Smooth for peak detection (more aggressive for noisy eval data)
    power_smoothed = gaussian_filter1d(power, sigma=gaussian_filter_sigma)
    
    # Detect peaks
    power_range = np.max(power_smoothed) - np.min(power_smoothed)
    min_prominence = prominence_scaler * power_range
    
    peaks, properties = find_peaks(power_smoothed, prominence=min_prominence, width=3)
    
    if len(peaks) == 0:
        logger.debug("No peaks detected in eval system sweep")
        return []
    
    logger.debug(f"Found {len(peaks)} candidate peaks in eval system sweep")
    
    # Fit each peak
    valid_peaks = []
    for peak_idx in peaks:
        result = fit_single_peak_evalsys_style(
            wavelength, power, peak_idx,
            left_baseline_window=left_baseline_window,
            right_baseline_window=right_baseline_window,
            peak_window=peak_window,
            poly_order=poly_order
        )
        
        if result is not None and result['R2'] >= r2_threshold:
            valid_peaks.append(result)
            logger.debug(f"  ✓ Peak at λ={result['wavelength']:.4f} nm: Q={result['Q']:.1f}, R²={result['R2']:.3f}")
        elif result is not None:
            logger.debug(f"  ✗ Rejected peak at λ={result['wavelength']:.4f} nm: R²={result['R2']:.3f} < {r2_threshold}")
    
    logger.info(f"Accepted {len(valid_peaks)}/{len(peaks)} eval system peaks (R² >= {r2_threshold})")
    
    return valid_peaks


def fit_and_track_evalsys_sweeps(spec: np.ndarray,
                                  wavelength: np.ndarray,
                                  gaussian_filter_sigma: float = 6.0,
                                  prominence_scaler: float = 0.12,
                                  r2_threshold: float = 0.85,
                                  left_baseline_window: int = 10,
                                  right_baseline_window: int = 10,
                                  peak_window: int = 15,
                                  poly_order: int = 1,
                                  min_trace_length: int = 10) -> Dict:
    """
    Fit and track peaks across multiple eval system sweeps.
    
    This uses the same clustering approach as benchtop/on-chip but with
    eval-system-specific baseline correction.
    
    Args:
        spec: 2D array (time x wavelength) of power values (already inverted & normalized)
        wavelength: 1D wavelength array [nm]
        gaussian_filter_sigma: Smoothing parameter
        prominence_scaler: Peak prominence threshold
        r2_threshold: Minimum R² to accept fit
        left_baseline_window: Baseline window size (left)
        right_baseline_window: Baseline window size (right)
        peak_window: Peak region half-width
        poly_order: Baseline polynomial order
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
        peaks = fit_all_peaks_evalsys_style(
            wavelength, power,
            gaussian_filter_sigma=gaussian_filter_sigma,
            prominence_scaler=prominence_scaler,
            r2_threshold=r2_threshold,
            left_baseline_window=left_baseline_window,
            right_baseline_window=right_baseline_window,
            peak_window=peak_window,
            poly_order=poly_order
        )
        all_sweep_peaks.append(peaks)
        n_peaks_per_sweep.append(len(peaks))
    
    logger.info(f"Eval system peak counts per sweep: min={min(n_peaks_per_sweep) if n_peaks_per_sweep else 0}, "
                f"max={max(n_peaks_per_sweep) if n_peaks_per_sweep else 0}, "
                f"mean={np.mean(n_peaks_per_sweep):.1f}")
    
    # Collect all wavelengths
    all_wavelengths = []
    for peaks in all_sweep_peaks:
        all_wavelengths.extend([p['wavelength'] for p in peaks])
    
    if len(all_wavelengths) == 0:
        logger.warning("No peaks found in any eval system sweep")
        return {
            'centers': np.full(n_sweeps, np.nan),
            'all_peak_traces': [],
            'fsr_stats': {'mean': None, 'std': None}
        }
    
    # Estimate FSR from first sweep with multiple peaks
    estimated_fsr = 0.0001  # Default fallback (0.1 pm)
    for peaks in all_sweep_peaks:
        if len(peaks) > 1:
            wls = sorted([p['wavelength'] for p in peaks])
            estimated_fsr = np.median(np.diff(wls))
            break
    
    if estimated_fsr == 0.0001:
        # No multi-peak sweep found, use global wavelength distribution
        all_wavelengths_sorted = sorted(all_wavelengths)
        if len(all_wavelengths_sorted) > 1:
            estimated_fsr = np.median(np.diff(all_wavelengths_sorted))
    
    # Clustering threshold: FSR/4
    cluster_threshold = estimated_fsr / 4.0
    logger.info(f"Estimated FSR: {estimated_fsr*1000:.1f} pm, cluster threshold: {cluster_threshold*1000:.1f} pm")
    
    # Identify stable peak positions by clustering
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
    
    logger.info(f"Tracked {len(peak_traces)} eval system peak traces (min_length={min_trace_length})")
    
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
