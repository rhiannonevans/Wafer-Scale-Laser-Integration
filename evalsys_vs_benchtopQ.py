#!/usr/bin/env python3
"""
================================================================================
Script: Benchtop_vs_EvalSystem_Resonance_Analysis.py
Author: sheri and co-pilot
Date: 2025-10-28

PURPOSE:
--------
Compare benchtop laser spectra with eval system data that may have inverted peaks.
Automatically detects and corrects inverted peaks before performing Q-factor and FSR analysis.

FEATURES:
---------
- Automatic peak inversion detection and correction
- Interactive Q-factor analysis with adjustable baseline
- FSR calculation and comparison
- Zoomed overlay plot of analyzed peaks
- Comprehensive data saving in .mat format
================================================================================
"""

import os
from datetime import datetime
from tkinter import Tk, filedialog, messagebox
import scipy.io
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import lorentzfit
from lorentzfit import lorentzfit
from matplotlib.widgets import Slider, Button
from matplotlib.backend_bases import MouseButton

# Plot font constants
PLOT_FONT_AXIS_LABEL = 18
PLOT_FONT_AXIS_TICKS = 18
PLOT_FONT_TITLE = 14
PLOT_FONT_LEGEND = 16
PLOT_FONT_TEXT = 9

def normalize_upward_peaks(y, label=''):
    """
    Ensure peaks point upward and normalize to [0,1].
    Auto-detects inverted traces and flips if needed.
    """
    y = np.asarray(y, dtype=float)
    if not np.isfinite(y).any():
        return y, False

    def _norm(v):
        v = v - np.nanmin(v)
        r = np.nanmax(v) - np.nanmin(v)
        return v / r if r > 0 else v

    y_pos = _norm(y)
    y_neg = _norm(-y)

    p_pos, prop_pos = find_peaks(y_pos, prominence=0.03)
    p_neg, prop_neg = find_peaks(y_neg, prominence=0.03)

    flip = False
    if len(p_neg) > len(p_pos):
        flip = True
    elif len(p_neg) == len(p_pos):
        prom_pos = prop_pos.get('prominences', np.array([])).sum() if prop_pos else 0.0
        prom_neg = prop_neg.get('prominences', np.array([])).sum() if prop_neg else 0.0
        flip = prom_neg > prom_pos

    y_up = -y if flip else y
    # Normalize to [0,1] for plotting/analysis
    y_up = y_up - np.nanmin(y_up)
    rng = np.nanmax(y_up) - np.nanmin(y_up)
    y_up = y_up / rng if rng > 0 else y_up

    if flip:
        print(f"  ✓ Auto-flip applied ({label}): inverted peaks detected")
    else:
        print(f"  ○ No flip needed ({label})")
    return y_up, flip

def interactive_peak_selection(x, y, title='Select peaks to analyze'):
    """
    Interactive plot for selecting peaks to analyze.
    Left-click to select peaks, right-click to remove, close when done.
    Returns indices of selected peaks.
    """
    selected_peaks = []
    
    fig, ax = plt.subplots(figsize=(14, 6))
    plt.subplots_adjust(bottom=0.2)
    
    ax.plot(x, y, '.k', markersize=3, label='Data')
    ax.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_title(f'{title}\nLeft-click: Add peak | Right-click: Remove nearest | Close window when done', 
                 fontsize=PLOT_FONT_TITLE)
    ax.grid(True)
    ax.legend(fontsize=PLOT_FONT_LEGEND)
    
    scatter = ax.scatter([], [], c='black', s=100, marker='^', 
                        label='Selected peaks', zorder=5)
    
    def onclick(event):
        if event.inaxes != ax:
            return
        
        if event.button == MouseButton.LEFT:
            # Find nearest data point
            distances = np.abs(x - event.xdata)
            idx = np.argmin(distances)
            
            if idx not in selected_peaks:
                selected_peaks.append(idx)
                print(f"Added peak at λ={x[idx]:.4f} nm (index {idx})")
                update_plot()
        
        elif event.button == MouseButton.RIGHT:
            # Remove nearest selected peak
            if selected_peaks:
                peak_wavelengths = x[selected_peaks]
                distances = np.abs(peak_wavelengths - event.xdata)
                nearest_idx = np.argmin(distances)
                removed_idx = selected_peaks.pop(nearest_idx)
                print(f"Removed peak at λ={x[removed_idx]:.4f} nm")
                update_plot()
    
    def update_plot():
        if selected_peaks:
            scatter.set_offsets(np.c_[x[selected_peaks], y[selected_peaks]])
        else:
            scatter.set_offsets(np.empty((0, 2)))
        fig.canvas.draw()
    
    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()
    
    return sorted(selected_peaks)

