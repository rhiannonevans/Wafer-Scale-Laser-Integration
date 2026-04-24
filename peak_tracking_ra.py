"""
Peak tracking using RetrospectiveAnalysis (RA) Dijkstra algorithm.

This module uses RA's peaks_to_traces() with Dijkstra shortest-path algorithm
for robust multi-peak tracking with FSR-based constraints.

Key Features:
- Uses RA's graph-based Dijkstra algorithm (not greedy matching)
- FSR-aware constraints (0.3×FSR tolerance by default)
- Minimum trace length filtering (removes transient peaks)
- Global path optimization (not just nearest neighbor)
- Auto-flip detection for inverted traces (eval system power4 channel)
"""

import sys
import os
import numpy as np
from typing import Dict, List, Optional

# Add RetrospectiveAnalysis/src to path
_RA_AVAILABLE = False
try:
    ra_src_path = os.path.join(os.path.dirname(__file__), 'RetrospectiveAnalysis', 'src')
    if os.path.exists(ra_src_path) and ra_src_path not in sys.path:
        sys.path.insert(0, ra_src_path)
    
    from core.lib import SweepFitResult, LorentzianPeakFitResult, peaks_to_traces  # type: ignore[reportMissingImports]
    _RA_AVAILABLE = True
except ImportError as e:
    _RA_IMPORT_ERROR = str(e)


def normalize_upward_peaks(y, label=''):
    """
    Ensure peaks point upward and normalize to [0,1].
    Auto-detects inverted traces and flips if needed.
    
    Args:
        y: 1D array of power values
        label: Optional label for logging
    
    Returns:
        (normalized_y, was_flipped)
    """
    from scipy.signal import find_peaks
    
    # Check both orientations
    peaks_up, props_up = find_peaks(y, prominence=0.1 * (y.max() - y.min()))
    peaks_down, props_down = find_peaks(-y, prominence=0.1 * (y.max() - y.min()))
    
    # Decide which orientation has stronger peaks
    prom_up = np.sum(props_up.get('prominences', [0]))
    prom_down = np.sum(props_down.get('prominences', [0]))
    
    if prom_down > prom_up and len(peaks_down) > len(peaks_up):
        # Inverted - flip it
        y_corrected = -y
        was_flipped = True
    else:
        y_corrected = y
        was_flipped = False
    
    # Normalize to [0,1]
    y_norm = (y_corrected - y_corrected.min()) / (y_corrected.max() - y_corrected.min() + 1e-10)
    
    return y_norm, was_flipped


