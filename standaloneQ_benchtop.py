# author: sheri and co-pilot
# date: 2025-10-27
# Description: Standalone script for Q-factor analysis of benchtop laser data.
# Prompts user to select a benchtop .mat file and performs Lorentzian fitting
# with interactive baseline adjustment for peaks around 1310 nm.

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

def analyze_peak_with_adjustable_baseline(x, y, peak_idx, initial_window=15, save_path=None, fit_dips=False):
    """
    Interactive baseline adjustment for a single peak or dip.
    Use sliders to adjust baseline window and polynomial order.
    
    Parameters:
    -----------
    x : array
        Wavelength data
    y : array
        Power data
    peak_idx : int
        Index of peak/dip to analyze
    initial_window : int
        Initial window size for peak region
    save_path : str, optional
        Path to save the figure when accepted
    fit_dips : bool, optional
        If True, fit inverted Lorentzian (dips). If False, fit normal Lorentzian (peaks)
    """
    # Store original peak index and data
    original_peak_idx = peak_idx
    
    fig, ((ax_main, ax_baseline), (ax_fit, ax_residual)) = plt.subplots(
        2, 2, figsize=(14, 10), 
        gridspec_kw={'height_ratios': [2, 1], 'width_ratios': [1, 1]}
    )
    plt.subplots_adjust(bottom=0.28, hspace=0.3)
    
    def calculate_baseline(left_win, right_win, order, peak_win):
        # Recalculate peak region based on peak_win slider
        left_idx = max(0, original_peak_idx - peak_win)
        right_idx = min(len(x), original_peak_idx + peak_win + 1)
        peak_x = x[left_idx:right_idx]
        peak_y = y[left_idx:right_idx]
        # Calculate baseline using points OUTSIDE the peak window
        baseline_left_start = max(0, left_idx - left_win)
        baseline_left_end = left_idx
        baseline_right_start = right_idx
        baseline_right_end = min(len(x), right_idx + right_win)
        
        # Get baseline points from OUTSIDE the peak region
        baseline_x_left = np.array([])
        baseline_y_left = np.array([])
        baseline_x_right = np.array([])
        baseline_y_right = np.array([])
        
        if baseline_left_end > baseline_left_start and (baseline_left_end - baseline_left_start) > 3:
            baseline_x_left = x[baseline_left_start:baseline_left_end]
            baseline_y_left = y[baseline_left_start:baseline_left_end]
            
            # For dips: select points near local maxima (baseline is at top)
            # For peaks: select points near local minima (baseline is at bottom)
            if fit_dips:
                # Take top 50% of points (more permissive to get more baseline points)
                threshold = np.percentile(baseline_y_left, 50)
                mask = baseline_y_left >= threshold
                baseline_x_left = baseline_x_left[mask]
                baseline_y_left = baseline_y_left[mask]
            else:
                # Take bottom 50% of points
                threshold = np.percentile(baseline_y_left, 50)
                mask = baseline_y_left <= threshold
                baseline_x_left = baseline_x_left[mask]
                baseline_y_left = baseline_y_left[mask]
        
        if baseline_right_end > baseline_right_start and (baseline_right_end - baseline_right_start) > 3:
            baseline_x_right = x[baseline_right_start:baseline_right_end]
            baseline_y_right = y[baseline_right_start:baseline_right_end]
            
            # Same filtering for right side
            if fit_dips:
                threshold = np.percentile(baseline_y_right, 50)
                mask = baseline_y_right >= threshold
                baseline_x_right = baseline_x_right[mask]
                baseline_y_right = baseline_y_right[mask]
            else:
                threshold = np.percentile(baseline_y_right, 50)
                mask = baseline_y_right <= threshold
                baseline_x_right = baseline_x_right[mask]
                baseline_y_right = baseline_y_right[mask]
        
        # Combine left and right baseline points
        baseline_x = np.concatenate([baseline_x_left, baseline_x_right])
        baseline_y = np.concatenate([baseline_y_left, baseline_y_right])
        
        # Fit baseline
        if len(baseline_x) >= max(3, order + 1):
            # Use robust polynomial fitting with weighted least squares
            # Weight points more heavily if they're closer to desired baseline
            if fit_dips:
                # For dips, weight higher values more
                weights = baseline_y / np.max(baseline_y)
            else:
                # For peaks, weight lower values more
                weights = (np.max(baseline_y) - baseline_y) / (np.max(baseline_y) - np.min(baseline_y) + 1e-10)
            
            p = np.polyfit(baseline_x, baseline_y, order, w=weights)
            baseline_peak = np.polyval(p, peak_x)
            baseline_full = np.polyval(p, x)
        else:
            print(f"Warning: Not enough baseline points ({len(baseline_x)}), using endpoints fallback")
            # Use the endpoints of the peak region as baseline estimate
            baseline_peak = np.linspace(peak_y[0], peak_y[-1], len(peak_x))
            baseline_full = np.interp(x, [peak_x[0], peak_x[-1]], [peak_y[0], peak_y[-1]])
            baseline_x = peak_x[[0, -1]]
            baseline_y = peak_y[[0, -1]]
        
        return baseline_peak, baseline_full, baseline_x, baseline_y, peak_x, peak_y, left_idx, right_idx
    
    def update(val=None):
        left_win = int(slider_left.val)
        right_win = int(slider_right.val)
        order = int(slider_order.val)
        peak_win = int(slider_peak.val)
        
        baseline_peak, baseline_full, baseline_x_pts, baseline_y_pts, peak_x, peak_y, left_idx, right_idx = calculate_baseline(
            left_win, right_win, order, peak_win
        )
        
        # Baseline-corrected data (subtract baseline from peak region)
        normalized_curve = peak_y - baseline_peak
        
        # Detect if we have a peak (max) or dip (min) after baseline correction
        abs_max = np.max(np.abs(normalized_curve))
        is_dip = (np.min(normalized_curve) < -abs_max/2) if not fit_dips else True
        
        # For dips: normalize to [-1, 0], For peaks: normalize to [0, 1]
        if is_dip:
            # Dip: normalize so dip goes to -1, baseline to 0
            ymax = np.max(normalized_curve)
            ymin = np.min(normalized_curve)
            if (ymax - ymin) > 0:
                normalized_curve_lin = (normalized_curve - ymax) / (ymax - ymin)
            else:
                normalized_curve_lin = normalized_curve
        else:
            # Peak: normalize so peak goes to 1, baseline to 0
            ymin = np.min(normalized_curve)
            ymax = np.max(normalized_curve)
            if (ymax - ymin) > 0:
                normalized_curve_lin = (normalized_curve - ymin) / (ymax - ymin)
            else:
                normalized_curve_lin = normalized_curve
        
        # Perform Lorentzian fit
        try:
            if is_dip:
                # Initial guess for DOWNWARD dip (negative A)
                peak_height = np.min(normalized_curve_lin) - np.max(normalized_curve_lin)  # Negative
                peak_center = peak_x[np.argmin(normalized_curve_lin)]
                peak_width = (peak_x[-1] - peak_x[0]) / 10
                baseline_level = np.max(normalized_curve_lin)  # Top baseline
                
                p0_guess = [
                    peak_height,      # A < 0 for downward dip
                    peak_center,      # x0 (wavelength at dip center)
                    peak_width**2,    # gamma (width parameter, squared)
                    baseline_level    # C (baseline offset at top)
                ]
            else:
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
        
        # Plot 3: Fitted data
        if fit_success:
            ax_fit.plot(peak_x, normalized_curve_lin, '.b', markersize=5, 
                       label='Normalized data')
            ax_fit.plot(peak_x, yfit, 'r-', linewidth=2, label='Lorentz fit')
            
            # Calculate half-maximum (works for both peaks and dips)
            half_max = (np.max(yfit) + np.min(yfit)) / 2
            ax_fit.axhline(half_max, color='gray', linestyle='--', linewidth=1, 
                          label=f'Half-max ({half_max:.2f})')
            
            # Find FWHM points (where fit crosses half-max)
            if is_dip:
                fwhm_indices = np.where(yfit <= half_max)[0]
            else:
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
            ax_residual.set_xlabel('Wavelength (nm)')
            ax_residual.set_ylabel('Residuals')
            ax_residual.set_title('Fit Residuals')
            ax_residual.grid(True)
        else:
            ax_fit.text(0.5, 0.5, 'Fit Failed', ha='center', va='center',
                       transform=ax_fit.transAxes, fontsize=14, color='red')
            ax_residual.text(0.5, 0.5, 'No Residuals', ha='center', va='center',
                           transform=ax_residual.transAxes, fontsize=PLOT_FONT_TITLE)
        
        fig.canvas.draw_idle()
        
        return Q_factor, R_sq, params
    
    # Create sliders
    ax_slider_peak = plt.axes([0.15, 0.16, 0.3, 0.03])
    ax_slider_left = plt.axes([0.15, 0.12, 0.3, 0.03])
    ax_slider_right = plt.axes([0.15, 0.08, 0.3, 0.03])
    ax_slider_order = plt.axes([0.15, 0.04, 0.3, 0.03])
    
    slider_peak = Slider(ax_slider_peak, 'Peak Window', 10, 100, 
                         valinit=initial_window, valstep=1)
    slider_left = Slider(ax_slider_left, 'Left Baseline', 0, 100, 
                         valinit=30, valstep=1)
    slider_right = Slider(ax_slider_right, 'Right Baseline', 0, 100, 
                          valinit=30, valstep=1)
    slider_order = Slider(ax_slider_order, 'Poly Order', 0, 3, 
                          valinit=1, valstep=1)
    
    slider_peak.on_changed(update)
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
                 fontsize=12)
    ax.grid(True)
    ax.legend()
    
    scatter = ax.scatter([], [], c='red', s=100, marker='^', 
                        label='Selected peaks', zorder=5)
    
    def onclick(event):
        if event.inaxes != ax:
            return
        
        if event.button == MouseButton.LEFT:
            distances = np.abs(x - event.xdata)
            idx = np.argmin(distances)
            
            if idx not in selected_peaks:
                selected_peaks.append(idx)
                print(f"Added peak at λ={x[idx]:.4f} nm (index {idx})")
                update_plot()
        
        elif event.button == MouseButton.RIGHT:
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


