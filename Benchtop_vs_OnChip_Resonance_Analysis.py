# author: sheri and co-pilot
# date: 2025-05-31
# Description: This script processes OSA and LIV .mat files to compare benchtop and on-chip laser spectra.
# It generates a plot of wavelength vs normalized power, annotates FSRs, and saves the plot and data.
# After the first plot, the user is prompted to perform quality factor (Q) analysis using Lorentzian fits.
# If accepted, the script overlays Lorentzian fits and Q values for all peaks, and shows residuals.
#the Q analysis needs to be fine tuned more


import os
from datetime import datetime
from tkinter import Tk, filedialog, messagebox
import scipy.io
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import lorentzfit
print("Using lorentzfit from:", lorentzfit.__file__)
from lorentzfit import lorentzfit  # Make sure lorentzfit.py is in your PYTHONPATH
from analyze_resonance import analyze_resonance
from matplotlib.widgets import Slider, Button
from matplotlib.backend_bases import MouseButton

# Plot fonts
PLOT_FONT_AXIS_LABEL = 18
PLOT_FONT_AXIS_TICKS = 18
PLOT_FONT_TITLE = 14
PLOT_FONT_LEGEND = 16
PLOT_FONT_TEXT = 9

def analyze_peak_qfactor(x, y, peak_idx, window=None, color='r', label='Data', plot_title='Lorentzian Fit'):
    # Auto-calculate window if not provided
    if window is None:
        wavelength_spacing = np.median(np.diff(x))
        window = max(15, int(0.02 / wavelength_spacing))  # Target ~0.02 nm window
        print(f"  Auto window size: {window} points ({window*wavelength_spacing*1e3:.1f} pm)")
    
    left = max(0, peak_idx - window)
    right = min(len(x), peak_idx + window + 1)
    peak_x = x[left:right]
    peak_y = y[left:right]
    slope = (peak_y[-1] - peak_y[0]) / (peak_x[-1] - peak_x[0])
    baseline = slope * (peak_x - peak_x[0]) + peak_y[0]
    normalized_curve = peak_y - baseline
    normalized_curve_lin = normalized_curve - np.min(normalized_curve)
    if np.max(normalized_curve_lin) > 0:
        normalized_curve_lin = normalized_curve_lin / np.max(normalized_curve_lin)
    try:
        # Add better initial guess and increase maxfev
        p0_guess = [np.max(normalized_curve_lin) - np.min(normalized_curve_lin), 
                    peak_x[np.argmax(normalized_curve_lin)], 
                    (peak_x[-1] - peak_x[0])/10, 
                    np.min(normalized_curve_lin)]
        yfit, params, resnorm, residual = lorentzfit(
            peak_x, normalized_curve_lin, p0=p0_guess, nparams='3c'
        )
    except Exception as e:
        print(f"Fit failed for peak at {peak_x[len(peak_x)//2]:.3f} nm: {e}")
        return None
    
    x0 = params[1]
    gamma = np.sqrt(params[2]) * 2  # FWHM = 2*sqrt(gamma)
    Q_factor = x0 / gamma if gamma != 0 else np.nan
    R_sq = 1 - np.var(normalized_curve_lin - yfit) / np.var(normalized_curve_lin)
    
    # Print fit coefficients
    print(f"\nLorentzian Fit Coefficients:")
    print(f"  Model: y(x) = A/((x - x₀)² + γ) + C")
    print(f"  A (Amplitude, P1)    = {params[0]:.6e}")
    print(f"  x₀ (Center, P2)      = {params[1]:.6f} nm")
    print(f"  γ (Gamma², P3)       = {params[2]:.6e} nm²")
    print(f"  C (Baseline)         = {params[3]:.6e}")
    print(f"  FWHM = 2√γ           = {gamma*1e3:.2f} pm")
    print(f"  Q-factor             = {Q_factor:.2f}")
    print(f"  R²                   = {R_sq:.4f}")
    
    plt.figure(figsize=(7, 6))
    plt.plot(peak_x, normalized_curve_lin, '.', color=color, label=label)
    plt.plot(peak_x, yfit, '-', color='b', label='Lorentz fit')
    plt.axhline(0.5, color='k', linewidth=2, label='Normalized Power=0.5')
    plt.xlabel('Wavelength [nm]', fontsize=PLOT_FONT_AXIS_LABEL)
    plt.ylabel('Normalized Linear Power', fontsize=PLOT_FONT_AXIS_LABEL)
    plt.title(plot_title + f"\nQ={Q_factor:.2f}, R²={R_sq:.2f}\n" + 
             f"A={params[0]:.2e}, x₀={params[1]:.4f}nm, γ={params[2]:.2e}nm², C={params[3]:.2e}")
    plt.legend(fontsize=PLOT_FONT_LEGEND)
    plt.ylim([0, 1.01])
    plt.grid(True)
    plt.show()
    plt.figure(figsize=(7, 6))
    plt.plot(yfit, residual, '.', linewidth=2)
    plt.axhline(0, color='k')
    plt.xlabel('Fit Value', fontsize=PLOT_FONT_AXIS_LABEL)
    plt.ylabel('Residuals', fontsize=PLOT_FONT_AXIS_LABEL)
    plt.title('Residual Plot for Linear Scale', fontsize=PLOT_FONT_TITLE)
    plt.grid(True)
    plt.show()
    return Q_factor, R_sq, params, resnorm, residual