def fit_all_peaks_multi_sweep(spec, wavelength, gaussian_filter_sigma=8.0, 
                              prominence_scaler=0.1, auto_flip=False,
                              r2_threshold=0.3, fsr_shift_tolerance=0.3,
                              min_trace_length=10, data_type='dbm'):
    """
    Fit ALL peaks across multiple sweeps using RA's Dijkstra-based tracking.
    
    This uses the actual peaks_to_traces() function from RA for robust tracking
    with FSR-based constraints and global path optimization.
    
    Args:
        spec: 2D array (time x wavelength)
        wavelength: 1D array of wavelength values [nm]
        gaussian_filter_sigma: Smoothing parameter for peak detection
        prominence_scaler: Peak prominence threshold (0-1 scale)
        auto_flip: Auto-detect and flip inverted traces
        r2_threshold: Minimum R² to accept a fit (default 0.3)
        fsr_shift_tolerance: Max wavelength shift as fraction of FSR (default 0.3)
        min_trace_length: Minimum valid points to keep a trace (default 10)
        data_type: 'dbm' for OSA data, 'linear' for benchtop mW data
    
    Returns:
        dict with 'peak_traces', 'fsr_stats', 'n_peaks_per_sweep'
    """
    if not _RA_AVAILABLE:
        raise ImportError(f"RetrospectiveAnalysis not available: {_RA_IMPORT_ERROR}")
    
    n_sweeps = spec.shape[0]
    
    # Warn if using RA's SweepFitResult with linear benchtop data
    if data_type == 'linear':
        print(f"WARNING: Benchtop linear data detected.")
        print(f"         RA's SweepFitResult expects dBm data and may produce poor fits.")
        print(f"         Falling back to dominant mode is recommended for benchtop data.")
    
    # Step 1: Fit all peaks for each sweep, collect peak parameters
    all_sweep_results = []
    n_peaks_per_sweep = []
    n_flipped = 0
    
    for sweep_idx in range(n_sweeps):
        power = spec[sweep_idx, :]
        
        # Auto-flip if requested
        if auto_flip:
            power, was_flipped = normalize_upward_peaks(power, f'sweep {sweep_idx}')
            if was_flipped:
                n_flipped += 1
        else:
            # Just normalize to [0,1]
            power = (power - power.min()) / (power.max() - power.min() + 1e-10)
        
        # Use RA's SweepFitResult to fit all peaks
        try:
            fit_result = SweepFitResult.from_data(
                powers=power,
                wavelengths=wavelength,
                gaussian_filter_sigma=gaussian_filter_sigma,
                prominence_scaler=prominence_scaler
            )
            
            # Filter by R² threshold
            valid_peaks = [p for p in fit_result.peaks if p.r2 >= r2_threshold]
            all_sweep_results.append(valid_peaks)
            n_peaks_per_sweep.append(len(valid_peaks))
            
        except Exception as e:
            # No peaks or fit failed
            all_sweep_results.append([])
            n_peaks_per_sweep.append(0)
    
    if auto_flip and n_flipped > 0:
        print(f"Auto-flip applied to {n_flipped}/{n_sweeps} sweeps")
    
    print(f"Peak counts per sweep: min={min(n_peaks_per_sweep)}, max={max(n_peaks_per_sweep)}, mean={np.mean(n_peaks_per_sweep):.1f}")
    
    # Step 2: Use RA's peaks_to_traces with Dijkstra algorithm
    # RA's get_peaks() returns peak_params arrays (5 elements: [x0, y0, _i, gamma, a])
    # peaks_to_traces expects list of 2D arrays where each row is peak_params
    peaks_per_sweep = []
    for sweep_peaks in all_sweep_results:
        if len(sweep_peaks) == 0:
            # Empty sweep - add empty array with shape (0, 5) for consistency
            peaks_per_sweep.append(np.array([]).reshape(0, 5).astype(np.float64))
        else:
            # Extract peak_params (5-element Lorentzian fit parameters)
            sweep_array = np.array([p.peak_params for p in sweep_peaks], dtype=np.float64)
            peaks_per_sweep.append(sweep_array)
    
    # Define distance function for RA (Euclidean distance in wavelength space)
    def euclidean_distance(p1, p2):
        """Distance between two peaks based on wavelength."""
        return abs(p1[0] - p2[0])
    
    # Call RA's peaks_to_traces with Dijkstra algorithm
    try:
        trace_groups, fsr_nm = peaks_to_traces(
            peaks=peaks_per_sweep,
            distance_func=euclidean_distance,
            shift_betweep_sweeps=fsr_shift_tolerance,
            traces_threshold=min_trace_length
        )
        
        # Count valid traces (non-NaN groups)
        valid_traces = [g for g in trace_groups if len(g) > 0 and not np.isnan(g[0])]
        print(f"Tracked {len(valid_traces)} peak traces")
        print(f"FSR: {fsr_nm*1000:.2f} pm")
        
    except Exception as e:
        print(f"peaks_to_traces failed: {e}")
        trace_groups = []
        fsr_nm = np.nan
    
    # Step 3: Convert RA trace format to our peak_traces format
    peak_traces = []
    
    # trace_groups is alternating [valid_trace, nan_list, valid_trace, nan_list, ...]
    # We only want the valid traces (non-NaN groups)
    for group in trace_groups:
        if len(group) == 0 or np.isnan(group[0]):
            continue  # Skip NaN separators
        
        # group is a list of wavelengths for one trace
        # Need to map back to full peak parameters
        trace_wavelengths = np.array(group)
        
        # Initialize arrays for this trace (fill with NaN for full time range)
        centers = np.full(n_sweeps, np.nan)
        Q_factors = np.full(n_sweeps, np.nan)
        FWHM = np.full(n_sweeps, np.nan)
        R_squared = np.full(n_sweeps, np.nan)
        ER = np.full(n_sweeps, np.nan)
        peak_powers = np.full(n_sweeps, np.nan)
        
        # Find which sweep each trace point came from and fill in parameters
        trace_idx = 0
        for sweep_idx in range(n_sweeps):
            if trace_idx >= len(trace_wavelengths):
                break
            
            target_wl = trace_wavelengths[trace_idx]
            
            # Find matching peak in this sweep
            for peak in all_sweep_results[sweep_idx]:
                if abs(peak.lambda0 - target_wl) < 1e-6:  # Match found
                    centers[sweep_idx] = peak.lambda0
                    Q_factors[sweep_idx] = peak.q
                    FWHM[sweep_idx] = peak.fwhm
                    R_squared[sweep_idx] = peak.r2
                    ER[sweep_idx] = peak.er
                    peak_powers[sweep_idx] = peak.peak_params[2]
                    trace_idx += 1
                    break
        
        # Calculate mean wavelength from valid points
        valid_centers = centers[np.isfinite(centers)]
        mean_wl = np.mean(valid_centers) if len(valid_centers) > 0 else np.nan
        
        peak_traces.append({
            'centers': centers,
            'Q_factors': Q_factors,
            'FWHM': FWHM,
            'R_squared': R_squared,
            'ER': ER,
            'peak_powers': peak_powers,
            'mean_wavelength': mean_wl
        })
    
    # Step 4: Calculate FSR statistics
    fsr_values = []
    for sweep_peaks in all_sweep_results:
        if len(sweep_peaks) >= 2:
            wavelengths = sorted([p.lambda0 for p in sweep_peaks])
            spacings = np.diff(wavelengths)
            fsr_values.extend(spacings)
    
    if fsr_values:
        fsr_stats = {
            'mean': np.mean(fsr_values),
            'std': np.std(fsr_values)
        }
    else:
        fsr_stats = {'mean': None, 'std': None}
    
    return {
        'peak_traces': peak_traces,
        'fsr_stats': fsr_stats,
        'n_peaks_per_sweep': n_peaks_per_sweep
    }