def analyze_peak_with_adjustable_baseline(x, y, peak_idx, initial_window=15, save_path=None):
    """
    Interactive baseline adjustment for a single peak.
    Use sliders to adjust baseline window and polynomial order.
    """
    # Store original indices
    left_idx = max(0, peak_idx - initial_window)
    right_idx = min(len(x), peak_idx + initial_window + 1)
    peak_x = x[left_idx:right_idx]
    peak_y = y[left_idx:right_idx]
    
    # Local peak index within the window
    local_peak_idx = peak_idx - left_idx
    
    fig, ((ax_main, ax_baseline), (ax_fit, ax_residual)) = plt.subplots(
        2, 2, figsize=(14, 10), 
        gridspec_kw={'height_ratios': [2, 1], 'width_ratios': [1, 1]}
    )
    plt.subplots_adjust(bottom=0.25, hspace=0.3)
    
    def calculate_baseline(left_win, right_win, order):
        # Calculate baseline using points OUTSIDE the peak window
        baseline_left_start = max(0, left_idx - left_win)
        baseline_left_end = left_idx
        baseline_right_start = right_idx
        baseline_right_end = min(len(x), right_idx + right_win)
        
        # Get baseline points from OUTSIDE the peak region
        if baseline_left_end > baseline_left_start:
            baseline_x_left = x[baseline_left_start:baseline_left_end]
            baseline_y_left = y[baseline_left_start:baseline_left_end]
        else:
            baseline_x_left = np.array([])
            baseline_y_left = np.array([])
        
        if baseline_right_end > baseline_right_start:
            baseline_x_right = x[baseline_right_start:baseline_right_end]
            baseline_y_right = y[baseline_right_start:baseline_right_end]
        else:
            baseline_x_right = np.array([])
            baseline_y_right = np.array([])
        
        # Combine left and right baseline points
        baseline_x = np.concatenate([baseline_x_left, baseline_x_right])
        baseline_y = np.concatenate([baseline_y_left, baseline_y_right])
        
        # Fit baseline
        if len(baseline_x) >= order + 1:
            p = np.polyfit(baseline_x, baseline_y, order)
            baseline_peak = np.polyval(p, peak_x)
            baseline_full = np.polyval(p, x)
        else:
            print(f"Warning: Not enough baseline points ({len(baseline_x)}), using linear fallback")
            slope = (peak_y[-1] - peak_y[0]) / (peak_x[-1] - peak_x[0])
            baseline_peak = slope * (peak_x - peak_x[0]) + peak_y[0]
            baseline_full = slope * (x - peak_x[0]) + peak_y[0]
            baseline_x = peak_x[[0, -1]]
            baseline_y = peak_y[[0, -1]]
        
        return baseline_peak, baseline_full, baseline_x, baseline_y
    
    def update(val=None):
        left_win = int(slider_left.val)
        right_win = int(slider_right.val)
        order = int(slider_order.val)
        
        baseline_peak, baseline_full, baseline_x_pts, baseline_y_pts = calculate_baseline(
            left_win, right_win, order
        )
        
        # Baseline-corrected data
        normalized_curve = peak_y - baseline_peak
        
        # Normalize to [0,1] range keeping peaks pointing UP
        ymin = np.min(normalized_curve)
        ymax = np.max(normalized_curve)
        if (ymax - ymin) > 0:
            normalized_curve_lin = (normalized_curve - ymin) / (ymax - ymin)
        else:
            normalized_curve_lin = normalized_curve
        
        # Perform Lorentzian fit
        try:
            peak_height = np.max(normalized_curve_lin) - np.min(normalized_curve_lin)
            peak_center = peak_x[np.argmax(normalized_curve_lin)]
            peak_width = (peak_x[-1] - peak_x[0]) / 10
            baseline_level = np.min(normalized_curve_lin)
            
            p0_guess = [peak_height, peak_center, peak_width**2, baseline_level]
            
            yfit, params, resnorm, residual = lorentzfit(
                peak_x, normalized_curve_lin, p0=p0_guess, nparams='3c'
            )
            
            x0 = params[1]
            gamma = np.sqrt(abs(params[2])) * 2  # FWHM
            Q_factor = x0 / gamma if gamma != 0 else np.nan
            R_sq = 1 - np.var(normalized_curve_lin - yfit) / np.var(normalized_curve_lin)
            
            fit_success = True
        except Exception as e:
            print(f"Fit failed: {e}")
            fit_success = False
            Q_factor = np.nan
            R_sq = np.nan
            params = None
        
        # Clear and replot
        ax_main.clear()
        ax_baseline.clear()
        ax_fit.clear()
        ax_residual.clear()
        
        # Plot 1: Original data with baseline
        ax_main.plot(x, y, '.k', markersize=3, alpha=0.3, label='All data')
        ax_main.plot(peak_x, peak_y, '.b', markersize=5, label='Peak region')
        ax_main.plot(x, baseline_full, 'r-', linewidth=2, label='Baseline')
        if len(baseline_x_pts) > 0:
            ax_main.plot(baseline_x_pts, baseline_y_pts, 'ro', markersize=6, 
                        label=f'Baseline points ({len(baseline_x_pts)})')
        ax_main.axvline(peak_x[0], color='gray', linestyle='--', alpha=0.5)
        ax_main.axvline(peak_x[-1], color='gray', linestyle='--', alpha=0.5)
        ax_main.set_xlabel('Wavelength (nm)')
        ax_main.set_ylabel('Normalized Power')
        ax_main.set_title('Original Data with Baseline')
        ax_main.legend(fontsize=PLOT_FONT_LEGEND)
        ax_main.grid(True)
        
        # Plot 2: Baseline detail
        ax_baseline.plot(peak_x, peak_y, '.b', markersize=5, label='Peak data')
        ax_baseline.plot(peak_x, baseline_peak, 'r-', linewidth=2, label='Baseline')
        ax_baseline.set_xlabel('Wavelength (nm)')
        ax_baseline.set_ylabel('Power')
        ax_baseline.set_title('Baseline Detail (Peak Region)')
        ax_baseline.legend()
        ax_baseline.grid(True)
        
        # Plot 3: Normalized and fitted
        if fit_success:
            ax_fit.plot(peak_x, normalized_curve_lin, '.b', markersize=5, label='Normalized data')
            ax_fit.plot(peak_x, yfit, 'r-', linewidth=2, label='Lorentz fit')
            
            half_max = (np.max(yfit) + np.min(yfit)) / 2
            ax_fit.axhline(half_max, color='gray', linestyle='--', linewidth=1, 
                          label=f'Half-max ({half_max:.2f})')
            
            ax_fit.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
            ax_fit.set_ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
            ax_fit.set_title(f'Lorentzian Fit: y = A/((x-x₀)²+γ) + C', fontsize=PLOT_FONT_TITLE)

            textstr = f'Q={Q_factor:.0f}, R²={R_sq:.3f}\nA={params[0]:.2e}, x₀={params[1]:.4f}\nγ={params[2]:.2e}, C={params[3]:.2e}'
            ax_fit.text(0.02, 0.98, textstr, transform=ax_fit.transAxes, 
                       fontsize=PLOT_FONT_TEXT, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            ax_fit.legend(fontsize=PLOT_FONT_LEGEND, loc='upper right')
            ax_fit.grid(True, alpha=0.3)
            
            # Plot 4: Residuals
            ax_residual.plot(peak_x, residual, '.k', markersize=4)
            ax_residual.axhline(0, color='r', linewidth=1)
            ax_residual.set_xlabel('Wavelength (nm)')
            ax_residual.set_ylabel('Residuals')
            ax_residual.set_title('Fit Residuals')
            ax_residual.grid(True)
        else:
            ax_fit.text(0.5, 0.5, 'Fit Failed', ha='center', va='center',
                       transform=ax_fit.transAxes, fontsize=PLOT_FONT_TITLE, color='red')
            ax_residual.text(0.5, 0.5, 'No Residuals', ha='center', va='center',
                           transform=ax_residual.transAxes, fontsize=PLOT_FONT_TITLE)
        
        fig.canvas.draw_idle()
        return Q_factor, R_sq, params
    
    # Create sliders
    ax_slider_left = plt.axes([0.15, 0.12, 0.3, 0.03])
    ax_slider_right = plt.axes([0.15, 0.08, 0.3, 0.03])
    ax_slider_order = plt.axes([0.15, 0.04, 0.3, 0.03])
    
    slider_left = Slider(ax_slider_left, 'Left Window', 0, 50, valinit=10, valstep=1)
    slider_right = Slider(ax_slider_right, 'Right Window', 0, 50, valinit=10, valstep=1)
    slider_order = Slider(ax_slider_order, 'Poly Order', 0, 3, valinit=1, valstep=1)
    
    slider_left.on_changed(update)
    slider_right.on_changed(update)
    slider_order.on_changed(update)
    
    # Add Accept/Skip buttons
    result = {'accept': False, 'Q': np.nan, 'R2': np.nan, 'params': None}
    
    def accept(event):
        Q, R2, params = update()
        result['accept'] = True
        result['Q'] = Q
        result['R2'] = R2
        result['params'] = params
        
        if save_path is not None:
            try:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"  Figure saved to: {save_path}")
            except Exception as e:
                print(f"  Warning: Could not save figure: {e}")
        
        plt.close(fig)
    
    def skip(event):
        result['accept'] = False
        plt.close(fig)
    
    ax_button_accept = plt.axes([0.6, 0.08, 0.1, 0.05])
    ax_button_skip = plt.axes([0.75, 0.08, 0.1, 0.05])
    button_accept = Button(ax_button_accept, 'Accept', color='lightgreen')
    button_skip = Button(ax_button_skip, 'Skip', color='lightcoral')
    button_accept.on_clicked(accept)
    button_skip.on_clicked(skip)
    
    # Initial plot
    update()
    plt.show()
    
    return result

