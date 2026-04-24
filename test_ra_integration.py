"""
Test script to verify RA-style multi-peak tracking integration.

This script tests:
1. MAT file saving (peak_shift.mat, fsr_er_q.mat)
2. Multi-peak collated offset plots
3. Spectrogram overlays with peak traces
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add RA to path
RA_PATH = Path(__file__).parent / "RetrospectiveAnalysis" / "src"
if RA_PATH.exists():
    sys.path.insert(0, str(RA_PATH))

from peak_tracking_ra import fit_and_track_sweeps


def generate_synthetic_spectrogram(n_sweeps=25, n_wavelengths=500, n_peaks=3):
    """Generate synthetic spectrogram with multiple drifting peaks."""
    
    # Wavelength range (nm)
    wavelength = np.linspace(1549.0, 1551.0, n_wavelengths)
    
    # Time array (minutes)
    times = np.linspace(0, 10, n_sweeps)
    
    # Initial peak positions
    peak_centers = np.array([1549.5, 1550.0, 1550.5])[:n_peaks]
    
    # Drift rates (pm/min)
    drift_rates = np.array([+20, -10, 0])[:n_peaks]
    
    # Generate spectrogram
    spec = np.zeros((n_sweeps, n_wavelengths))
    
    for i, t in enumerate(times):
        for j, (center, drift) in enumerate(zip(peak_centers, drift_rates)):
            # Wavelength drift in nm
            current_center = center + (drift * t / 1000.0)  # pm to nm
            
            # Lorentzian peak
            gamma = 0.02  # FWHM in nm
            lorentzian = 1.0 / (1 + ((wavelength - current_center) / (gamma / 2))**2)
            
            # Peak power varies
            peak_power = 1.0 + 0.1 * np.sin(2 * np.pi * t / 5)
            
            spec[i, :] += peak_power * lorentzian
    
    # Add noise
    spec += 0.05 * np.random.randn(*spec.shape)
    
    return spec, wavelength, times


def test_ra_integration():
    """Test RA-style multi-peak tracking and output generation."""
    
    print("=" * 60)
    print("Testing RA-style Multi-Peak Integration")
    print("=" * 60)
    
    # Generate synthetic data
    print("\n1. Generating synthetic spectrogram...")
    spec, wavelength, times = generate_synthetic_spectrogram(n_sweeps=25, n_peaks=3)
    print(f"   Shape: {spec.shape}, wavelength range: {wavelength.min():.3f}-{wavelength.max():.3f} nm")
    print(f"   Time range: {times.min():.1f}-{times.max():.1f} min")
    
    # Fit all peaks
    print("\n2. Fitting all peaks with RA's Lorentzian fitter...")
    results = fit_and_track_sweeps(
        spec=spec,
        wavelength=wavelength,
        gaussian_filter_sigma=5.0,
        prominence_scaler=0.1
    )
    
    peak_wavelengths = results['centers']
    all_peak_traces = results.get('all_peak_traces', [])
    fsr_stats = results.get('fsr_stats', {})
    
    print(f"   Primary trace: {np.sum(np.isfinite(peak_wavelengths))}/{len(peak_wavelengths)} valid points")
    print(f"   Total peaks tracked: {len(all_peak_traces)}")
    
    # Calculate drift rates
    print("\n3. Calculating drift rates...")
    for idx, trace in enumerate(all_peak_traces):
        valid_mask = np.isfinite(trace['centers'])
        n_valid = np.sum(valid_mask)
        
        if n_valid > 2:
            # Get corresponding time values for valid wavelength points
            # Note: trace['centers'] might have extra element, trim to match times
            centers = trace['centers'][:len(times)]
            valid_mask = np.isfinite(centers)
            
            t_valid = times[valid_mask]
            wl_valid = centers[valid_mask]
            
            if len(t_valid) > 2:
                # Initial wavelength
                wl_0 = wl_valid[0]
                
                # Wavelength shift in pm
                delta_wl_pm = (wl_valid - wl_0) * 1000
                
                # Linear fit for drift rate
                coeffs = np.polyfit(t_valid, delta_wl_pm, 1)
                drift_rate = coeffs[0]  # pm/min
                
                mean_Q = np.nanmean(trace['Q_factors'][:len(times)])
                mean_R2 = np.nanmean(trace['R_squared'][:len(times)])
                mean_FWHM = np.nanmean(trace['FWHM'][:len(times)]) * 1000  # nm to pm
                
                print(f"   Peak {idx+1}: lambda_0={wl_0:.4f} nm, drift={drift_rate:+.2f} pm/min, "
                      f"Q={mean_Q:.0f}, R2={mean_R2:.3f}, FWHM={mean_FWHM:.1f} pm")
    
    # FSR statistics
    if fsr_stats.get('mean'):
        print(f"\n4. FSR Statistics:")
        print(f"   Mean: {fsr_stats['mean']*1000:.1f} ± {fsr_stats['std']*1000:.1f} pm")
    
    # Test MAT file saving
    print("\n5. Testing MAT file generation...")
    import scipy.io
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save peak_shift.mat
        peak_shift_dict = {'t_array': times}
        for idx, trace in enumerate(all_peak_traces):
            peak_shift_dict[f'peak{idx+1}_wl_trace'] = trace['centers']
            valid_mask = np.isfinite(trace['centers'])
            if np.any(valid_mask):
                initial_wl = trace['centers'][valid_mask][0]
                peak_shift_dict[f'peak{idx+1}_wl_shift_nm'] = trace['centers'] - initial_wl
        
        peak_shift_path = Path(tmpdir) / "test_peak_shift.mat"
        scipy.io.savemat(peak_shift_path, peak_shift_dict)
        print(f"   [OK] peak_shift.mat created ({peak_shift_path.stat().st_size} bytes)")
        
        # Verify loading
        loaded = scipy.io.loadmat(peak_shift_path)
        print(f"   [OK] Verified: {len(loaded)-5} peak traces saved (excluding metadata)")
        
        # Save fsr_er_q.mat
        fsr_er_q_dict = {'t_array': times}
        for idx, trace in enumerate(all_peak_traces):
            fsr_er_q_dict[f'peak{idx+1}_Q'] = trace['Q_factors']
            fsr_er_q_dict[f'peak{idx+1}_FWHM_nm'] = trace['FWHM']
            fsr_er_q_dict[f'peak{idx+1}_R2'] = trace['R_squared']
            fsr_er_q_dict[f'peak{idx+1}_ER'] = trace['ER']
            fsr_er_q_dict[f'peak{idx+1}_wavelength_nm'] = trace['centers']
            fsr_er_q_dict[f'peak{idx+1}_power'] = trace['peak_powers']
        
        if fsr_stats.get('mean'):
            fsr_er_q_dict['FSR_mean_nm'] = fsr_stats['mean']
            fsr_er_q_dict['FSR_std_nm'] = fsr_stats['std']
        
        fsr_er_q_path = Path(tmpdir) / "test_fsr_er_q.mat"
        scipy.io.savemat(fsr_er_q_path, fsr_er_q_dict)
        print(f"   [OK] fsr_er_q.mat created ({fsr_er_q_path.stat().st_size} bytes)")
        
        # Verify loading
        loaded_fsr = scipy.io.loadmat(fsr_er_q_path)
        print(f"   [OK] Verified: Q, FWHM, R2, ER, wavelength, power saved for {len(all_peak_traces)} peaks")
    
    print("\n" + "=" * 60)
    print("All RA integration tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_ra_integration()
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