def fit_and_track_sweeps(spec, wavelength, gaussian_filter_sigma=8.0,
                        prominence_scaler=0.1, peak_mode='lorentz',
                        auto_flip=False, r2_threshold=0.3,
                        fsr_shift_tolerance=0.3, min_trace_length=10,
                        data_type='dbm'):
    """
    Backward-compatible wrapper for fit_all_peaks_multi_sweep.
    
    Args:
        data_type: 'dbm' for OSA data (default), 'linear' for benchtop mW data
    
    Returns both single "best" trace and all traces for compatibility.
    """
    result = fit_all_peaks_multi_sweep(
        spec=spec,
        wavelength=wavelength,
        gaussian_filter_sigma=gaussian_filter_sigma,
        prominence_scaler=prominence_scaler,
        auto_flip=auto_flip,
        r2_threshold=r2_threshold,
        fsr_shift_tolerance=fsr_shift_tolerance,
        min_trace_length=min_trace_length,
        data_type=data_type
    )
    
    peak_traces = result['peak_traces']
    
    # Select "best" trace (most valid points) for backward compatibility
    if len(peak_traces) > 0:
        best_trace = max(peak_traces, key=lambda t: np.sum(np.isfinite(t['centers'])))
        centers = best_trace['centers']
    else:
        # No peaks tracked
        centers = np.full(spec.shape[0], np.nan)
    
    return {
        'centers': centers,
        'all_peak_traces': peak_traces,
        'fsr_stats': result['fsr_stats']
    }