def analyze_peak_qfactor_overlay(x, y, peak_idx, window=10):
    left = max(0, peak_idx - window)
    right = min(len(x), peak_idx + window + 1)
    peak_x = x[left:right]
    peak_y = y[left:right]
    
    # Linear baseline
    slope = (peak_y[-1] - peak_y[0]) / (peak_x[-1] - peak_x[0])
    baseline = slope * (peak_x - peak_x[0]) + peak_y[0]
    normalized_curve = peak_y - baseline
    
    # Normalize to [0,1] keeping upward peaks
    ymin = np.min(normalized_curve)
    ymax = np.max(normalized_curve)
    if (ymax - ymin) > 0:
        normalized_curve_lin = (normalized_curve - ymin) / (ymax - ymin)
    else:
        normalized_curve_lin = normalized_curve
    
    try:
        # Initial guess for upward peak
        p0_guess = [
            ymax - ymin,                        # A > 0 (upward peak)
            peak_x[np.argmax(normalized_curve_lin)],  # x0
            ((peak_x[-1] - peak_x[0])/10)**2,   # gamma (squared width)
            0.0                                  # C (baseline = 0 after normalization)
        ]
        
        yfit, params, resnorm, residual = lorentzfit(
            peak_x, normalized_curve_lin, p0=p0_guess, nparams='3c'
        )
    except Exception as e:
        print(f"Fit failed: {e}")
        return None, None, None, None, None, None, None
    
    x0 = params[1]
    gamma = np.sqrt(abs(params[2])) * 2  # FWHM
    Q_factor = x0 / gamma if gamma != 0 else np.nan
    R_sq = 1 - np.var(normalized_curve_lin - yfit) / np.var(normalized_curve_lin)
    
    return peak_x, normalized_curve_lin, yfit, Q_factor, R_sq, residual, params

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
    ax.set_xlabel('Wavelength (nm)', fontsize=14)
    ax.set_ylabel('Normalized Power', fontsize=14)
    ax.set_title(f'{title}\nLeft-click: Add peak | Right-click: Remove nearest | Close window when done', 
                 fontsize=12)
    ax.grid(True)
    ax.legend()
    
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
    
    Parameters:
    -----------
    x : array
        Wavelength data
    y : array
        Power data
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
        # Calculate baseline using points OUTSIDE the peak window
        # Use global indices for the full dataset
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
            # Polynomial fit to baseline points
            p = np.polyfit(baseline_x, baseline_y, order)
            baseline_peak = np.polyval(p, peak_x)  # Baseline under peak
            baseline_full = np.polyval(p, x)  # Baseline for full dataset
        else:
            # Fallback: linear baseline using peak endpoints
            print(f"Warning: Not enough baseline points ({len(baseline_x)}), using linear fallback")
            slope = (peak_y[-1] - peak_y[0]) / (peak_x[-1] - peak_x[0])
            baseline_peak = slope * (peak_x - peak_x[0]) + peak_y[0]
            baseline_full = slope * (x - peak_x[0]) + peak_y[0]
            baseline_x = peak_x[[0, -1]]  # Just endpoints
            baseline_y = peak_y[[0, -1]]
        
        return baseline_peak, baseline_full, baseline_x, baseline_y
    
    def update(val=None):
        left_win = int(slider_left.val)
        right_win = int(slider_right.val)
        order = int(slider_order.val)
        
        baseline_peak, baseline_full, baseline_x_pts, baseline_y_pts = calculate_baseline(
            left_win, right_win, order
        )
        
        # Baseline-corrected data (subtract baseline from peak region)
        normalized_curve = peak_y - baseline_peak
        
        # Normalize to [0,1] range keeping peaks pointing UP (positive Lorentzian)
        ymin = np.min(normalized_curve)
        ymax = np.max(normalized_curve)
        if (ymax - ymin) > 0:
            normalized_curve_lin = (normalized_curve - ymin) / (ymax - ymin)
        else:
            normalized_curve_lin = normalized_curve
        
        # Perform Lorentzian fit
        try:
            # Initial guess for UPWARD peak (positive A)
            peak_height = np.max(normalized_curve_lin) - np.min(normalized_curve_lin)
            peak_center = peak_x[np.argmax(normalized_curve_lin)]
            peak_width = (peak_x[-1] - peak_x[0]) / 10
            baseline_level = np.min(normalized_curve_lin)
            
            p0_guess = [
                peak_height,      # A > 0 for upward peak
                peak_center,      # x0 (wavelength at peak)
                peak_width**2,    # gamma (width parameter, squared)
                baseline_level    # C (baseline offset)
            ]
            
            yfit, params, resnorm, residual = lorentzfit(
                peak_x, normalized_curve_lin, p0=p0_guess, nparams='3c'
            )
            
            x0 = params[1]
            gamma = np.sqrt(abs(params[2])) * 2  # FWHM from gamma parameter
            Q_factor = x0 / gamma if gamma != 0 else np.nan
            R_sq = 1 - np.var(normalized_curve_lin - yfit) / np.var(normalized_curve_lin)
            
            # Print fit coefficients to console
            print(f"\n  Fit Coefficients:")
            print(f"    A (P1)  = {params[0]:.6e}")
            print(f"    x₀ (P2) = {params[1]:.6f} nm")
            print(f"    γ (P3)  = {params[2]:.6e} nm²")
            print(f"    C       = {params[3]:.6e}")
            print(f"    FWHM    = {gamma*1e3:.2f} pm")
            
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
        
        # Plot 1: Original data with baseline (full dataset view)
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
        ax_main.legend(fontsize=9)
        ax_main.grid(True)
        
        # Plot 2: Baseline detail (zoomed to peak region)
        ax_baseline.plot(peak_x, peak_y, '.b', markersize=5, label='Peak data')
        ax_baseline.plot(peak_x, baseline_peak, 'r-', linewidth=2, label='Baseline')
        ax_baseline.set_xlabel('Wavelength (nm)')
        ax_baseline.set_ylabel('Power')
        ax_baseline.set_title('Baseline Detail (Peak Region)')
        ax_baseline.legend()
        ax_baseline.grid(True)
        
        # Plot 3: Normalized and fitted (UPWARD peak)
        if fit_success:
            ax_fit.plot(peak_x, normalized_curve_lin, '.b', markersize=5, 
                       label='Normalized data')
            ax_fit.plot(peak_x, yfit, 'r-', linewidth=2, label='Lorentz fit')
            
            # Draw FWHM line at half-maximum (0.5 in normalized [0,1] scale)
            half_max = (np.max(yfit) + np.min(yfit)) / 2
            ax_fit.axhline(half_max, color='gray', linestyle='--', linewidth=1, 
                          label=f'Half-max ({half_max:.2f})')
            
            # Mark FWHM points
            fwhm_indices = np.where(yfit >= half_max)[0]
            if len(fwhm_indices) >= 2:
                fwhm_wl_left = peak_x[fwhm_indices[0]]
                fwhm_wl_right = peak_x[fwhm_indices[-1]]
                ax_fit.plot([fwhm_wl_left, fwhm_wl_right], [half_max, half_max],
                           'mo-', linewidth=3, markersize=8, label=f'FWHM = {gamma*1e3:.1f} pm')
            
            ax_fit.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
            ax_fit.set_ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
            # FIXED: Compact single-line title
            ax_fit.set_title(f'Lorentzian Fit: y = A/((x-x₀)²+γ) + C', fontsize=PLOT_FONT_TITLE)

            # Put fit parameters in text box instead of title
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
                       transform=ax_fit.transAxes, fontsize=PLOT_FONT_TITLE, color='black')
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
        Q, R2, params = update()
        result['accept'] = True
        result['Q'] = Q
        result['R2'] = R2
        result['params'] = params
        
        # Save the current figure before closing
        if save_path is not None:  # Use the parameter directly
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

