"""
Benchtop-specific Lorentzian peak fitting with baseline correction.

This module implements the fitting approach from Benchtop_vs_OnChip_Resonance_Analysis.py
tailored for linear power data (mW) rather than dBm OSA data.

Key differences from RA approach:
- Operates on LINEAR power data (not dBm)
- Uses linear baseline subtraction (slope fit from peak endpoints)
- Normalizes to [0,1] after baseline removal
- Fits Lorentzian to baseline-corrected data

Author: Derived from Benchtop_vs_OnChip_Resonance_Analysis.py
"""

import numpy as np
from scipy.signal import find_peaks
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


def fit_single_peak_with_baseline(wavelength: np.ndarray, 
                                   power: np.ndarray,
                                   peak_idx: int,
                                   window: int = 15) -> Optional[Dict]:
    """
    Fit a single peak with linear baseline correction.
    
    This implements the approach from analyze_peak_qfactor() in the reference script:
    1. Extract window around peak
    2. Fit linear baseline from endpoints
    3. Subtract baseline
    4. Normalize to [0, 1]
    5. Fit Lorentzian
    
    Args:
        wavelength: Full wavelength array [nm]
        power: Full power array (linear units, e.g., mW)
        peak_idx: Index of peak center in wavelength/power arrays
        window: Number of points on each side of peak (default 15)
    
    Returns:
        Dict with fit results or None if fit fails:
            - 'wavelength': fitted peak center [nm]
            - 'power': peak power (from original data)
            - 'Q': Quality factor
            - 'R2': R-squared goodness of fit
            - 'FWHM': Full width half maximum [nm]
            - 'params': Lorentzian parameters [A, x0, gamma, C]
    """
    if not LORENTZFIT_AVAILABLE:
        logger.error("lorentzfit not available")
        return None
    
    # Extract window around peak
    left = max(0, peak_idx - window)
    right = min(len(wavelength), peak_idx + window + 1)
    peak_x = wavelength[left:right]
    peak_y = power[left:right]
    
    if len(peak_x) < 5:  # Need minimum points for fitting
        logger.warning(f"Window too small ({len(peak_x)} points) for peak at idx={peak_idx}")
        return None
    
    # Step 1: Linear baseline from endpoints
    slope = (peak_y[-1] - peak_y[0]) / (peak_x[-1] - peak_x[0])
    baseline = slope * (peak_x - peak_x[0]) + peak_y[0]
    
    # Step 2: Subtract baseline
    normalized_curve = peak_y - baseline
    
    # Step 3: Normalize to [0, 1] (shift min to 0, scale max to 1)
    ymin = np.min(normalized_curve)
    normalized_curve_lin = normalized_curve - ymin
    ymax = np.max(normalized_curve_lin)
    if ymax > 0:
        normalized_curve_lin = normalized_curve_lin / ymax
    else:
        logger.warning(f"Peak at idx={peak_idx} has zero range after baseline correction")
        return None
    
    # Step 4: Fit Lorentzian
    # Initial guess for UPWARD peak (positive A)
    try:
        p0_guess = [
            np.max(normalized_curve_lin) - np.min(normalized_curve_lin),  # A
            peak_x[np.argmax(normalized_curve_lin)],  # x0 (wavelength at peak)
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


def fit_all_peaks_benchtop_style(wavelength: np.ndarray,
                                  power: np.ndarray,
                                  gaussian_filter_sigma: float = 8.0,
                                  prominence_scaler: float = 0.1,
                                  r2_threshold: float = 0.85,
                                  window: int = 15) -> List[Dict]:
    """
    Detect and fit all peaks in a single sweep using benchtop baseline approach.
    
    Args:
        wavelength: Wavelength array [nm]
        power: Power array (linear units)
        gaussian_filter_sigma: Smoothing for peak detection (ignored for now)
        prominence_scaler: Minimum peak prominence relative to max power
        r2_threshold: Minimum R² to accept a fit
        window: Window size for baseline fitting
    
    Returns:
        List of fit result dicts for valid peaks
    """
    if not LORENTZFIT_AVAILABLE:
        logger.error("lorentzfit not available")
        return []
    
    # Normalize for peak detection
    power_norm = (power - power.min()) / (power.max() - power.min() + 1e-10)
    
    # Detect peaks
    max_power = np.max(power_norm)
    peaks, properties = find_peaks(power_norm, prominence=prominence_scaler * max_power)
    
    if len(peaks) == 0:
        logger.debug("No peaks detected in sweep")
        return []
    
    # Fit each peak
    valid_peaks = []
    for peak_idx in peaks:
        result = fit_single_peak_with_baseline(wavelength, power, peak_idx, window=window)
        
        if result is not None and result['R2'] >= r2_threshold:
            valid_peaks.append(result)
    
    return valid_peaks


def fit_and_track_benchtop_sweeps(spec: np.ndarray,
                                   wavelength: np.ndarray,
                                   gaussian_filter_sigma: float = 8.0,
                                   prominence_scaler: float = 0.1,
                                   r2_threshold: float = 0.85,
                                   window: int = 15,
                                   min_trace_length: int = 10) -> Dict:
    """
    Fit and track peaks across multiple benchtop sweeps.
    
    This is a simplified tracker that matches peaks by nearest wavelength.
    Does NOT use RA's Dijkstra algorithm (which is designed for dBm data).
    
    Args:
        spec: 2D array (time x wavelength) of LINEAR power values
        wavelength: 1D wavelength array [nm]
        gaussian_filter_sigma: Smoothing parameter (currently unused)
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
        peaks = fit_all_peaks_benchtop_style(
            wavelength, power, 
            gaussian_filter_sigma=gaussian_filter_sigma,
            prominence_scaler=prominence_scaler,
            r2_threshold=r2_threshold,
            window=window
        )
        all_sweep_peaks.append(peaks)
        n_peaks_per_sweep.append(len(peaks))
    
    logger.info(f"Benchtop peak counts per sweep: min={min(n_peaks_per_sweep) if n_peaks_per_sweep else 0}, "
                f"max={max(n_peaks_per_sweep) if n_peaks_per_sweep else 0}, "
                f"mean={np.mean(n_peaks_per_sweep):.1f}")
    
    # Better peak tracking: Identify stable peak positions first, then track jitter
    peak_traces = []
    
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
    
    # Estimate FSR from first sweep (peaks are typically evenly spaced)
    if len(all_sweep_peaks[0]) > 1:
        first_sweep_wls = sorted([p['wavelength'] for p in all_sweep_peaks[0]])
        estimated_fsr = np.median(np.diff(first_sweep_wls))
    else:
        # Fallback: use all wavelengths
        all_wavelengths_sorted = sorted(all_wavelengths)
        estimated_fsr = np.median(np.diff(all_wavelengths_sorted)) if len(all_wavelengths_sorted) > 1 else 0.1
    
    # Clustering threshold: peaks within FSR/4 are considered the same peak
    # This allows for jitter but prevents mixing adjacent peaks
    cluster_threshold = estimated_fsr / 4.0
    logger.info(f"Estimated FSR: {estimated_fsr*1000:.1f} pm, cluster threshold: {cluster_threshold*1000:.1f} pm")
    
    # Identify stable peak positions by clustering all wavelengths
    all_wavelengths_sorted = sorted(all_wavelengths)
    peak_clusters = []  # List of (mean_wavelength, [wavelength_values])
    
    current_cluster = [all_wavelengths_sorted[0]]
    for wl in all_wavelengths_sorted[1:]:
        if wl - current_cluster[-1] < cluster_threshold:
            current_cluster.append(wl)
        else:
            # Start new cluster
            peak_clusters.append(np.mean(current_cluster))
            current_cluster = [wl]
    peak_clusters.append(np.mean(current_cluster))  # Add last cluster
    
    logger.info(f"Identified {len(peak_clusters)} stable peak positions")
    
    # Track each stable peak across all sweeps
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
            
            # Find peak nearest to this cluster position
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
    
    logger.info(f"Tracked {len(peak_traces)} benchtop peak traces (min_length={min_trace_length})")
    
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
    
    # Select "best" trace for primary output (most valid points)
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