# ============================================================================
# MAIN SCRIPT
# ============================================================================

print("=== Benchtop Laser Q-Factor Analysis ===")
print("Script run at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Initialize Tkinter
root = Tk()
root.withdraw()

# Prompt user to select Benchtop .mat file
benchtopFile = filedialog.askopenfilename(
    title="Select the Benchtop .mat file",
    filetypes=[("MAT files", "*.mat")],
    initialdir=r"C:\Users\jsheri1\Documents\A_Research\2021-09_Biosensor_ShuksanZep\2026-01-19_Water_Characterization_ANT_Spiral_Paperclip"
)
if not benchtopFile:
    raise FileNotFoundError("No Benchtop .mat file selected.")

# Load Benchtop data
print(f"\nLoading: {os.path.basename(benchtopFile)}")
benchtopData = scipy.io.loadmat(benchtopFile)

# Detect file format
print("\n" + "="*60)
print("Detecting file format...")
print("="*60)

file_format = None

# Format 1: Original format with wavelength + channel_X_mW
if 'wavelength' in benchtopData:
    # Check for channel_X_mW format
    has_channel_mW = any(key.startswith('channel_') and key.endswith('_mW') 
                         for key in benchtopData.keys())
    if has_channel_mW:
        file_format = 'channel_mW'
        print("✓ Detected Format 1: wavelength + channel_X_mW")

# Format 2: Loopback format with Power matrix (rows x columns)
if file_format is None:
    if 'Power' in benchtopData and 'wavelength' in benchtopData:
        file_format = 'power_matrix'
        print("✓ Detected Format 2: Power matrix + wavelength vector")
    elif 'power' in benchtopData and 'wavelength' in benchtopData:
        file_format = 'power_matrix'
        print("✓ Detected Format 2: power matrix + wavelength vector")

if file_format is None:
    raise KeyError("Could not detect file format. Expected:\n" +
                   "  Format 1: 'wavelength' + 'channel_X_mW' variables\n" +
                   "  Format 2: 'Power' (or 'power') matrix + 'wavelength' vector")

wavelength = np.array(benchtopData['wavelength']).flatten()

# Find all available channels based on format
available_channels = []
power_matrix = None

if file_format == 'channel_mW':
    # Format 1: Extract channel_X_mW variables
    for key in benchtopData.keys():
        if key.startswith('channel_') and key.endswith('_mW'):
            available_channels.append(key)
    
    if len(available_channels) == 0:
        raise KeyError("No channel_X_mW data found in the file.")
    
    print(f"\nFound {len(available_channels)} channels: {', '.join(available_channels)}")

elif file_format == 'power_matrix':
    # Format 2: Extract from Power matrix (rows = sweeps, columns = channels)
    power_key = 'Power' if 'Power' in benchtopData else 'power'
    power_matrix = np.array(benchtopData[power_key])
    
    # Check if power matrix needs transposing (wavelength should match one dimension)
    if power_matrix.shape[0] == len(wavelength):
        # Rows are wavelengths, columns are channels
        num_channels = power_matrix.shape[1]
    elif power_matrix.shape[1] == len(wavelength):
        # Columns are wavelengths, rows are channels - transpose
        print("  Transposing Power matrix (rows=channels, cols=wavelength)")
        power_matrix = power_matrix.T
        num_channels = power_matrix.shape[1]
    else:
        raise ValueError(f"Power matrix shape {power_matrix.shape} does not match wavelength length {len(wavelength)}")
    
    # Create channel names
    available_channels = [f"channel_{i}" for i in range(num_channels)]
    print(f"\nFound {num_channels} channels in Power matrix (shape: {power_matrix.shape})")
    print(f"  Wavelength points: {len(wavelength)}")
    print(f"  Channel columns: {num_channels}")

# Plot all channels for user to see
fig, ax = plt.subplots(figsize=(14, 8))
channel_lines = {}

# Use highly distinct colors and vary line styles for better differentiation
num_channels = len(available_channels)

# Define bold, highly saturated colors that stand out
distinct_colors = [
    '#1f77b4',  # Blue
    '#ff7f0e',  # Orange
    '#2ca02c',  # Green
    '#d62728',  # Red
    '#9467bd',  # Purple
    '#8c564b',  # Brown
    '#e377c2',  # Pink
    '#7f7f7f',  # Gray
    '#bcbd22',  # Olive
    '#17becf',  # Cyan
    '#ff1493',  # Deep Pink
    '#00ced1',  # Dark Turquoise
    '#ff4500',  # Orange Red
    '#9370db',  # Medium Purple
    '#32cd32',  # Lime Green
]

# Cycle through line styles for additional differentiation
line_styles = ['-', '--', '-.', ':']

if file_format == 'channel_mW':
    for idx, ch in enumerate(available_channels):
        power_data = np.array(benchtopData[ch]).flatten()
        color = distinct_colors[idx % len(distinct_colors)]
        linestyle = line_styles[idx // len(distinct_colors)]
        line, = ax.plot(wavelength, power_data, linestyle, linewidth=2.5, label=ch, 
                       color=color, alpha=0.85)
        channel_lines[ch] = line
elif file_format == 'power_matrix':
    for i, ch in enumerate(available_channels):
        power_data = power_matrix[:, i]
        display_name = f"Channel {i+1}"  # 1-based numbering for display
        color = distinct_colors[i % len(distinct_colors)]
        linestyle = line_styles[i // len(distinct_colors)]
        line, = ax.plot(wavelength, power_data, linestyle, linewidth=2.5, label=display_name, 
                       color=color, alpha=0.85)
        channel_lines[ch] = line

ax.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
ax.set_ylabel('Power (mW)', fontsize=PLOT_FONT_AXIS_LABEL)
ax.set_title(f'All Channels - Select one to analyze\n{os.path.basename(benchtopFile)}', 
             fontsize=PLOT_FONT_TITLE)
ax.grid(True, alpha=0.3)
ax.legend(fontsize=PLOT_FONT_LEGEND)
plt.tight_layout()
plt.show()

# Ask user to select channel
from tkinter import simpledialog

if file_format == 'channel_mW':
    channel_names = [ch.replace('_mW', '').replace('channel_', 'Channel ') for ch in available_channels]
elif file_format == 'power_matrix':
    channel_names = [f"Channel {i+1}" for i in range(len(available_channels))]  # 1-based numbering

choice_str = "\n".join([f"{i+1}. {name}" for i, name in enumerate(channel_names)])
print(f"\nAvailable channels:\n{choice_str}")

channel_choice = simpledialog.askinteger("Channel Selection", 
    f"Select channel to analyze (1-{len(available_channels)}):\n\n{choice_str}",
    minvalue=1, maxvalue=len(available_channels))

if channel_choice is None:
    print("No channel selected. Exiting.")
    exit()

selected_channel = available_channels[channel_choice - 1]

if file_format == 'channel_mW':
    power = np.array(benchtopData[selected_channel]).flatten()
    print(f"\nSelected: {selected_channel}")
elif file_format == 'power_matrix':
    channel_idx = channel_choice - 1
    power = power_matrix[:, channel_idx].flatten()
    print(f"\nSelected: Channel {channel_choice} from Power matrix")  # Display 1-based number
    
    # Convert units for power_matrix format (m → nm, dBm → mW)
    print("\nConverting units for loopback format:")
    print(f"  Wavelength: {wavelength.min():.6e} - {wavelength.max():.6e} m → ", end="")
    wavelength = wavelength * 1e9  # m to nm (multiply by 1,000,000,000)
    print(f"{wavelength.min():.2f} - {wavelength.max():.2f} nm")
    
    print(f"  Power: {power.min():.2f} - {power.max():.2f} dBm → ", end="")
    power = 10 ** (power / 10)  # dBm to mW: mW = 10^(dBm/10)
    print(f"{power.min():.6f} - {power.max():.6f} mW")

# Ask user if fitting peaks (maxima) or dips (minima)
print("\n" + "="*60)
print("IMPORTANT: Peak Type Selection Dialog")
print("A dialog window is about to appear - check your taskbar!")
print("="*60)

fit_dips = messagebox.askyesno("Peak Type Selection", 
    "Are you analyzing DIPS (transmission minima)?\n\n" +
    "YES = Fit dips/minima (data will be inverted)\n" +
    "NO = Fit peaks/maxima (standard mode)\n\n" +
    "Check the channel plot you just saw to decide.",
    default='no')

if fit_dips:
    print("\n>>> Mode: Fitting DIPS (transmission minima) - native Lorentzian dips <<<")
else:
    print("\n>>> Mode: Fitting PEAKS (maxima) - native Lorentzian peaks <<<")

# Filter data around 1310 nm (±0.5 nm range by default)
center_wavelength = 1310.0
wavelength_range = 0.3  # nm

minWavelength = center_wavelength - wavelength_range
maxWavelength = center_wavelength + wavelength_range

# Ask user if they want to customize the range
customize_range = messagebox.askyesno("Wavelength Range", 
    f"Default range: {minWavelength:.1f} - {maxWavelength:.1f} nm\n\nDo you want to customize?")

if customize_range:
    from tkinter import simpledialog
    center_wavelength = simpledialog.askfloat("Center Wavelength", 
        "Enter center wavelength (nm):", initialvalue=1310.0)
    wavelength_range = simpledialog.askfloat("Range", 
        "Enter ± range (nm):", initialvalue=0.3)
    
    minWavelength = center_wavelength - wavelength_range
    maxWavelength = center_wavelength + wavelength_range

print(f"\nAnalyzing wavelength range: {minWavelength:.2f} - {maxWavelength:.2f} nm")
print(f"Data wavelength range: {wavelength.min():.2f} - {wavelength.max():.2f} nm")
print(f"Data points: {len(wavelength)}")

# Filter data
validIdx = (wavelength >= minWavelength) & (wavelength <= maxWavelength)
wavelength_limited = wavelength[validIdx]
power_limited = power[validIdx]

if len(wavelength_limited) == 0:
    print(f"\nERROR: No data points found in the specified range!")
    print(f"  Requested range: {minWavelength:.2f} - {maxWavelength:.2f} nm")
    print(f"  Available data range: {wavelength.min():.2f} - {wavelength.max():.2f} nm")
    print(f"\nSuggestion: Your data might be centered at a different wavelength.")
    print(f"Try customizing the range to match your data.")
    raise ValueError(f"No data found in range {minWavelength:.2f} - {maxWavelength:.2f} nm")

# Normalize power
power_normalized = power_limited / np.max(power_limited)

# Find peaks
peaks, _ = find_peaks(power_normalized, height=0.4)
peak_wavelengths = wavelength_limited[peaks]
print(f"\nAuto-detected {len(peaks)} peaks")

# Calculate data spacing and window size
wavelength_spacing = np.median(np.diff(wavelength_limited))
# Set window size to capture dip/peak width (~0.06 nm = 60 pm) - adjustable via sliders
window_size = max(25, int(0.06 / wavelength_spacing))
print(f"Data spacing: {wavelength_spacing*1e3:.4f} pm")
print(f"Peak window size: {window_size} points ({window_size*wavelength_spacing*1e3:.1f} pm)")

# Create output folder
output_folder = os.path.dirname(benchtopFile)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create descriptive folder name with .mat filename and channel number
mat_basename = os.path.splitext(os.path.basename(benchtopFile))[0]  # Remove .mat extension

if file_format == 'channel_mW':
    channel_name = selected_channel.replace('channel_', 'Ch').replace('_mW', '')
    analysis_folder = os.path.join(output_folder, f"Q_Analysis_{timestamp}_{mat_basename}_{channel_name}")
elif file_format == 'power_matrix':
    analysis_folder = os.path.join(output_folder, f"Q_Analysis_{timestamp}_{mat_basename}_Ch{channel_choice}")

os.makedirs(analysis_folder, exist_ok=True)
print(f"\nOutput folder: {analysis_folder}")

# Show initial plot
plt.figure(figsize=(12, 6))
plt.plot(wavelength_limited, power_normalized, '-k', linewidth=1.5, label='Benchtop Data')
plt.plot(wavelength_limited[peaks], power_normalized[peaks], 'r^', markersize=10, label='Auto-detected peaks')
plt.xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
plt.ylabel('Normalized Power', fontsize=PLOT_FONT_AXIS_LABEL)
plt.title(f'Benchtop Laser Spectrum\n{os.path.basename(benchtopFile)}', fontsize=PLOT_FONT_TITLE)
plt.grid(True)
plt.legend()
plt.tight_layout()
overview_file = os.path.join(analysis_folder, "00_Overview.png")
plt.savefig(overview_file, dpi=300)
print(f"Overview saved: {overview_file}")
plt.show()

# Ask for analysis mode
use_interactive = messagebox.askyesno("Peak Selection", 
    f"Auto-detected {len(peaks)} peaks.\n\nUse interactive selection?\n\nYes = Click to select\nNo = Use auto-detected")

if use_interactive:
    print("\nInteractive mode: Click peaks to select...")
    peaks = interactive_peak_selection(wavelength_limited, power_normalized, 
                                      title='Select Peaks for Q Analysis')
    print(f"Selected {len(peaks)} peaks")

if len(peaks) == 0:
    print("No peaks selected. Exiting.")
    exit()

# Analyze each peak
print(f"\n=== Analyzing {len(peaks)} Peaks ===")
results = []
Q_factors = []
FWHMs = []

for i, peak_idx in enumerate(peaks):
    peak_wl = wavelength_limited[peak_idx]
    print(f"\n[Peak {i+1}/{len(peaks)}] λ = {peak_wl:.4f} nm")
    print("Adjust baseline with sliders, then Accept or Skip")
    
    save_filename = f"Peak{i+1:02d}_lambda{peak_wl:.4f}nm.png"
    save_path = os.path.join(analysis_folder, save_filename)
    
    result = analyze_peak_with_adjustable_baseline(
        wavelength_limited,
        power_normalized,
        peak_idx,
        initial_window=window_size,
        save_path=save_path,
        fit_dips=fit_dips
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

# Summary plot
if len(results) > 0:
    print(f"\n=== Creating Summary (accepted {len(results)}/{len(peaks)} peaks) ===")
    
    fig, (ax_main, ax_bar) = plt.subplots(2, 1, figsize=(12, 8),
                                           gridspec_kw={'height_ratios': [3, 1]})
    
    # Main plot with Q annotations
    ax_main.plot(wavelength_limited, power_normalized, '-k', linewidth=1.5, label='Data')
    
    analyzed_wavelengths = [r['wavelength'] for r in results]
    FSRs = np.diff(analyzed_wavelengths) * 1e3  # pm
    
    for res in results:
        peak_idx = res['peak_idx']
        ax_main.plot([res['wavelength']], [power_normalized[peak_idx]], 
                     'r^', markersize=10)
        ax_main.text(res['wavelength'], power_normalized[peak_idx]*0.92,
                    f"Q={res['Q']:.0f}\nFWHM={res['FWHM']*1e3:.1f}pm", 
                    fontsize=PLOT_FONT_TEXT, ha='center', color='magenta', va='top',
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
        ax_main.set_title(f'Benchtop Q-Factor Analysis Summary\n' +
                         f'Avg Q = {np.mean(Q_factors):.0f} ± {np.std(Q_factors):.0f}, ' +
                         f'Avg FSR = {np.mean(FSRs):.1f} ± {np.std(FSRs):.1f} pm, ' +
                         f'Finesse = {finesse:.1f}',
                         fontsize=PLOT_FONT_TITLE)
    else:
        ax_main.set_title(f'Benchtop Q-Factor Analysis Summary\n' +
                         f'Avg Q = {np.mean(Q_factors):.0f} ± {np.std(Q_factors):.0f}',
                         fontsize=14)
    
    ax_main.set_ylim([0, 1.05])
    ax_main.legend(fontsize=PLOT_FONT_LEGEND)
    ax_main.grid(True)
    
    # Bar chart of Q factors
    ax_bar.bar(analyzed_wavelengths, Q_factors, width=0.01, color='red', alpha=0.6)
    ax_bar.set_xlabel('Wavelength (nm)', fontsize=PLOT_FONT_AXIS_LABEL)
    ax_bar.set_ylabel('Q Factor', fontsize=PLOT_FONT_AXIS_LABEL)
    ax_bar.grid(True)
    
    plt.tight_layout()
    summary_file = os.path.join(analysis_folder, "Summary_Q_Analysis.png")
    plt.savefig(summary_file, dpi=300)
    print(f"Summary saved: {summary_file}")
    plt.show()
    
    # Save MATLAB file
    mat_file = os.path.join(analysis_folder, "Q_Analysis_Results.mat")
    scipy.io.savemat(mat_file, {
        'wavelength': wavelength_limited,
        'power_normalized': power_normalized,
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
        'fit_params': [r['params'] for r in results]
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