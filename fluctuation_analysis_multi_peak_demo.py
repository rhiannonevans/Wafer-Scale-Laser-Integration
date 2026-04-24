"""
Demonstration of multi-peak fluctuation analysis modes.

This script creates synthetic spectrogram data with MULTIPLE PEAKS
and demonstrates all three peak detection modes:
1. "dominant" - tracks the highest peak (may jump between peaks)
2. "nearest" - tracks a specific peak by wavelength
3. "all" - detects and shows all peaks

Run this to see how each mode handles multi-peak scenarios.
"""

import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Create synthetic spectrogram data with TWO PEAKS
np.random.seed(42)
time_points = 50
wavelengths = np.linspace(1330.0, 1331.0, 300)
times = np.linspace(0, 60, time_points)  # 60 minutes

# Create synthetic spectrum with TWO peaks that vary in relative power
spec = np.zeros((time_points, len(wavelengths)))
for i, t in enumerate(times):
    # PEAK 1: centered around 1330.3 nm, power fluctuates
    peak1_wl = 1330.3 + 0.005 * np.sin(2 * np.pi * t / 25)
    peak1_power = 2.0 + 0.5 * np.sin(2 * np.pi * t / 30) + 0.1 * np.random.randn()
    peak1_width = 0.04
    
    # PEAK 2: centered around 1330.7 nm, power varies differently
    # Sometimes stronger, sometimes weaker than peak 1 (mode competition!)
    peak2_wl = 1330.7 + 0.003 * np.cos(2 * np.pi * t / 20)
    peak2_power = 2.2 - 0.6 * np.sin(2 * np.pi * t / 30) + 0.1 * np.random.randn()
    peak2_width = 0.035
    
    # Combine both Gaussian peaks
    spectrum = (peak1_power * np.exp(-((wavelengths - peak1_wl) / peak1_width)**2) +
                peak2_power * np.exp(-((wavelengths - peak2_wl) / peak2_width)**2))
    
    # Add noise
    spectrum += 0.03 * np.random.randn(len(wavelengths))
    spec[i] = np.maximum(spectrum, 0)

# Import the quantify_fluctuations function
sys.path.insert(0, os.path.dirname(__file__))
from plot_spectrograms import quantify_fluctuations

# Create output directory
output_dir = os.path.join(os.path.dirname(__file__), "multi_peak_demo_output")
os.makedirs(output_dir, exist_ok=True)

print("\n" + "="*80)
print("MULTI-PEAK FLUCTUATION ANALYSIS DEMONSTRATION")
print("="*80)
print("\nSynthetic data created with TWO competing peaks:")
print("  - Peak 1 near 1330.3 nm (power varies sinusoidally)")
print("  - Peak 2 near 1330.7 nm (power varies with opposite phase)")
print("  - The peaks alternate being dominant over time")
print("\n" + "="*80)

# MODE 1: Dominant Peak (will jump between the two peaks)
print("\nMODE 1: 'dominant' - Tracking the global maximum")
print("-" * 80)
print("This mode tracks whichever peak is brightest at each moment.")
print("EXPECTED BEHAVIOR: The tracked wavelength will JUMP between ~1330.3 and ~1330.7 nm")
print("as the two peaks compete for dominance.")

stats_dominant = quantify_fluctuations(
    spec, wavelengths, times, output_dir, 
    prefix="mode1_dominant", 
    peak_mode="dominant"
)
print(f"\nRESULTS:")
print(f"  Peak wavelength range: {stats_dominant['peak_wl_range']:.4f} nm")
print(f"  Peak wavelength std:   {stats_dominant['peak_wl_std']:.4f} nm (HIGH due to jumping)")
print(f"  Peak power CV:         {stats_dominant['peak_power_cv']:.2f}%")

# MODE 2: Nearest to Peak 1 (track the ~1330.3 nm peak specifically)
print("\n" + "="*80)
print("\nMODE 2: 'nearest' - Tracking peak near 1330.3 nm")
print("-" * 80)
print("This mode locks onto the peak near 1330.3 nm, ignoring the peak at 1330.7 nm.")
print("EXPECTED BEHAVIOR: Smooth tracking of ONE peak, much lower wavelength std dev.")

stats_nearest = quantify_fluctuations(
    spec, wavelengths, times, output_dir, 
    prefix="mode2_nearest_peak1", 
    peak_mode="nearest",
    target_wavelength=1330.3,
    prominence_threshold=0.05  # 5% of max
)
print(f"\nRESULTS:")
print(f"  Peak wavelength range: {stats_nearest['peak_wl_range']:.4f} nm")
print(f"  Peak wavelength std:   {stats_nearest['peak_wl_std']:.4f} nm (LOWER - one peak)")
print(f"  Peak power CV:         {stats_nearest['peak_power_cv']:.2f}%")

# MODE 3: All peaks (detect and show both)
print("\n" + "="*80)
print("\nMODE 3: 'all' - Detecting all significant peaks")
print("-" * 80)
print("This mode finds ALL peaks with sufficient prominence.")
print("EXPECTED BEHAVIOR: Detects both peaks, shows them as gray X markers in plots,")
print("tracks the most prominent one for statistics.")

stats_all = quantify_fluctuations(
    spec, wavelengths, times, output_dir, 
    prefix="mode3_all_peaks", 
    peak_mode="all",
    prominence_threshold=0.1  # 10% of max
)
print(f"\nRESULTS:")
print(f"  Average # of peaks:    {stats_all.get('num_peaks_mean', 'N/A'):.1f}")
print(f"  Peak wavelength range: {stats_all['peak_wl_range']:.4f} nm")
print(f"  Peak wavelength std:   {stats_all['peak_wl_std']:.4f} nm")
print(f"  Peak power CV:         {stats_all['peak_power_cv']:.2f}%")

# Create a reference spectrogram
print("\n" + "="*80)
print("\nCreating reference spectrogram...")
fig, ax = plt.subplots(figsize=(12, 6))
extent = [times.min(), times.max(), wavelengths.min(), wavelengths.max()]
im = ax.imshow(spec.T, aspect="auto", origin="lower", cmap="inferno", extent=extent)
ax.set_xlabel("Time (min)", fontsize=12)
ax.set_ylabel("Wavelength (nm)", fontsize=12)
ax.set_title("Reference Spectrogram: Two Competing Peaks", fontsize=14, fontweight='bold')

# Add annotations showing where the peaks are
ax.axhline(1330.3, color='cyan', linestyle='--', linewidth=1, alpha=0.5, label='Peak 1 region')
ax.axhline(1330.7, color='lime', linestyle='--', linewidth=1, alpha=0.5, label='Peak 2 region')
ax.legend(fontsize=10)

cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Power (mW)", fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(output_dir, "reference_spectrogram_two_peaks.png"), dpi=300)
plt.close(fig)

print(f"\nAll outputs saved to: {output_dir}")
print("\nCOMPARE THE THREE MODES:")
print("  1. mode1_dominant_fluctuation_analysis.png")
print("     - Will show large wavelength jumps between the two peaks")
print("  2. mode2_nearest_peak1_fluctuation_analysis.png")
print("     - Will show smooth tracking of just the 1330.3 nm peak")
print("  3. mode3_all_peaks_fluctuation_analysis.png")
print("     - Will show BOTH peaks as gray X markers in the plots")
print("\n" + "="*80)
print("\nRECOMMENDATION:")
print("  - Use 'dominant' for single-peak data or when you don't care which peak")
print("  - Use 'nearest' to track a SPECIFIC resonance in multi-peak data")
print("  - Use 'all' to get a complete picture of mode competition")
print("="*80 + "\n")