# Print current date and time for logging
print("Script run at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Initialize the Tkinter root window
root = Tk()
root.withdraw()  # Hide the root window but keep it active for dialogs

# Prompt user to select the OSA folder
osaFolder = filedialog.askdirectory(
    title="Select the folder containing OSA .mat files",
    initialdir=r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\OSA"
)
if not osaFolder:
    raise FileNotFoundError("No OSA folder selected.")

# Prompt user to select the LIV folder
livFolder = filedialog.askdirectory(
    title="Select the folder containing LIV .mat files",
    initialdir=r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\LIV"
)
if not livFolder:
    raise FileNotFoundError("No LIV folder selected.")

# Prompt user to select the Benchtop .mat file
benchtopFile = filedialog.askopenfilename(
    title="Select the Benchtop .mat file",
    filetypes=[("MAT files", "*.mat")],
    initialdir=r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\Benchtop"
)
if not benchtopFile:
    raise FileNotFoundError("No Benchtop .mat file selected.")

# Process OSA files
osaFiles = [f for f in os.listdir(osaFolder) if f.endswith('.mat')]
if not osaFiles:
    raise FileNotFoundError("No .mat files found in the selected OSA folder.")

osaData = scipy.io.loadmat(os.path.join(osaFolder, osaFiles[0]))  # Load the first file
if 'polyfit_peakWL_vs_I_deg2_coeffs' not in osaData:
    raise KeyError("FitParams not found in the selected OSA file.")

# Process LIV files
livFiles = [f for f in os.listdir(livFolder) if f.endswith('.mat')]
if not livFiles:
    raise FileNotFoundError("No .mat files found in the selected LIV folder.")
## comment the following if you are using the eval_system data
# Load the first LIV file
# livData = scipy.io.loadmat(os.path.join(livFolder, livFiles[0]))  # Load the first file
# if 'current' not in livData or 'channel_3' not in livData:
#     raise KeyError("'current' or 'channel3' data not found in the selected LIV file.")

# current = np.array(livData['current']).flatten()  # Current data
# channel3 = np.array(livData['channel_3']).flatten()  # Power data

# Load the eval_system data
livData = scipy.io.loadmat(os.path.join(livFolder, livFiles[0]))  # Load the first file
if 'current' not in livData or 'channel_3' not in livData:
     raise KeyError("'current' or 'channel_3' data not found in the selected LIV file.")

current = np.array(livData['current']).flatten()  # Current data

channel3 = np.array(livData['channel_3']).flatten()  # Power data

# Store full range on-chip data before filtering
current_fullRange = current.copy()
powerOnChip_fullRange = channel3.copy()

# Detect units and filter current data between 20 mA and 50 mA
# First, try filtering assuming units are in mA (20-50 mA)
validIdx = (current >= 20) & (current <= 50)
currentFiltered = current[validIdx]
powerFiltered = channel3[validIdx]
current_units = "mA"  # Track which units we're using

# If no data found, try assuming units are in A (0.02-0.05 A)
if len(currentFiltered) == 0:
    print("No data found in mA range (20-50 mA), trying A range (0.02-0.05 A)...")
    validIdx = (current >= 0.02) & (current <= 0.05)
    currentFiltered = current[validIdx]
    powerFiltered = channel3[validIdx]
    current_units = "A"

# Convert power from dBm to mW if current is in A (indicates OSA data in dBm)
if current_units == "A":
    print("Current in A detected - converting power from dBm to linear mW scale...")
    print(f"Power before conversion (dBm): min={np.min(powerFiltered):.2f}, max={np.max(powerFiltered):.2f}")
    powerFiltered = 10 ** (powerFiltered / 10)  # dBm to mW conversion: mW = 10^(dBm/10)
    print(f"Power after conversion (mW): min={np.min(powerFiltered):.6f}, max={np.max(powerFiltered):.6f}")

# Debugging: Print the filtered data
print(f"Current array min/max: {np.min(current):.6f} / {np.max(current):.6f}")
print(f"Detected units: {current_units}")
print(f"Valid indices count: {np.sum(validIdx)}")
print(f"Filtered current values: {currentFiltered}")

# Ensure currentFiltered is not empty
if len(currentFiltered) == 0:
    raise ValueError(f"No valid current values found in either range.\n"
                     f"  Tried mA range: 20-50 mA\n"
                     f"  Tried A range: 0.02-0.05 A\n"
                     f"  Current data range: {np.min(current):.6f} to {np.max(current):.6f}\n"
                     f"  Please check the data or adjust the range.")

# Convert current to mA for polynomial calculation (polynomials are typically calibrated in mA)
if current_units == "A":
    print("Converting current from A to mA for wavelength calculation...")
    currentFiltered_mA = currentFiltered * 1000  # Convert A to mA
else:
    currentFiltered_mA = currentFiltered  # Already in mA

print(f"Current for polynomial (mA): {currentFiltered_mA}")

# Calculate wavelength using the polynomial coefficients (expecting current in mA)
polyfit_peakWL_vs_I_deg2_coeffs = osaData['polyfit_peakWL_vs_I_deg2_coeffs'].flatten()
wavelengthOnChip = (
    polyfit_peakWL_vs_I_deg2_coeffs[0] * currentFiltered_mA**2 +
    polyfit_peakWL_vs_I_deg2_coeffs[1] * currentFiltered_mA +
    polyfit_peakWL_vs_I_deg2_coeffs[2]
)

# Calculate full range wavelength for on-chip data
current_fullRange_mA = current_fullRange * 1000 if current_units == "A" else current_fullRange
wavelengthOnChip_fullRange = (
    polyfit_peakWL_vs_I_deg2_coeffs[0] * current_fullRange_mA**2 +
    polyfit_peakWL_vs_I_deg2_coeffs[1] * current_fullRange_mA +
    polyfit_peakWL_vs_I_deg2_coeffs[2]
)

# Convert full range power from dBm to mW if needed
if current_units == "A":
    powerOnChip_fullRange = 10 ** (powerOnChip_fullRange / 10)

# Ensure wavelengthOnChip is not empty
if len(wavelengthOnChip) == 0:
    raise ValueError("No valid wavelengths calculated for the on-chip data.")

# Process Benchtop file
benchtopData = scipy.io.loadmat(benchtopFile)  # Load the selected file
if 'wavelength' not in benchtopData or 'channel_4_mW' not in benchtopData:
    raise KeyError("'wavelength' or 'channel_4_mW' data not found in the selected Benchtop file.")

wavelengthBenchtop = np.array(benchtopData['wavelength']).flatten()
powerBenchtop = np.array(benchtopData['channel_4_mW']).flatten()

# Limit Benchtop data to the nearest 0.1 nm range of the on-chip wavelength
minWavelength = np.floor(min(wavelengthOnChip) * 10) / 10  # Round down to nearest 0.1 nm
maxWavelength = np.ceil(max(wavelengthOnChip) * 10) / 10   # Round up to nearest 0.1 nm

benchtopIdx = (wavelengthBenchtop >= minWavelength) & (wavelengthBenchtop <= maxWavelength)
wavelengthBenchtopLimited = wavelengthBenchtop[benchtopIdx]
powerBenchtopLimited = powerBenchtop[benchtopIdx]

# Ensure Benchtop data is valid
if len(wavelengthBenchtopLimited) == 0 or len(powerBenchtopLimited) == 0:
    raise ValueError("No Benchtop data found within the specified wavelength range.")

# Normalize the power values
powerBenchtopNormalized = powerBenchtopLimited / np.max(powerBenchtopLimited)
powerFilteredNormalized = powerFiltered / np.max(powerFiltered)

# Find peaks for Benchtop data
benchtopPeaks, _ = find_peaks(powerBenchtopNormalized, height=0.4)
benchtopPeakWavelengths = wavelengthBenchtopLimited[benchtopPeaks]  # Extract peak wavelengths
benchtopPeakWavelengths = np.sort(benchtopPeakWavelengths)  # Ensure sorted order
benchtopPeakDistances = np.diff(benchtopPeakWavelengths) * 1e3  # Convert to picometers (pm)

# Find peaks for On-Chip data
onChipPeaks, _ = find_peaks(powerFilteredNormalized,  height=0.2)
onChipPeakWavelengths = wavelengthOnChip[onChipPeaks]  # Extract peak wavelengths
onChipPeakWavelengths = np.sort(onChipPeakWavelengths)  # Ensure sorted order
onChipPeakDistances = np.diff(onChipPeakWavelengths) * 1e3  # Convert to picometers (pm)

# Calculate appropriate window sizes based on data density
benchtop_wavelength_spacing = np.median(np.diff(wavelengthBenchtopLimited))
onchip_wavelength_spacing = np.median(np.diff(wavelengthOnChip))

# Target window of ~0.02 nm on each side of peak
benchtop_window = max(20, int(0.04 / benchtop_wavelength_spacing))
onchip_window = max(20, int(0.04 / onchip_wavelength_spacing))

print(f"\nData spacing info:")
print(f"  Benchtop: {benchtop_wavelength_spacing*1e3:.4f} pm spacing → window = {benchtop_window} points")
print(f"  On-Chip:  {onchip_wavelength_spacing*1e3:.4f} pm spacing → window = {onchip_window} points")

# Save plot data to a .mat file
comparisonFolder = r"C:\Users\jsheri1\Desktop\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\Month7"
if not os.path.exists(comparisonFolder):
    os.makedirs(comparisonFolder)

benchtopFileName = os.path.basename(benchtopFile)
comparisonFileName = f"Comparison2_{benchtopFileName}"
outputFile = os.path.join(comparisonFolder, comparisonFileName)

scipy.io.savemat(outputFile, {
    'wavelengthBenchtopLimited': wavelengthBenchtopLimited,
    'powerBenchtopLimited': powerBenchtopLimited,
    'powerBenchtopNormalized': powerBenchtopNormalized,
    'benchtopPeakWavelengths': benchtopPeakWavelengths,
    'benchtopPeakDistances': benchtopPeakDistances,
    'wavelengthOnChip': wavelengthOnChip,
    'powerFiltered': powerFiltered,
    'powerFilteredNormalized': powerFilteredNormalized,
    'onChipPeakWavelengths': onChipPeakWavelengths,
    'onChipPeakDistances': onChipPeakDistances,
    'wavelengthBenchtop_fullRange': wavelengthBenchtop,
    'powerBenchtop_fullRange': powerBenchtop,
    'wavelengthOnChip_fullRange': wavelengthOnChip_fullRange,
    'powerOnChip_fullRange': powerOnChip_fullRange,
    'current_fullRange': current_fullRange
})
print(f"Plot data saved to {outputFile}")

# Plotting
plt.figure(figsize=(12, 8))
plt.tick_params(axis='both', which='major', labelsize=16)  # Set axis tick label font size
plt.plot(wavelengthBenchtopLimited, powerBenchtopNormalized, color='black', linestyle='--', linewidth=1.5, label='Benchtop Laser')
plt.plot(wavelengthOnChip, powerFilteredNormalized, color='purple', linestyle='-', linewidth=1.5, label='On-Chip Laser')

# Annotate Benchtop peak distances
for i in range(len(benchtopPeakDistances)):
    x = (benchtopPeakWavelengths[i] + benchtopPeakWavelengths[i + 1]) / 2
    y = max(powerBenchtopNormalized) * (0.9 if i % 2 == 0 else 0.85)  # Alternate y position
    y_offset = 0.05 * (i % 2)  # Add a small vertical offset to alternate positions
    plt.annotate(f"{benchtopPeakDistances[i]:.1f} pm", (x, y + y_offset), fontsize=PLOT_FONT_TEXT, color='black', ha='center')

# Annotate On-Chip peak distances
for i in range(len(onChipPeakDistances)):
    x = (onChipPeakWavelengths[i] + onChipPeakWavelengths[i + 1]) / 2
    y = max(powerFilteredNormalized) * (0.5 if i % 2 == 0 else 0.75)  # Alternate y position
    y_offset = 0.05 * (i % 2)  # Add a small vertical offset to alternate positions
    plt.annotate(f"{onChipPeakDistances[i]:.1f} pm", (x, y + y_offset), fontsize=PLOT_FONT_TEXT, color='purple', ha='center')

plt.xlim([minWavelength, maxWavelength])  # Set x-axis limits to match the adjusted wavelength range
plt.xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
plt.ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
plt.legend(loc='upper right', fontsize=PLOT_FONT_LEGEND)  # Place the legend in the top-right corner

# Remove "_data" and ".mat" from the benchtop file name for the title
benchtopFileNameCleaned = os.path.splitext(benchtopFileName.replace("_data", ""))[0]

# Set the plot title with the cleaned file name
plt.title(f'Wavelength vs Normalized Power ({benchtopFileNameCleaned})', fontsize=PLOT_FONT_TITLE)

plt.grid(True)

# Save the figure as a PNG file
figureFileName = os.path.splitext(comparisonFileName)[0] + ".png"
figureFilePath = os.path.join(comparisonFolder, figureFileName)
plt.savefig(figureFilePath, format='png', dpi=300)
print(f"Figure saved to {figureFilePath}")

# Show the plot
plt.show()

# Prompt user for Q factor analysis
do_q_analysis = messagebox.askyesno("Q Factor Analysis", 
    "Do you want to perform quality factor (Q) analysis using Lorentzian fits?")

if do_q_analysis:
    print("\n=== Performing Q Factor Analysis ===")
    
    # Ask for analysis mode
    use_interactive = messagebox.askyesno("Analysis Mode",
        "Use interactive peak selection?\n\nYes = Click to select peaks\nNo = Use auto-detected peaks")
    
    # --- Analyze Benchtop Data ---
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
        # Use auto-detected peaks - already calculated above
        print(f"Using {len(benchtopPeaks)} auto-detected peaks")
    
    benchtop_Q_factors = []
    benchtop_FWHMs = []
    benchtop_results = []
    
    # Fit each peak with adjustable baseline
    for i, peak_idx in enumerate(benchtopPeaks):
        print(f"\nAnalyzing Benchtop Peak {i+1}/{len(benchtopPeaks)} at λ={wavelengthBenchtopLimited[peak_idx]:.4f} nm")
        print("Adjust baseline using sliders, then click Accept or Skip")
        
        # Set save path BEFORE calling the function
        peak_wavelength = wavelengthBenchtopLimited[peak_idx]
        save_filename = f"Benchtop_Peak{i+1}_lambda{peak_wavelength:.4f}nm_Baseline.png"
        save_path = os.path.join(comparisonFolder, save_filename)
        
        result = analyze_peak_with_adjustable_baseline(
            wavelengthBenchtopLimited,
            powerBenchtopNormalized,
            peak_idx,
            initial_window=benchtop_window,
            save_path=save_path  # Pass it as parameter
        )
        
        if result['accept'] and result['params'] is not None:
            benchtop_Q_factors.append(result['Q'])
            params = result['params']
            gamma = np.sqrt(params[2]) * 2
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
    
    # --- Analyze On-Chip Data ---
    print("\n--- On-Chip Laser ---")
    
    if use_interactive:
        print("Please select peaks to analyze (close window when done)...")
        onChipPeaks = interactive_peak_selection(
            wavelengthOnChip,
            powerFilteredNormalized,
            title='On-Chip Laser - Select Peaks'
        )
        print(f"Selected {len(onChipPeaks)} peaks for analysis")
    else:
        # Use auto-detected peaks - already calculated above
        print(f"Using {len(onChipPeaks)} auto-detected peaks")
    
    onchip_Q_factors = []
    onchip_FWHMs = []
    onchip_results = []
    
    # Fit each peak with adjustable baseline
    for i, peak_idx in enumerate(onChipPeaks):
        print(f"\nAnalyzing On-Chip Peak {i+1}/{len(onChipPeaks)} at λ={wavelengthOnChip[peak_idx]:.4f} nm")
        print("Adjust baseline using sliders, then click Accept or Skip")
        
        # Set save path BEFORE calling the function
        peak_wavelength = wavelengthOnChip[peak_idx]
        save_filename = f"OnChip_Peak{i+1}_lambda{peak_wavelength:.4f}nm_Baseline.png"
        save_path = os.path.join(comparisonFolder, save_filename)
        
        result = analyze_peak_with_adjustable_baseline(
            wavelengthOnChip,
            powerFilteredNormalized,
            peak_idx,
            initial_window=onchip_window,
            save_path=save_path  # Pass it as parameter
        )
        
        if result['accept'] and result['params'] is not None:
            onchip_Q_factors.append(result['Q'])
            params = result['params']
            gamma = np.sqrt(params[2]) * 2
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
    
    # --- Create summary overlay plots ---
    if len(benchtop_results) > 0:
        fig_bench, (ax_bench, ax_bench_res) = plt.subplots(2, 1, figsize=(12, 8),
                                                            gridspec_kw={'height_ratios': [3, 1]})
        ax_bench.plot(wavelengthBenchtopLimited, powerBenchtopNormalized,
                     '-k', markersize=3, label='Benchtop Data')
        
        # Calculate FSR between consecutive analyzed peaks
        benchtop_analyzed_wavelengths = [r['wavelength'] for r in benchtop_results]
        benchtop_analyzed_FSRs = np.diff(benchtop_analyzed_wavelengths) * 1e3  # Convert to pm
        
        for res in benchtop_results:
            peak_idx = res['peak_idx']
            ax_bench.plot([res['wavelength']], [powerBenchtopNormalized[peak_idx]], 
                         'r^', markersize=10)
            # Place text BELOW the peak to keep inside plot
            ax_bench.text(res['wavelength'], powerBenchtopNormalized[peak_idx]*0.92,
                        f"Q={res['Q']:.0f}\nFWHM={res['FWHM']*1e3:.1f}pm", 
                        fontsize=10, ha='center', color='magenta', va='top',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none'))
        
        # Annotate FSR between consecutive peaks
        for i in range(len(benchtop_analyzed_FSRs)):
            x_mid = (benchtop_analyzed_wavelengths[i] + benchtop_analyzed_wavelengths[i+1]) / 2
            y_pos = max(powerBenchtopNormalized) * 0.4  # Lower position to avoid clipping
            ax_bench.annotate('', xy=(benchtop_analyzed_wavelengths[i+1], y_pos), 
                           xytext=(benchtop_analyzed_wavelengths[i], y_pos),
                           arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
            ax_bench.text(x_mid, y_pos*0.95, f"FSR={benchtop_analyzed_FSRs[i]:.1f}pm",
                        fontsize=10, ha='center', color='magenta', va='top',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none'))
        
        ax_bench.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
        ax_bench.set_ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
        if len(benchtop_analyzed_FSRs) > 0:
            ax_bench.set_title(f'Benchtop - Q Analysis Summary\n' +
                              f'Avg Q = {np.mean(benchtop_Q_factors):.0f} ± {np.std(benchtop_Q_factors):.0f}, ' +
                              f'Avg FSR = {np.mean(benchtop_analyzed_FSRs):.1f} ± {np.std(benchtop_analyzed_FSRs):.1f} pm',
                              fontsize=14)
        else:
            ax_bench.set_title(f'Benchtop - Q Analysis Summary\n' +
                              f'Avg Q = {np.mean(benchtop_Q_factors):.0f} ± {np.std(benchtop_Q_factors):.0f}',
                              fontsize=14)
        ax_bench.set_ylim([0, 1.05])  # Add margin at top
        ax_bench.legend()
        ax_bench.grid(True)
        
        ax_bench_res.set_xlabel('Wavelength (nm)')
        ax_bench_res.set_ylabel('Q Factor')
        ax_bench_res.bar([r['wavelength'] for r in benchtop_results],
                        benchtop_Q_factors, width=0.01, color='black', alpha=0.6)
        ax_bench_res.grid(True)
        
        plt.tight_layout()
        bench_q_filename = os.path.splitext(comparisonFileName)[0] + "_Benchtop_Q.png"
        plt.savefig(os.path.join(comparisonFolder, bench_q_filename), dpi=300)
        plt.show()
    
    if len(onchip_results) > 0:
        fig_chip, (ax_chip, ax_chip_res) = plt.subplots(2, 1, figsize=(12, 8),
                                                         gridspec_kw={'height_ratios': [3, 1]})
        ax_chip.plot(wavelengthOnChip, powerFilteredNormalized,
                    '-k', markersize=3, label='On-Chip Data')
        
        # Calculate FSR between consecutive analyzed peaks
        onchip_analyzed_wavelengths = [r['wavelength'] for r in onchip_results]
        onchip_analyzed_FSRs = np.diff(onchip_analyzed_wavelengths) * 1e3  # Convert to pm
        
        for res in onchip_results:
            peak_idx = res['peak_idx']
            ax_chip.plot([res['wavelength']], [powerFilteredNormalized[peak_idx]],
                        'm^', markersize=10)
            # Place text BELOW the peak to keep inside plot
            ax_chip.text(res['wavelength'], powerFilteredNormalized[peak_idx]*0.92,
                       f"Q={res['Q']:.0f}\nFWHM={res['FWHM']*1e3:.1f}pm", 
                       fontsize=10, ha='center', color='purple', va='top',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none'))
        
        # Annotate FSR between consecutive peaks
        for i in range(len(onchip_analyzed_FSRs)):
            x_mid = (onchip_analyzed_wavelengths[i] + onchip_analyzed_wavelengths[i+1]) / 2
            y_pos = max(powerFilteredNormalized) * 0.4  # Lower position to avoid clipping
            ax_chip.annotate('', xy=(onchip_analyzed_wavelengths[i+1], y_pos), 
                          xytext=(onchip_analyzed_wavelengths[i], y_pos),
                          arrowprops=dict(arrowstyle='<->', color='purple', lw=2))
            ax_chip.text(x_mid, y_pos*0.95, f"FSR={onchip_analyzed_FSRs[i]:.1f}pm",
                       fontsize=10, ha='center', color='blue', va='top',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='purple'))

        ax_chip.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
        ax_chip.set_ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
        if len(onchip_analyzed_FSRs) > 0:
            ax_chip.set_title(f'On-Chip - Q Analysis Summary\n' +
                             f'Avg Q = {np.mean(onchip_Q_factors):.0f} ± {np.std(onchip_Q_factors):.0f}, ' +
                             f'Avg FSR = {np.mean(onchip_analyzed_FSRs):.1f} ± {np.std(onchip_analyzed_FSRs):.1f} pm',
                             fontsize=14)
        else:
            ax_chip.set_title(f'On-Chip - Q Analysis Summary\n' +
                             f'Avg Q = {np.mean(onchip_Q_factors):.0f} ± {np.std(onchip_Q_factors):.0f}',
                             fontsize=14)
        ax_chip.set_ylim([0, 1.05])  # Add margin at top
        ax_chip.legend()
        ax_chip.grid(True)
        
        ax_chip_res.set_xlabel('Wavelength (nm)')
        ax_chip_res.set_ylabel('Q Factor')
        ax_chip_res.bar([r['wavelength'] for r in onchip_results],
                       onchip_Q_factors, width=0.01, color='purple', alpha=0.6)
        ax_chip_res.grid(True)
        
        plt.tight_layout()
        chip_q_filename = os.path.splitext(comparisonFileName)[0] + "_OnChip_Q.png"
        plt.savefig(os.path.join(comparisonFolder, chip_q_filename), dpi=300)
        plt.show()
    else:
        print("No on-chip results to plot")
    
    # --- Summary Statistics ---
    print("\n=== Summary ===")
    if len(benchtop_Q_factors) > 0:
        print(f"Benchtop: Avg Q = {np.mean(benchtop_Q_factors):.0f} ± {np.std(benchtop_Q_factors):.0f}")
        print(f"          Avg FWHM = {np.mean(benchtop_FWHMs)*1e3:.2f} ± {np.std(benchtop_FWHMs)*1e3:.2f} pm")
        if len(benchtop_analyzed_FSRs) > 0:
            print(f"          Avg FSR = {np.mean(benchtop_analyzed_FSRs):.2f} ± {np.std(benchtop_analyzed_FSRs):.2f} pm")
            finesse_bench = np.mean(benchtop_analyzed_FSRs) / (np.mean(benchtop_FWHMs)*1e3)
            print(f"          Finesse = {finesse_bench:.1f} (FSR/FWHM)")
        else:
            print(f"          No FSR data (only 1 peak analyzed)")
    
    if len(onchip_Q_factors) > 0:
        print(f"\nOn-Chip:  Avg Q = {np.mean(onchip_Q_factors):.0f} ± {np.std(onchip_Q_factors):.0f}")
        print(f"          Avg FWHM = {np.mean(onchip_FWHMs)*1e3:.2f} ± {np.std(onchip_FWHMs)*1e3:.2f} pm")
        if len(onchip_analyzed_FSRs) > 0:
            print(f"          Avg FSR = {np.mean(onchip_analyzed_FSRs):.2f} ± {np.std(onchip_analyzed_FSRs):.2f} pm")
            finesse_chip = np.mean(onchip_analyzed_FSRs) / (np.mean(onchip_FWHMs)*1e3)
            print(f"          Finesse = {finesse_chip:.1f} (FSR/FWHM)")
        else:
            print(f"          No FSR data (only 1 peak analyzed)")
    
    # Save results
    scipy.io.savemat(outputFile, {
        'wavelengthBenchtopLimited': wavelengthBenchtopLimited,
        'powerBenchtopLimited': powerBenchtopLimited,
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
        'wavelengthOnChip': wavelengthOnChip,
        'powerFiltered': powerFiltered,
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
        'wavelengthBenchtop_fullRange': wavelengthBenchtop,
        'powerBenchtop_fullRange': powerBenchtop,
        'wavelengthOnChip_fullRange': wavelengthOnChip_fullRange,
        'powerOnChip_fullRange': powerOnChip_fullRange,
        'current_fullRange': current_fullRange,
        'onchip_avg_FWHM': np.mean(onchip_FWHMs) if len(onchip_FWHMs) > 0 else np.nan,
        'onchip_std_FWHM': np.std(onchip_FWHMs) if len(onchip_FWHMs) > 0 else np.nan,
        'onchip_avg_FSR': np.mean(onchip_analyzed_FSRs) if len(onchip_results) > 1 else np.nan,
        'onchip_std_FSR': np.std(onchip_analyzed_FSRs) if len(onchip_results) > 1 else np.nan,
        'onchip_finesse': (np.mean(onchip_analyzed_FSRs) / (np.mean(onchip_FWHMs)*1e3)) if len(onchip_results) > 1 else np.nan
    })
    print(f"\nUpdated data saved to {outputFile}")
    # =============================================================================
    # CREATE ZOOMED OVERLAY PLOT - ANALYZED PEAKS ONLY
    # =============================================================================
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
            wl_margin = (wl_max - wl_min) * 0.15  # 15% margin on each side
            zoom_wl_min = wl_min - wl_margin
            zoom_wl_max = wl_max + wl_margin
            
            # Filter data to zoomed range
            benchtop_zoom_idx = (wavelengthBenchtopLimited >= zoom_wl_min) & (wavelengthBenchtopLimited <= zoom_wl_max)
            onchip_zoom_idx = (wavelengthOnChip >= zoom_wl_min) & (wavelengthOnChip <= zoom_wl_max)
            
            benchtop_zoom_wl = wavelengthBenchtopLimited[benchtop_zoom_idx]
            benchtop_zoom_power = powerBenchtopNormalized[benchtop_zoom_idx]
            onchip_zoom_wl = wavelengthOnChip[onchip_zoom_idx]
            onchip_zoom_power = powerFilteredNormalized[onchip_zoom_idx]
            
            # Create figure
            fig_zoom = plt.figure(figsize=(14, 9))
            plt.tick_params(axis='both', which='major', labelsize=14)
            
            # Plot data
            plt.plot(benchtop_zoom_wl, benchtop_zoom_power, color='black', linestyle='--', 
                    linewidth=2, label='Benchtop Laser', alpha=0.8)
            plt.plot(onchip_zoom_wl, onchip_zoom_power, color='purple', linestyle='-', 
                    linewidth=2, label='On-Chip Laser', alpha=0.8)
            
            # Fixed annotation positions to avoid overlap
            benchtop_q_y = 0.88      # Benchtop Q labels
            benchtop_fsr_y = 0.76    # Benchtop FSR arrows
            onchip_q_y = 0.60        # On-chip Q labels  
            onchip_fsr_y = 0.48      # On-chip FSR arrows
            
            # Plot benchtop analyzed peaks with Q annotations
            if len(benchtop_results) > 0:
                for i, res in enumerate(benchtop_results):
                    wl = res['wavelength']
                    # Find nearest point for peak marker
                    nearest_idx = np.argmin(np.abs(wavelengthBenchtopLimited - wl))
                    y_val = powerBenchtopNormalized[nearest_idx]
                    
                    # Vertical line from peak to Q label
                    plt.plot([wl, wl], [y_val, benchtop_q_y], 'r:', linewidth=1.5, alpha=0.6, zorder=1)
                    
                    # Peak marker
                    plt.plot([wl], [y_val], 'r^', markersize=10, zorder=5, 
                            markeredgecolor='darkred', markeredgewidth=1)
                    
                    # Q label at FIXED height
                    plt.text(wl, benchtop_q_y + 0.02,
                            f"Q={res['Q']:.0f}\n{res['FWHM']*1e3:.1f}pm",
                            fontsize=12, ha='center', color='black', va='bottom',
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
                                fontsize=12, ha='center', color='black', va='top',
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                        alpha=0.9, edgecolor='black'))
            
            # Plot on-chip analyzed peaks with Q annotations
            if len(onchip_results) > 0:
                for i, res in enumerate(onchip_results):
                    wl = res['wavelength']
                    # Find nearest point for peak marker
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
                            fontsize=12, ha='center', color='purple', va='bottom',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                    alpha=0.9, edgecolor='purple', linewidth=1.5))
                
                # On-chip FSR arrows at fixed position
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
                                fontsize=12, ha='center', color='purple', va='top',
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                        alpha=0.9, edgecolor='purple'))
            
            # Configure plot
            plt.xlim([zoom_wl_min, zoom_wl_max])
            plt.ylim([0, 1.05])
            plt.xlabel('Wavelength (nm)', fontsize=16)
            plt.ylabel('Normalized Power', fontsize=16)
            plt.legend(loc='upper right', fontsize=14)
            
            # Title with summary statistics
            title_lines = [f'Q-Factor Analysis - Analyzed Peaks Only ({benchtopFileNameCleaned})']
            
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
            
            plt.title('\n'.join(title_lines), fontsize=13, pad=20)
            plt.grid(True, alpha=0.3, linestyle='--')
            plt.tight_layout()
            
            # Save figure
            zoom_filename = os.path.splitext(comparisonFileName)[0] + "_Q_Analysis_Zoomed.png"
            zoom_filepath = os.path.join(comparisonFolder, zoom_filename)
            plt.savefig(zoom_filepath, format='png', dpi=300, bbox_inches='tight')
            print(f"✓ Zoomed Q-analysis plot saved to: {zoom_filepath}")
            plt.show()

