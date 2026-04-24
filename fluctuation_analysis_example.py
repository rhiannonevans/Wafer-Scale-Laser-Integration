"""
Example demonstrating the new fluctuation analysis feature.

This script creates synthetic spectrogram data and runs the fluctuation
analysis to show what the output looks like.
"""

import numpy as np
import matplotlib.pyplot as plt
import os

# Create synthetic spectrogram data
np.random.seed(42)
time_points = 50
wavelengths = np.linspace(1330.0, 1331.0, 200)
times = np.linspace(0, 60, time_points)  # 60 minutes

# Create synthetic spectrum with drift and fluctuations
spec = np.zeros((time_points, len(wavelengths)))
for i, t in enumerate(times):
    # Peak wavelength drifts slightly over time
    peak_wl = 1330.5 + 0.01 * np.sin(2 * np.pi * t / 30) + 0.002 * t / 60
    # Peak power fluctuates around 2.5 mW
    peak_power = 2.5 + 0.15 * np.sin(2 * np.pi * t / 20) + 0.1 * np.random.randn()
    # Width varies slightly
    width = 0.05 + 0.01 * np.random.randn()
    
    # Create Gaussian peak
    spec[i] = peak_power * np.exp(-((wavelengths - peak_wl) / width)**2)
    # Add noise
    spec[i] += 0.02 * np.random.randn(len(wavelengths))
    # Ensure non-negative
    spec[i] = np.maximum(spec[i], 0)

# Import the quantify_fluctuations function
import sys
sys.path.insert(0, os.path.dirname(__file__))
from plot_spectrograms import quantify_fluctuations

# Run fluctuation analysis
output_dir = os.path.join(os.path.dirname(__file__), "fluctuation_example_output")
os.makedirs(output_dir, exist_ok=True)

stats = quantify_fluctuations(spec, wavelengths, times, output_dir, 
                              prefix="example_spectrogram", wl_roi=None)

print("\n" + "="*60)
print("EXAMPLE FLUCTUATION ANALYSIS COMPLETE")
print("="*60)
print(f"\nOutput files created in: {output_dir}")
print("\nKey Statistics:")
print(f"  Peak Wavelength Drift:    {stats['peak_wl_drift']:.6f} nm")
print(f"  Peak Wavelength Range:    {stats['peak_wl_range']:.6f} nm")
print(f"  Peak Wavelength Std Dev:  {stats['peak_wl_std']:.6f} nm")
print(f"  Peak Power CV:            {stats['peak_power_cv']:.3f} %")
print(f"  Average Power CV:         {stats['avg_power_cv']:.3f} %")
print("\nCheck the output directory for:")
print("  - example_spectrogram_fluctuation_statistics.txt")
print("  - example_spectrogram_fluctuation_analysis.png")
print("="*60 + "\n")

# Also create a simple spectrogram plot for reference
fig, ax = plt.subplots(figsize=(10, 6))
extent = [times.min(), times.max(), wavelengths.min(), wavelengths.max()]
im = ax.imshow(spec.T, aspect="auto", origin="lower", cmap="inferno", extent=extent)
ax.set_xlabel("Time (min)", fontsize=12)
ax.set_ylabel("Wavelength (nm)", fontsize=12)
ax.set_title("Example Spectrogram", fontsize=14)
cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Power (mW)", fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(output_dir, "example_spectrogram.png"), dpi=200)
plt.close(fig)
print("Also created: example_spectrogram.png")
