# author: sheri and co-pilot
# date: 2025-10-28
# Description: Standalone script for Q-factor analysis of on-chip laser data from eval_system.
# Extracts wavelength from OSA polynomial fit, converts current to wavelength for LIV data,
# handles inverted peaks in 'power4' channel, and performs Lorentzian fitting with 
# interactive baseline adjustment.

import os
from datetime import datetime
from tkinter import Tk, filedialog, messagebox
import scipy.io
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from lorentzfit import lorentzfit
from matplotlib.widgets import Slider, Button
from matplotlib.backend_bases import MouseButton

# Plot font constants
PLOT_FONT_AXIS_LABEL = 18
PLOT_FONT_AXIS_TICKS = 18
PLOT_FONT_TITLE = 14
PLOT_FONT_LEGEND = 16
PLOT_FONT_TEXT = 9

def analyze_peak_with_adjustable_baseline(x, y, peak_idx, initial_window=15, save_path=None):
    """
    Interactive baseline adjustment for a single peak.
    Use sliders to adjust baseline window and polynomial order.
    
    Parameters:
    -----------
    x : array
        Wavelength data
    y : array
        Power data (normalized, peaks pointing UP)
    peak_idx : int
        Index of peak to analyze
    initial_window : int
        Initial window size for peak region
    save_path : str, optional
        Path to save the figure when accepted
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
        """Calculate polynomial baseline using points outside the peak window"""
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
        """Update plots when slider values change"""
        left_win = int(slider_left.val)
        right_win = int(slider_right.val)
        order = int(slider_order.val)
        
        baseline_peak, baseline_full, baseline_x_pts, baseline_y_pts = calculate_baseline(
            left_win, right_win, order
        )
        
        # Baseline-corrected data
        normalized_curve = peak_y - baseline_peak
        
        # Normalize to [0,1] range
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
            gamma = np.sqrt(abs(params[2])) * 2
            Q_factor = x0 / gamma if gamma != 0 else np.nan
            R_sq = 1 - np.var(normalized_curve_lin - yfit) / np.var(normalized_curve_lin)
            
            print(f"\n  Fit Coefficients:")
            print(f"    A (P1)  = {params[0]:.6e}")
            print(f"    x₀ (P2) = {params[1]:.6f} nm")
            print(f"    γ (P3)  = {params[2]:.6e} nm²")
            print(f"    C       = {params[3]:.6e}")
            print(f"    FWHM    = {gamma*1e3:.2f} pm")
            print(f"    Q       = {Q_factor:.0f}")
            print(f"    R²      = {R_sq:.3f}")
            
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
        ax_main.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
        ax_main.set_ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
        ax_main.set_title('Original Data with Baseline', fontsize=PLOT_FONT_TITLE)
        ax_main.legend(fontsize=PLOT_FONT_LEGEND)
        ax_main.grid(True)
        
        # Plot 2: Baseline detail
        ax_baseline.plot(peak_x, peak_y, '.b', markersize=5, label='Peak data')
        ax_baseline.plot(peak_x, baseline_peak, 'r-', linewidth=2, label='Baseline')
        ax_baseline.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
        ax_baseline.set_ylabel('Power', fontsize=PLOT_FONT_AXIS_LABEL)
        ax_baseline.set_title('Baseline Detail (Peak Region)', fontsize=PLOT_FONT_TITLE)
        ax_baseline.legend(fontsize=PLOT_FONT_LEGEND)
        ax_baseline.grid(True)
        
        # Plot 3: Fitted data
        if fit_success:
            ax_fit.plot(peak_x, normalized_curve_lin, '.b', markersize=5, 
                       label='Normalized data')
            ax_fit.plot(peak_x, yfit, 'r-', linewidth=2, label='Lorentz fit')
            
            half_max = (np.max(yfit) + np.min(yfit)) / 2
            ax_fit.axhline(half_max, color='gray', linestyle='--', linewidth=1, 
                          label=f'Half-max ({half_max:.2f})')
            
            fwhm_indices = np.where(yfit >= half_max)[0]
            if len(fwhm_indices) >= 2:
                fwhm_wl_left = peak_x[fwhm_indices[0]]
                fwhm_wl_right = peak_x[fwhm_indices[-1]]
                ax_fit.plot([fwhm_wl_left, fwhm_wl_right], [half_max, half_max],
                           'mo-', linewidth=3, markersize=8, label=f'FWHM = {gamma*1e3:.1f} pm')
            
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
            ax_residual.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
            ax_residual.set_ylabel('Residuals', fontsize=PLOT_FONT_AXIS_LABEL)
            ax_residual.set_title('Fit Residuals', fontsize=PLOT_FONT_TITLE)
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
    
    slider_left = Slider(ax_slider_left, 'Left Window', 0, 50, 
                         valinit=10, valstep=1)
    slider_right = Slider(ax_slider_right, 'Right Window', 0, 50, 
                          valinit=10, valstep=1)
    slider_order = Slider(ax_slider_order, 'Poly Order', 0, 3, 
                          valinit=1, valstep=1)
    
    slider_left.on_changed(update)
    slider_right.on_changed(update)
    slider_order.on_changed(update)
    
    # Add Accept/Skip buttons
    result = {'accept': False, 'Q': np.nan, 'R2': np.nan, 'params': None}
    
    def accept(event):
        """Save results and close when Accept is clicked"""
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
        """Close without saving when Skip is clicked"""
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


def interactive_peak_selection(x, y, title='Select peaks to analyze'):
    """
    Interactive plot for selecting peaks to analyze.
    Left-click to select peaks, right-click to remove, close when done.
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
    
    scatter = ax.scatter([], [], c='red', s=100, marker='^', 
                        label='Selected peaks', zorder=5)
    
    def onclick(event):
        """Handle mouse click events for peak selection"""
        if event.inaxes != ax:
            return
        
        if event.button == MouseButton.LEFT:
            # Find nearest data point and add peak
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
        """Update scatter plot of selected peaks"""
        if selected_peaks:
            scatter.set_offsets(np.c_[x[selected_peaks], y[selected_peaks]])
        else:
            scatter.set_offsets(np.empty((0, 2)))
        fig.canvas.draw()
    
    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()
    
    return sorted(selected_peaks)