def main():
    """Main execution flow"""
    print("=== Benchtop vs Eval System Resonance Analysis ===")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize Tkinter
    root = Tk()
    root.withdraw()
    
    try:
        # Step 1: Load OSA data
        print("\n--- Step 1: Loading OSA Data ---")
        osaFolder = filedialog.askdirectory(
            title="Select the OSA folder containing .mat files",
            initialdir=r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\OSA"
        )
        if not osaFolder:
            raise FileNotFoundError("No OSA folder selected")

        osaFiles = [f for f in os.listdir(osaFolder) if f.endswith('.mat')]
        if not osaFiles:
            raise FileNotFoundError("No .mat files found in OSA folder")

        osaData = scipy.io.loadmat(os.path.join(osaFolder, osaFiles[0]))
        if 'polyfit_peakWL_vs_I_deg2_coeffs' not in osaData:
            raise KeyError("'polyfit_peakWL_vs_I_deg2_coeffs' not found in OSA file")

        osaPolyCoeffs = osaData['polyfit_peakWL_vs_I_deg2_coeffs'].flatten()
        print(f"  ✓ Loaded polynomial coefficients")

        # Step 2: Load benchtop data
        print("\n--- Step 2: Loading Benchtop Data ---")
        benchtopFile = filedialog.askopenfilename(
            title="Select BENCHTOP .mat file",
            filetypes=[("MAT files", "*.mat")],
            initialdir=r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\Benchtop"
        )
        if not benchtopFile:
            raise FileNotFoundError("No benchtop file selected")

        # Load and process benchtop data
        benchtopData = scipy.io.loadmat(benchtopFile)
        if 'wavelength' not in benchtopData or 'channel_4_mW' not in benchtopData:
            raise KeyError("'wavelength' or 'channel_4_mW' data not found in benchtop file")

        wavelengthBenchtop = np.array(benchtopData['wavelength']).flatten()
        powerBenchtop = np.array(benchtopData['channel_4_mW']).flatten()
        print(f"  ✓ Loaded benchtop data: {len(wavelengthBenchtop)} points")

        # Step 3: Load eval system data
        print("\n--- Step 3: Loading Eval System Data ---")
        evalFile = filedialog.askopenfilename(
            title="Select EVAL SYSTEM .mat file",
            filetypes=[("MAT files", "*.mat")],
            initialdir=r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\LIV"
        )
        if not evalFile:
            raise FileNotFoundError("No eval system file selected")

        # Load eval system data
        evalData = scipy.io.loadmat(evalFile)
        if 'current' not in evalData or 'power4' not in evalData:
            raise KeyError("'current' or 'power4' data not found in eval system file")

        current = np.array(evalData['current']).flatten()
        channel_3 = np.array(evalData['power4']).flatten()
        print(f"  ✓ Loaded eval system data: {len(current)} points")

        # Ask user about peak inversion
        is_inverted = messagebox.askyesno(
            "Peak Orientation Check",
            f"Analyzing: {os.path.basename(evalFile)}\n\n"
            "Are the peaks in power4 inverted (pointing down)?\n\n"  # ✓ Fixed text
            "Yes = Apply automatic correction\n"
            "No = Use original orientation"
        )

        if is_inverted:
            print("  ⚠ User indicated inverted peaks - applying correction")
            
            # MANUAL INVERSION (like standaloneQ_evalsys):
            power4_inverted = -channel_3  # Flip the peaks
            
            # NORMALIZE: Scale to [0, 1] with peaks at 1
            power_min = np.min(power4_inverted)
            power_max = np.max(power4_inverted)
            power4_normalized = (power4_inverted - power_min) / (power_max - power_min)
            
            channel_3 = power4_normalized
            print(f"  ✓ Peaks manually flipped and normalized to [0,1]")
        else:
            print("  ○ Using original peak orientation")
            # Regular normalization for non-inverted peaks
            channel_3 = (channel_3 - np.min(channel_3)) / (np.max(channel_3) - np.min(channel_3))

        # Filter current data between 20-50 mA
        validIdx = (current >= 20) & (current <= 50)
        currentFiltered = current[validIdx]
        powerFiltered = channel_3[validIdx]

        if len(currentFiltered) == 0:
            raise ValueError("No valid current values found in the range 20-50 mA")

        # Convert current to wavelength using OSA polynomial
        wavelengthOnChip = (
            osaPolyCoeffs[0] * currentFiltered**2 +
            osaPolyCoeffs[1] * currentFiltered +
            osaPolyCoeffs[2]
        )

        powerFilteredNormalized = powerFiltered
        print(f"  ✓ Processed eval system data: {len(wavelengthOnChip)} points")
        print(f"  ✓ Wavelength range: {wavelengthOnChip.min():.4f}-{wavelengthOnChip.max():.4f} nm")

        # Step 4: Process and align benchtop data
        print("\n--- Step 4: Processing Benchtop Data ---")
        
        # Limit benchtop data to match eval system wavelength range
        minWavelength = np.floor(min(wavelengthOnChip) * 10) / 10
        maxWavelength = np.ceil(max(wavelengthOnChip) * 10) / 10

        benchtopIdx = (wavelengthBenchtop >= minWavelength) & (wavelengthBenchtop <= maxWavelength)
        wavelengthBenchtopLimited = wavelengthBenchtop[benchtopIdx]
        powerBenchtopLimited = powerBenchtop[benchtopIdx]

        if len(wavelengthBenchtopLimited) == 0:
            raise ValueError("No benchtop data found within eval system wavelength range")

        # Normalize benchtop power
        powerBenchtopNormalized = powerBenchtopLimited / np.max(powerBenchtopLimited)
        print(f"  ✓ Limited benchtop data: {len(wavelengthBenchtopLimited)} points")
        print(f"  ✓ Wavelength range: {minWavelength:.1f}-{maxWavelength:.1f} nm")

        # Step 5: Find peaks
        print("\n--- Step 5: Peak Detection ---")
        
        # Find peaks for benchtop data
        benchtopPeaks, _ = find_peaks(powerBenchtopNormalized, height=0.4)
        benchtopPeakWavelengths = wavelengthBenchtopLimited[benchtopPeaks]
        benchtopPeakWavelengths = np.sort(benchtopPeakWavelengths)
        benchtopPeakDistances = np.diff(benchtopPeakWavelengths) * 1e3  # Convert to pm

        # Find peaks for eval system data
        onChipPeaks, _ = find_peaks(powerFilteredNormalized, height=0.2)
        onChipPeakWavelengths = wavelengthOnChip[onChipPeaks]
        onChipPeakWavelengths = np.sort(onChipPeakWavelengths)
        onChipPeakDistances = np.diff(onChipPeakWavelengths) * 1e3  # Convert to pm

        print(f"  ✓ Benchtop peaks found: {len(benchtopPeaks)}")
        print(f"  ✓ Eval system peaks found: {len(onChipPeaks)}")

        # Calculate window sizes
        benchtop_wavelength_spacing = np.median(np.diff(wavelengthBenchtopLimited))
        onchip_wavelength_spacing = np.median(np.diff(wavelengthOnChip))
        benchtop_window = max(20, int(0.04 / benchtop_wavelength_spacing))
        onchip_window = max(20, int(0.04 / onchip_wavelength_spacing))

        print(f"  ✓ Analysis windows: Benchtop={benchtop_window}, EvalSystem={onchip_window}")

        # Step 6: Create comparison folder and save initial data
        print("\n--- Step 6: Setting up Output ---")
        
        comparisonFolder = r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements"
        if not os.path.exists(comparisonFolder):
            os.makedirs(comparisonFolder)

        benchtopFileName = os.path.basename(benchtopFile)
        evalFileName = os.path.basename(evalFile)
        comparisonFileName = f"Comparison_OnChip_{benchtopFileName}"
        outputFile = os.path.join(comparisonFolder, comparisonFileName)

        # Save initial comparison data
        scipy.io.savemat(outputFile, {
            'wavelengthBenchtopLimited': wavelengthBenchtopLimited,
            'powerBenchtopNormalized': powerBenchtopNormalized,
            'benchtopPeakWavelengths': benchtopPeakWavelengths,
            'benchtopPeakDistances': benchtopPeakDistances,
            'wavelengthOnChip': wavelengthOnChip,
            'powerFilteredNormalized': powerFilteredNormalized,
            'onChipPeakWavelengths': onChipPeakWavelengths,
            'onChipPeakDistances': onChipPeakDistances
        })
        print(f"  ✓ Initial data saved to: {outputFile}")

        # Step 7: Create initial comparison plot
        print("\n--- Step 7: Creating Initial Comparison Plot ---")
        
        plt.figure(figsize=(12, 8))
        plt.tick_params(axis='both', which='major', labelsize=16)
        plt.plot(wavelengthBenchtopLimited, powerBenchtopNormalized, 
                color='black', linestyle='--', linewidth=1.5, label='Benchtop Laser')
        plt.plot(wavelengthOnChip, powerFilteredNormalized, 
                color='purple', linestyle='-', linewidth=1.5, label='On-Chip Laser')

        # Annotate benchtop FSR
        for i in range(len(benchtopPeakDistances)):
            x = (benchtopPeakWavelengths[i] + benchtopPeakWavelengths[i + 1]) / 2
            y = max(powerBenchtopNormalized) * (0.9 if i % 2 == 0 else 0.85)
            y_offset = 0.05 * (i % 2)
            plt.annotate(f"{benchtopPeakDistances[i]:.1f} pm", (x, y + y_offset), 
                        fontsize=PLOT_FONT_TEXT, color='black', ha='center')

        # Annotate eval system FSR
        for i in range(len(onChipPeakDistances)):
            x = (onChipPeakWavelengths[i] + onChipPeakWavelengths[i + 1]) / 2
            y = max(powerFilteredNormalized) * (0.5 if i % 2 == 0 else 0.75)
            y_offset = 0.05 * (i % 2)
            plt.annotate(f"{onChipPeakDistances[i]:.1f} pm", (x, y + y_offset), 
                        fontsize=PLOT_FONT_TEXT, color='purple', ha='center')

        plt.xlim([minWavelength, maxWavelength])
        plt.xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
        plt.ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
        plt.legend(loc='upper right', fontsize=PLOT_FONT_LEGEND)

        benchtopFileNameCleaned = os.path.splitext(benchtopFileName.replace("_data", ""))[0]
        onchipFileName = os.path.basename(evalFile)  # Get the eval file name
        onchipFileNameCleaned = os.path.splitext(onchipFileName.replace("_data", ""))[0]
        plt.title(f'Benchtop vs On-Chip Comparison\n({benchtopFileNameCleaned} vs {onchipFileNameCleaned})', 
             fontsize=PLOT_FONT_TITLE)
        plt.grid(True)

        # Save initial figure
        figureFileName = os.path.splitext(comparisonFileName)[0] + ".png"
        figureFilePath = os.path.join(comparisonFolder, figureFileName)
        plt.savefig(figureFilePath, format='png', dpi=300)
        print(f"  ✓ Initial comparison plot saved to: {figureFilePath}")
        plt.show()

        # Step 8: Q-factor analysis
        print("\n--- Step 8: Q-Factor Analysis ---")
        
        do_q_analysis = messagebox.askyesno("Q Factor Analysis", 
            "Do you want to perform quality factor (Q) analysis using Lorentzian fits?")

        if do_q_analysis:
            print("\n=== Performing Q Factor Analysis ===")
            
            # Ask for analysis mode
            use_interactive = messagebox.askyesno("Analysis Mode",
                "Use interactive peak selection?\n\nYes = Click to select peaks\nNo = Use auto-detected peaks")
            
            # Analyze Benchtop Data
            print("\n--- Benchtop Laser ---")
            
            if use_interactive:
                print("Please select peaks to analyze (close window when done)...")
                benchtopPeaks = interactive_peak_selection(
                    wavelengthBenchtopLimited, 
                    powerBenchtopNormalized,
                    title='Benchtop Laser - Select Peaks'
                )
                print(f"Selected {len(benchtopPeaks)} peaks for analysis")
            else:
                print(f"Using {len(benchtopPeaks)} auto-detected peaks")
            
            benchtop_Q_factors = []
            benchtop_FWHMs = []
            benchtop_results = []
            
            # Fit each benchtop peak
            for i, peak_idx in enumerate(benchtopPeaks):
                print(f"\nAnalyzing Benchtop Peak {i+1}/{len(benchtopPeaks)} at λ={wavelengthBenchtopLimited[peak_idx]:.4f} nm")
                
                peak_wavelength = wavelengthBenchtopLimited[peak_idx]
                save_filename = f"Benchtop_Peak{i+1}_lambda{peak_wavelength:.4f}nm_Baseline.png"
                save_path = os.path.join(comparisonFolder, save_filename)
                
                result = analyze_peak_with_adjustable_baseline(
                    wavelengthBenchtopLimited,
                    powerBenchtopNormalized,
                    peak_idx,
                    initial_window=benchtop_window,
                    save_path=save_path
                )
                
                if result['accept'] and result['params'] is not None:
                    benchtop_Q_factors.append(result['Q'])
                    params = result['params']
                    gamma = np.sqrt(abs(params[2])) * 2
                    benchtop_FWHMs.append(gamma)
                    benchtop_results.append({
                        'peak_idx': peak_idx,
                        'wavelength': params[1],
                        'Q': result['Q'],
                        'R2': result['R2'],
                        'FWHM': gamma,
                        'params': params
                    })
                    print(f"  ✓ Accepted: Q={result['Q']:.0f}, R²={result['R2']:.3f}")
                else:
                    print(f"  ✗ Skipped")

            # Analyze On-Chip Data (changed from "Eval System")
            print("\n--- On-Chip Laser ---")
            
            if use_interactive:
                print("Please select peaks to analyze (close window when done)...")
                onChipPeaks = interactive_peak_selection(
                    wavelengthOnChip,
                    powerFilteredNormalized,
                    title='On-Chip Laser - Select Peaks'  # Changed from 'Eval System Laser'
                )
                print(f"Selected {len(onChipPeaks)} peaks for analysis")
            else:
                print(f"Using {len(onChipPeaks)} auto-detected peaks")
            
            onchip_Q_factors = []  # Keep this variable name
            onchip_FWHMs = []     # Keep this variable name
            onchip_results = []   # Keep this variable name
            
            # Fit each on-chip peak
            for i, peak_idx in enumerate(onChipPeaks):
                print(f"\nAnalyzing On-Chip Peak {i+1}/{len(onChipPeaks)} at λ={wavelengthOnChip[peak_idx]:.4f} nm")
                
                peak_wavelength = wavelengthOnChip[peak_idx]
                save_filename = f"OnChip_Peak{i+1}_lambda{peak_wavelength:.4f}nm_Baseline.png"  # Changed from EvalSystem_
                save_path = os.path.join(comparisonFolder, save_filename)
                
                result = analyze_peak_with_adjustable_baseline(
                    wavelengthOnChip,
                    powerFilteredNormalized,
                    peak_idx,
                    initial_window=onchip_window,
                    save_path=save_path
                )
                
                if result['accept'] and result['params'] is not None:
                    onchip_Q_factors.append(result['Q'])
                    params = result['params']
                    gamma = np.sqrt(abs(params[2])) * 2
                    onchip_FWHMs.append(gamma)
                    onchip_results.append({
                        'peak_idx': peak_idx,
                        'wavelength': params[1],
                        'Q': result['Q'],
                        'R2': result['R2'],
                        'FWHM': gamma,
                        'params': params
                    })
                    print(f"  ✓ Accepted: Q={result['Q']:.0f}, R²={result['R2']:.3f}")
                else:
                    print(f"  ✗ Skipped")

            # Calculate FSR between consecutive analyzed peaks
            benchtop_analyzed_wavelengths = [r['wavelength'] for r in benchtop_results]
            benchtop_analyzed_FSRs = np.diff(benchtop_analyzed_wavelengths) * 1e3 if len(benchtop_results) > 1 else []
            
            onchip_analyzed_wavelengths = [r['wavelength'] for r in onchip_results]
            onchip_analyzed_FSRs = np.diff(onchip_analyzed_wavelengths) * 1e3 if len(onchip_results) > 1 else []

            # Summary Statistics
            print("\n=== Summary ===")
            if len(benchtop_Q_factors) > 0:
                print(f"Benchtop: Avg Q = {np.mean(benchtop_Q_factors):.0f} ± {np.std(benchtop_Q_factors):.0f}")
                print(f"          Avg FWHM = {np.mean(benchtop_FWHMs)*1e3:.1f} pm ± {np.std(benchtop_FWHMs)*1e3:.1f} pm")
                if len(benchtop_analyzed_FSRs) > 0:
                    print(f"          Avg FSR = {np.mean(benchtop_analyzed_FSRs):.1f} ± {np.std(benchtop_analyzed_FSRs):.1f} pm")
                    benchtop_finesse = np.mean(benchtop_analyzed_FSRs) / (np.mean(benchtop_FWHMs)*1e3)
                    print(f"          Finesse = {benchtop_finesse:.1f}")
                else:
                    print(f"          Avg FSR = Not enough peaks")
            else:
                print("Benchtop: No valid Q factors")
            
            if len(onchip_Q_factors) > 0:
                print(f"On-Chip: Avg Q = {np.mean(onchip_Q_factors):.0f} ± {np.std(onchip_Q_factors):.0f}")
                print(f"         Avg FWHM = {np.mean(onchip_FWHMs)*1e3:.1f} pm ± {np.std(onchip_FWHMs)*1e3:.1f} pm")
                if len(onchip_analyzed_FSRs) > 0:
                    print(f"         Avg FSR = {np.mean(onchip_analyzed_FSRs):.1f} ± {np.std(onchip_analyzed_FSRs):.1f} pm")
                    onchip_finesse = np.mean(onchip_analyzed_FSRs) / (np.mean(onchip_FWHMs)*1e3)
                    print(f"         Finesse = {onchip_finesse:.1f}")
                else:
                    print(f"         Avg FSR = Not enough peaks")
            else:
                print("On-Chip: No valid Q factors")

            # Create zoomed overlay plot showing only analyzed peaks
            if len(benchtop_results) > 0 or len(onchip_results) > 0:
                print("\n--- Creating Zoomed Overlay Plot (Analyzed Peaks Only) ---")
                
                # Calculate wavelength range from all analyzed peaks
                all_analyzed_wavelengths = []
                if len(benchtop_results) > 0:
                    all_analyzed_wavelengths.extend([r['wavelength'] for r in benchtop_results])
                if len(onchip_results) > 0:
                    all_analyzed_wavelengths.extend([r['wavelength'] for r in onchip_results])
                
                if len(all_analyzed_wavelengths) > 0:
                    wl_min = min(all_analyzed_wavelengths)
                    wl_max = max(all_analyzed_wavelengths)
                    wl_margin = (wl_max - wl_min) * 0.15  # 15% margin
                    zoom_wl_min = wl_min - wl_margin
                    zoom_wl_max = wl_max + wl_margin
                    
                    # Filter data to zoomed range
                    benchtop_zoom_idx = (wavelengthBenchtopLimited >= zoom_wl_min) & (wavelengthBenchtopLimited <= zoom_wl_max)
                    onchip_zoom_idx = (wavelengthOnChip >= zoom_wl_min) & (wavelengthOnChip <= zoom_wl_max)
                    
                    benchtop_zoom_wl = wavelengthBenchtopLimited[benchtop_zoom_idx]
                    benchtop_zoom_power = powerBenchtopNormalized[benchtop_zoom_idx]
                    onchip_zoom_wl = wavelengthOnChip[onchip_zoom_idx]
                    onchip_zoom_power = powerFilteredNormalized[onchip_zoom_idx]
                    
                    # Create zoomed figure
                    fig_zoom = plt.figure(figsize=(14, 9))
                    plt.tick_params(axis='both', which='major', labelsize=14)
                    
                    # Plot data
                    plt.plot(benchtop_zoom_wl, benchtop_zoom_power, color='black', linestyle='--', 
                            linewidth=2, label='Benchtop Laser', alpha=0.8)
                    plt.plot(onchip_zoom_wl, onchip_zoom_power, color='purple', linestyle='-', 
                            linewidth=2, label='On-Chip Laser', alpha=0.8)
                    
                    # Fixed annotation positions
                    benchtop_q_y = 0.88      # Benchtop Q labels
                    benchtop_fsr_y = 0.76    # Benchtop FSR arrows
                    onchip_q_y = 0.60        # Eval system Q labels  
                    onchip_fsr_y = 0.48      # Eval system FSR arrows
                    
                    # Plot benchtop analyzed peaks with Q annotations
                    if len(benchtop_results) > 0:
                        for i, res in enumerate(benchtop_results):
                            wl = res['wavelength']
                            nearest_idx = np.argmin(np.abs(wavelengthBenchtopLimited - wl))
                            y_val = powerBenchtopNormalized[nearest_idx]
                            
                            # Vertical line from peak to Q label
                            plt.plot([wl, wl], [y_val, benchtop_q_y], 'k:', linewidth=1.5, alpha=0.6, zorder=1)
                            
                            # Peak marker
                            plt.plot([wl], [y_val], 'k^', markersize=10, zorder=5, 
                                    markeredgecolor='darkgray', markeredgewidth=1)
                            
                            # Q label at FIXED height
                            plt.text(wl, benchtop_q_y + 0.02,
                                    f"Q={res['Q']:.0f}\n{res['FWHM']*1e3:.1f}pm",
                                    fontsize=PLOT_FONT_TEXT, ha='center', color='black', va='bottom',
                                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                            alpha=0.9, edgecolor='black', linewidth=1.5))
                        
                        # Benchtop FSR arrows at fixed position
                        if len(benchtop_analyzed_FSRs) > 0:
                            for i in range(len(benchtop_analyzed_FSRs)):
                                x_start = benchtop_analyzed_wavelengths[i]
                                x_end = benchtop_analyzed_wavelengths[i+1]
                                x_mid = (x_start + x_end) / 2
                                
                                plt.annotate('', xy=(x_end, benchtop_fsr_y),
                                           xytext=(x_start, benchtop_fsr_y),
                                           arrowprops=dict(arrowstyle='<->', color='black', lw=2.5))
                                plt.text(x_mid, benchtop_fsr_y - 0.02, 
                                        f"FSR={benchtop_analyzed_FSRs[i]:.1f}pm",
                                        fontsize=PLOT_FONT_TEXT, ha='center', color='black', va='top',
                                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                                alpha=0.9, edgecolor='black'))
                    
                    # Plot eval system analyzed peaks with Q annotations
                    if len(onchip_results) > 0:
                        for i, res in enumerate(onchip_results):
                            wl = res['wavelength']
                            nearest_idx = np.argmin(np.abs(wavelengthOnChip - wl))
                            y_val = powerFilteredNormalized[nearest_idx]
                            
                            # Vertical line from peak to Q label
                            plt.plot([wl, wl], [y_val, onchip_q_y], 'm:', linewidth=1.5, alpha=0.6, zorder=1)
                            
                            # Peak marker
                            plt.plot([wl], [y_val], 'mv', markersize=10, zorder=5,
                                    markeredgecolor='darkmagenta', markeredgewidth=1)
                            
                            # Q label at FIXED height
                            plt.text(wl, onchip_q_y + 0.02,
                                    f"Q={res['Q']:.0f}\n{res['FWHM']*1e3:.1f}pm",
                                    fontsize=PLOT_FONT_TEXT, ha='center', color='purple', va='bottom',
                                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                            alpha=0.9, edgecolor='purple', linewidth=1.5))
                        
                        # Eval system FSR arrows at fixed position
                        if len(onchip_analyzed_FSRs) > 0:
                            for i in range(len(onchip_analyzed_FSRs)):
                                x_start = onchip_analyzed_wavelengths[i]
                                x_end = onchip_analyzed_wavelengths[i+1]
                                x_mid = (x_start + x_end) / 2
                                
                                plt.annotate('', xy=(x_end, onchip_fsr_y),
                                           xytext=(x_start, onchip_fsr_y),
                                           arrowprops=dict(arrowstyle='<->', color='purple', lw=2.5))
                                plt.text(x_mid, onchip_fsr_y - 0.02, 
                                        f"FSR={onchip_analyzed_FSRs[i]:.1f}pm",
                                        fontsize=10, ha='center', color='purple', va='top',
                                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                                alpha=0.9, edgecolor='purple'))
                    
                    # Configure plot
                    plt.xlim([zoom_wl_min, zoom_wl_max])
                    plt.ylim([0, 1.05])
                    plt.xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
                    plt.ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
                    plt.legend(loc='upper right', fontsize=PLOT_FONT_LEGEND)
                    
                    # Title with summary statistics
                    title_lines = [f'Q-Factor Analysis - Analyzed Peaks Only ({benchtopFileNameCleaned} vs {onchipFileNameCleaned})']
                    
                    # Add summary stats if both datasets have results
                    if len(benchtop_Q_factors) > 0 and len(onchip_Q_factors) > 0:
                        title_lines.append(
                            f'Benchtop: Avg Q={np.mean(benchtop_Q_factors):.0f}±{np.std(benchtop_Q_factors):.0f}, '
                            f'FSR={np.mean(benchtop_analyzed_FSRs):.1f}±{np.std(benchtop_analyzed_FSRs):.1f}pm | '
                            f'On-Chip: Avg Q={np.mean(onchip_Q_factors):.0f}±{np.std(onchip_Q_factors):.0f}, '
                            f'FSR={np.mean(onchip_analyzed_FSRs):.1f}±{np.std(onchip_analyzed_FSRs):.1f}pm'
                        )
                    elif len(benchtop_Q_factors) > 0:
                        title_lines.append(
                            f'Benchtop: Avg Q={np.mean(benchtop_Q_factors):.0f}±{np.std(benchtop_Q_factors):.0f}, '
                            f'FSR={np.mean(benchtop_analyzed_FSRs):.1f}±{np.std(benchtop_analyzed_FSRs):.1f}pm'
                        )
                    elif len(onchip_Q_factors) > 0:
                        title_lines.append(
                            f'On-Chip: Avg Q={np.mean(onchip_Q_factors):.0f}±{np.std(onchip_Q_factors):.0f}, '
                            f'FSR={np.mean(onchip_analyzed_FSRs):.1f}±{np.std(onchip_analyzed_FSRs):.1f}pm'
                        )

                    plt.title('\n'.join(title_lines), fontsize=PLOT_FONT_TITLE, pad=20)
                    plt.grid(True, alpha=0.3, linestyle='--')
                    plt.tight_layout()
                    
                    # Save zoomed figure
                    zoom_filename = os.path.splitext(comparisonFileName)[0] + "_Q_Analysis_Zoomed.png"
                    zoom_filepath = os.path.join(comparisonFolder, zoom_filename)
                    plt.savefig(zoom_filepath, format='png', dpi=300, bbox_inches='tight')
                    print(f"✓ Zoomed Q-analysis plot saved to: {zoom_filepath}")
                    plt.show()

            # Save final results with complete Q-factor data
            scipy.io.savemat(outputFile, {
                # Benchtop data
                'wavelengthBenchtopLimited': wavelengthBenchtopLimited,
                'powerBenchtopNormalized': powerBenchtopNormalized,
                'benchtopPeakWavelengths': benchtopPeakWavelengths,
                'benchtopPeakDistances': benchtopPeakDistances,
                'benchtop_Q_factors': benchtop_Q_factors,
                'benchtop_FWHMs': benchtop_FWHMs,
                'benchtop_FSRs': benchtop_analyzed_FSRs if len(benchtop_results) > 0 else [],
                'benchtop_fit_params': [r['params'] for r in benchtop_results] if len(benchtop_results) > 0 else [],
                'benchtop_fit_A': [r['params'][0] for r in benchtop_results] if len(benchtop_results) > 0 else [],
                'benchtop_fit_x0': [r['params'][1] for r in benchtop_results] if len(benchtop_results) > 0 else [],
                'benchtop_fit_gamma': [r['params'][2] for r in benchtop_results] if len(benchtop_results) > 0 else [],
                'benchtop_fit_C': [r['params'][3] for r in benchtop_results] if len(benchtop_results) > 0 else [],
                'benchtop_avg_Q': np.mean(benchtop_Q_factors) if len(benchtop_Q_factors) > 0 else np.nan,
                'benchtop_std_Q': np.std(benchtop_Q_factors) if len(benchtop_Q_factors) > 0 else np.nan,
                'benchtop_avg_FWHM': np.mean(benchtop_FWHMs) if len(benchtop_FWHMs) > 0 else np.nan,
                'benchtop_std_FWHM': np.std(benchtop_FWHMs) if len(benchtop_FWHMs) > 0 else np.nan,
                'benchtop_avg_FSR': np.mean(benchtop_analyzed_FSRs) if len(benchtop_results) > 1 else np.nan,
                'benchtop_std_FSR': np.std(benchtop_analyzed_FSRs) if len(benchtop_results) > 1 else np.nan,
                'benchtop_finesse': (np.mean(benchtop_analyzed_FSRs) / (np.mean(benchtop_FWHMs)*1e3)) if len(benchtop_results) > 1 else np.nan,
                
                # On-chip data (exactly matching your reference structure)
                'wavelengthOnChip': wavelengthOnChip,
                'powerFilteredNormalized': powerFilteredNormalized,
                'onChipPeakWavelengths': onChipPeakWavelengths,
                'onChipPeakDistances': onChipPeakDistances,
                'onchip_Q_factors': onchip_Q_factors,
                'onchip_FWHMs': onchip_FWHMs,
                'onchip_FSRs': onchip_analyzed_FSRs if len(onchip_results) > 0 else [],
                'onchip_fit_params': [r['params'] for r in onchip_results] if len(onchip_results) > 0 else [],
                'onchip_fit_A': [r['params'][0] for r in onchip_results] if len(onchip_results) > 0 else [],
                'onchip_fit_x0': [r['params'][1] for r in onchip_results] if len(onchip_results) > 0 else [],
                'onchip_fit_gamma': [r['params'][2] for r in onchip_results] if len(onchip_results) > 0 else [],
                'onchip_fit_C': [r['params'][3] for r in onchip_results] if len(onchip_results) > 0 else [],
                'onchip_avg_Q': np.mean(onchip_Q_factors) if len(onchip_Q_factors) > 0 else np.nan,
                'onchip_std_Q': np.std(onchip_Q_factors) if len(onchip_Q_factors) > 0 else np.nan,
                'onchip_avg_FWHM': np.mean(onchip_FWHMs) if len(onchip_FWHMs) > 0 else np.nan,
                'onchip_std_FWHM': np.std(onchip_FWHMs) if len(onchip_FWHMs) > 0 else np.nan,
                'onchip_avg_FSR': np.mean(onchip_analyzed_FSRs) if len(onchip_results) > 1 else np.nan,
                'onchip_std_FSR': np.std(onchip_analyzed_FSRs) if len(onchip_results) > 1 else np.nan,
                'onchip_finesse': (np.mean(onchip_analyzed_FSRs) / (np.mean(onchip_FWHMs)*1e3)) if len(onchip_results) > 1 else np.nan
            })
            print(f"\n✓ Final results saved to: {outputFile}")

        print(f"\n=== Analysis Complete ===")
        print(f"Results saved in: {comparisonFolder}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        messagebox.showerror("Error", str(e))
        return

if __name__ == "__main__":
    main()