# ============================================================================
# MAIN SCRIPT - DATA EXTRACTION AND Q ANALYSIS
# ============================================================================

print("=== On-Chip Laser Q-Factor Analysis (eval_system) ===")
print("Script run at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Initialize Tkinter
root = Tk()
root.withdraw()

# =============================================================================
# STEP 1: Load OSA data to get wavelength-current relationship
# =============================================================================
print("\n--- Step 1: Load OSA Polynomial Fit ---")
osaFolder = filedialog.askdirectory(
    title="Select the OSA folder containing .mat files",
    initialdir=r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\OSA"
)
if not osaFolder:
    raise FileNotFoundError("No OSA folder selected.")

osaFiles = [f for f in os.listdir(osaFolder) if f.endswith('.mat')]
if not osaFiles:
    raise FileNotFoundError("No .mat files found in OSA folder.")

osaData = scipy.io.loadmat(os.path.join(osaFolder, osaFiles[0]))
if 'polyfit_peakWL_vs_I_deg2_coeffs' not in osaData:
    raise KeyError("'polyfit_peakWL_vs_I_deg2_coeffs' not found in OSA file.")

polyfit_coeffs = osaData['polyfit_peakWL_vs_I_deg2_coeffs'].flatten()
print(f"Loaded OSA polynomial: λ(I) = {polyfit_coeffs[0]:.6e}·I² + {polyfit_coeffs[1]:.6e}·I + {polyfit_coeffs[2]:.6f}")

# =============================================================================
# STEP 2: Load LIV data (eval_system format with 'power4' channel)
# =============================================================================
print("\n--- Step 2: Load LIV Data ---")
livFolder = filedialog.askdirectory(
    title="Select the LIV folder containing .mat files",
    initialdir=r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\LIV"
)
if not livFolder:
    raise FileNotFoundError("No LIV folder selected.")

livFiles = [f for f in os.listdir(livFolder) if f.endswith('.mat')]
if not livFiles:
    raise FileNotFoundError("No .mat files found in LIV folder.")

livData = scipy.io.loadmat(os.path.join(livFolder, livFiles[0]))

# Check for 'power4' channel (eval_system format)
if 'current' not in livData or 'power4' not in livData:
    raise KeyError("'current' or 'power4' data not found in LIV file. Check file format.")

current = np.array(livData['current']).flatten()
power4 = np.array(livData['power4']).flatten()

print(f"Loaded LIV data: {len(current)} points")
print(f"Current range: {current.min():.2f} - {current.max():.2f} mA")
print(f"Power4 range: {power4.min():.4f} - {power4.max():.4f}")

# =============================================================================
# STEP 3: Filter current range (20-50 mA) and convert to wavelength
# =============================================================================
print("\n--- Step 3: Filter and Convert to Wavelength ---")
validIdx = (current >= 20) & (current <= 50)
currentFiltered = current[validIdx]
powerFiltered = power4[validIdx]

if len(currentFiltered) == 0:
    raise ValueError("No data in 20-50 mA range. Adjust range or check data.")

# Convert current to wavelength using OSA polynomial
wavelength = (
    polyfit_coeffs[0] * currentFiltered**2 +
    polyfit_coeffs[1] * currentFiltered +
    polyfit_coeffs[2]
)

print(f"Filtered to {len(currentFiltered)} points (20-50 mA)")
print(f"Wavelength range: {wavelength.min():.4f} - {wavelength.max():.4f} nm")

# =============================================================================
# STEP 4: Handle inverted peaks - REVERSE and NORMALIZE
# =============================================================================
print("\n--- Step 4: Invert and Normalize Power ---")
print(f"Original power range: {powerFiltered.min():.4f} - {powerFiltered.max():.4f}")

# INVERT: Flip upside down (peaks were pointing down, now point up)
power_inverted = -powerFiltered

# NORMALIZE: Scale to [0, 1] with peaks at 1
power_min = np.min(power_inverted)
power_max = np.max(power_inverted)
power_normalized = (power_inverted - power_min) / (power_max - power_min)

print(f"After inversion and normalization: {power_normalized.min():.4f} - {power_normalized.max():.4f}")

# =============================================================================
# STEP 5: Find peaks in normalized data
# =============================================================================
print("\n--- Step 5: Detect Peaks ---")
peaks, _ = find_peaks(power_normalized, height=0.4)
print(f"Auto-detected {len(peaks)} peaks")

if len(peaks) == 0:
    print("WARNING: No peaks detected. Try lowering height threshold.")
    peaks, _ = find_peaks(power_normalized, height=0.2)
    print(f"Retrying with lower threshold: {len(peaks)} peaks found")

# Calculate data spacing and window size
wavelength_spacing = np.median(np.diff(wavelength))
window_size = max(20, int(0.04 / wavelength_spacing))
print(f"Data spacing: {wavelength_spacing*1e3:.4f} pm")
print(f"Peak window size: {window_size} points ({window_size*wavelength_spacing*1e3:.1f} pm)")

# =============================================================================
# STEP 6: Create output folder and save overview
# =============================================================================
print("\n--- Step 6: Create Output Folder ---")
output_folder = livFolder  # Save in same folder as LIV data
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
analysis_folder = os.path.join(output_folder, f"Q_Analysis_OnChip_{timestamp}")
os.makedirs(analysis_folder, exist_ok=True)
print(f"Output folder: {analysis_folder}")

# Show initial overview plot
plt.figure(figsize=(12, 6))
plt.plot(wavelength, power_normalized, '-k', linewidth=1.5, label='On-Chip Data (Normalized)')
plt.plot(wavelength[peaks], power_normalized[peaks], 'r^', markersize=10, label=f'Auto-detected peaks ({len(peaks)})')
plt.xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
plt.ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
plt.title(f'On-Chip Laser Spectrum\n{os.path.basename(livFiles[0])}', fontsize=PLOT_FONT_TITLE)
plt.grid(True)
plt.legend(fontsize=PLOT_FONT_LEGEND)
plt.tight_layout()
overview_file = os.path.join(analysis_folder, "00_Overview.png")
plt.savefig(overview_file, dpi=300)
print(f"Overview saved: {overview_file}")
plt.show()

# =============================================================================
# STEP 7: Interactive peak selection
# =============================================================================
print("\n--- Step 7: Peak Selection ---")
use_interactive = messagebox.askyesno("Peak Selection", 
    f"Auto-detected {len(peaks)} peaks.\n\nUse interactive selection?\n\nYes = Click to select\nNo = Use auto-detected")

if use_interactive:
    print("Interactive mode: Click peaks to select...")
    peaks = interactive_peak_selection(wavelength, power_normalized, 
                                      title='Select Peaks for Q Analysis')
    print(f"Selected {len(peaks)} peaks")

if len(peaks) == 0:
    print("No peaks selected. Exiting.")
    exit()

# =============================================================================
# STEP 8: Analyze each peak with interactive baseline adjustment
# =============================================================================
print(f"\n=== Analyzing {len(peaks)} Peaks ===")
results = []
Q_factors = []
FWHMs = []

for i, peak_idx in enumerate(peaks):
    peak_wl = wavelength[peak_idx]
    print(f"\n[Peak {i+1}/{len(peaks)}] λ = {peak_wl:.4f} nm")
    print("Adjust baseline with sliders, then Accept or Skip")
    
    save_filename = f"Peak{i+1:02d}_lambda{peak_wl:.4f}nm.png"
    save_path = os.path.join(analysis_folder, save_filename)
    
    result = analyze_peak_with_adjustable_baseline(
        wavelength,
        power_normalized,
        peak_idx,
        initial_window=window_size,
        save_path=save_path
    )
    
    if result['accept'] and result['params'] is not None:
        params = result['params']
        gamma = np.sqrt(abs(params[2])) * 2
        
        results.append({
            'peak_idx': peak_idx,
            'wavelength': params[1],
            'Q': result['Q'],
            'R2': result['R2'],
            'FWHM': gamma,
            'params': params
        })
        Q_factors.append(result['Q'])
        FWHMs.append(gamma)
        print(f"  ✓ Accepted: Q={result['Q']:.0f}, R²={result['R2']:.3f}, FWHM={gamma*1e3:.1f} pm")
    else:
        print(f"  ✗ Skipped")

# =============================================================================
# STEP 9: Create summary plot
# =============================================================================
if len(results) > 0:
    print(f"\n=== Creating Summary (accepted {len(results)}/{len(peaks)} peaks) ===")
    
    fig, (ax_main, ax_bar) = plt.subplots(2, 1, figsize=(12, 8),
                                           gridspec_kw={'height_ratios': [3, 1]})
    
    # Main plot with Q annotations
    ax_main.plot(wavelength, power_normalized, '-k', linewidth=1.5, label='On-Chip Data')
    
    analyzed_wavelengths = [r['wavelength'] for r in results]
    FSRs = np.diff(analyzed_wavelengths) * 1e3  # pm
    
    for res in results:
        peak_idx = res['peak_idx']
        ax_main.plot([res['wavelength']], [power_normalized[peak_idx]], 
                     'r^', markersize=10)
        ax_main.text(res['wavelength'], power_normalized[peak_idx]*0.92,
                    f"Q={res['Q']:.0f}\nFWHM={res['FWHM']*1e3:.1f}pm", 
                    fontsize=PLOT_FONT_TEXT, ha='center', color='purple', va='top',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    # FSR annotations
    for i in range(len(FSRs)):
        x_mid = (analyzed_wavelengths[i] + analyzed_wavelengths[i+1]) / 2
        y_pos = max(power_normalized) * 0.4
        ax_main.annotate('', xy=(analyzed_wavelengths[i+1], y_pos), 
                       xytext=(analyzed_wavelengths[i], y_pos),
                       arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
        ax_main.text(x_mid, y_pos*0.95, f"FSR={FSRs[i]:.1f}pm",
                fontsize=PLOT_FONT_TEXT, ha='center', color='blue', va='top',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    ax_main.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
    ax_main.set_ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
    
    if len(FSRs) > 0:
        finesse = np.mean(FSRs) / (np.mean(FWHMs)*1e3)
        ax_main.set_title(f'On-Chip Q-Factor Analysis Summary\n' +
                         f'Avg Q = {np.mean(Q_factors):.0f} ± {np.std(Q_factors):.0f}, ' +
                         f'Avg FSR = {np.mean(FSRs):.1f} ± {np.std(FSRs):.1f} pm, ' +
                         f'Finesse = {finesse:.1f}',
                         fontsize=PLOT_FONT_TITLE)
    else:
        ax_main.set_title(f'On-Chip Q-Factor Analysis Summary\n' +
                         f'Avg Q = {np.mean(Q_factors):.0f} ± {np.std(Q_factors):.0f}',
                         fontsize=PLOT_FONT_TITLE)
    
    ax_main.set_ylim([0, 1.05])
    ax_main.legend(fontsize=PLOT_FONT_LEGEND)
    ax_main.grid(True)
    
    # Bar chart of Q factors
    ax_bar.bar(analyzed_wavelengths, Q_factors, width=0.01, color='purple', alpha=0.6)
    ax_bar.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
    ax_bar.set_ylabel('Q Factor', fontsize=PLOT_FONT_AXIS_LABEL)
    ax_bar.grid(True)
    
    plt.tight_layout()
    summary_file = os.path.join(analysis_folder, "Summary_Q_Analysis.png")
    plt.savefig(summary_file, dpi=300)
    print(f"Summary saved: {summary_file}")
    plt.show()
    
    # =============================================================================
    # STEP 10: Save MATLAB results
    # =============================================================================
    mat_file = os.path.join(analysis_folder, "Q_Analysis_Results.mat")
    scipy.io.savemat(mat_file, {
        'wavelength': wavelength,
        'power_normalized': power_normalized,
        'current_filtered': currentFiltered,
        'peak_wavelengths': analyzed_wavelengths,
        'Q_factors': Q_factors,
        'FWHMs': FWHMs,
        'FSRs': FSRs if len(FSRs) > 0 else [],
        'avg_Q': np.mean(Q_factors),
        'std_Q': np.std(Q_factors),
        'avg_FWHM': np.mean(FWHMs),
        'std_FWHM': np.std(FWHMs),
        'avg_FSR': np.mean(FSRs) if len(FSRs) > 0 else np.nan,
        'std_FSR': np.std(FSRs) if len(FSRs) > 0 else np.nan,
        'finesse': (np.mean(FSRs) / (np.mean(FWHMs)*1e3)) if len(FSRs) > 0 else np.nan,
        'fit_params': [r['params'] for r in results],
        'osa_polyfit_coeffs': polyfit_coeffs
    })
    print(f"MATLAB data saved: {mat_file}")
    
    # Print summary
    print("\n=== SUMMARY ===")
    print(f"Analyzed peaks: {len(results)}/{len(peaks)}")
    print(f"Avg Q-factor: {np.mean(Q_factors):.0f} ± {np.std(Q_factors):.0f}")
    print(f"Avg FWHM: {np.mean(FWHMs)*1e3:.2f} ± {np.std(FWHMs)*1e3:.2f} pm")
    if len(FSRs) > 0:
        print(f"Avg FSR: {np.mean(FSRs):.2f} ± {np.std(FSRs):.2f} pm")
        print(f"Finesse: {finesse:.1f}")
    
    print(f"\nAll results saved to: {analysis_folder}")
else:
    print("\nNo peaks accepted. Analysis complete.")

print("\n=== Done ===")