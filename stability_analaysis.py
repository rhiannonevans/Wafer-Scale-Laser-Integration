"""
Stability Analysis and Aggregated Plotting for Wafer-Scale Laser Integration
----------------------------------------------------------------------------

Date: 2025-05-31

Description:
-------------
This script analyzes and visualizes laser sweep data from multiple experimental folders.
It aggregates sweeps, normalizes and inverts power channels, and plots voltage, temperature,
and power characteristics for multiple datasets using different colormaps for comparison.
The script supports custom step sizes for temperature and voltage extraction and saves all
resulting figures to the specified output directory.

Colormap and Label Mapping:
- Inferno: Aggregated data_folder + datafolder2 ("500Sweeps_0.05")
- Viridis: Aggregated datafolder3 + datafolder4 ("200Sweeps_0.1")
- Cividis: Aggregated datafolder5 + datafolder6 + datafolder7 ("100Sweeps_0.02")

Author: [Your Name or Lab]
----------------------------------------------------------------------------

"""

import os
import re
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import loadmat
from scipy.signal import find_peaks

output_dir = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\Eval_sys'
os.makedirs(output_dir, exist_ok=True)
# Define the data folders
data_folder = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\Eval_sys\sweep_2025-05-29_13-23-48.29'
datafolder2 = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\Eval_sys\sweep_2025-05-29_16-36-34.29'
datafolder3 = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\Eval_sys\allfiles\sweep_3'
datafolder4 = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\Eval_sys\allfiles\sweep_4'
datafolder5 = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\Eval_sys\allfiles\sweep_1'
datafolder6 = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\Eval_sys\sweep_7'
datafolder7 = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\Eval_sys\sweep_8'


def plot_folder(data_folder, axes, cmap, color_frac=0.8):
    all_files = [f for f in os.listdir(data_folder) if re.match(r'laser_sweep_\d+\.mat', f)]
    nums = [int(re.search(r'laser_sweep_(\d+)\.mat', name).group(1)) for name in all_files]
    sort_idx = np.argsort(nums)
    files_sorted = [all_files[i] for i in sort_idx]
    num_curves = len(files_sorted)
    for idx, fname in enumerate(files_sorted):
        fn = os.path.join(data_folder, fname)
        S = loadmat(fn, squeeze_me=True)
        curr = np.atleast_1d(S['current'])
        voltage = np.atleast_1d(S['voltage'])
        srs_temps = np.atleast_1d(S['srs_temps'])
        power2 = np.atleast_1d(S['power2'])
        power3 = np.atleast_1d(S['power3'])
        power4 = np.atleast_1d(S['power4'])
        # Use only the first color_frac of the colormap to avoid very light colors
        color = cmap(color_frac * idx / max(num_curves - 1, 1))
        # Correct current indices for voltage and temperature
        temp_idx = np.arange(0, len(curr), 10)[:len(srs_temps)]
        volt_idx = np.arange(5, len(curr), 10)[:len(voltage)]
        # Plot voltage and temperature with correct current mapping
        axes[0].plot(curr[volt_idx], voltage, '-.', linewidth=2, color=color)
        axes[1].plot(curr[temp_idx], srs_temps, '-.', linewidth=2, color=color)
        # Channel 2: normalize and invert
        p2 = np.atleast_1d(S['power2'])
        p2norm = (p2 - np.min(p2)) / (np.max(p2) - np.min(p2)) if np.max(p2) != np.min(p2) else p2
        axes[2].plot(curr, 1 - p2norm, '-.', linewidth=2, color=color)
        # Channel 3: normalize and invert
        p3 = np.atleast_1d(S['power3'])
        p3norm = (p3 - np.min(p3)) / (np.max(p3) - np.min(p3)) if np.max(p3) != np.min(p3) else p3
        axes[3].plot(curr, 1 - p3norm, '-.', linewidth=2, color=color)
        # Channel 4: normalize and invert
        p4 = np.atleast_1d(S['power4'])
        p4norm = (p4 - np.min(p4)) / (np.max(p4) - np.min(p4)) if np.max(p4) != np.min(p4) else p4
        axes[4].plot(curr, 1 - p4norm, '-.', linewidth=2, color=color)

def aggregate_and_plot_folders(folders, axes, cmap, color_frac=0.8):
    all_files = []
    for folder in folders:
        if not os.path.exists(folder):
            print(f"Warning: Folder does not exist: {folder}")
            continue
        files = [os.path.join(folder, f) for f in os.listdir(folder) if re.match(r'laser_sweep_\d+\.mat', f)]
        all_files.extend(files)
    if not all_files:
        print("No files found for aggregation.")
        return
    nums = [int(re.search(r'laser_sweep_(\d+)\.mat', os.path.basename(name)).group(1)) for name in all_files]
    sort_idx = np.argsort(nums)
    files_sorted = [all_files[i] for i in sort_idx]
    num_curves = len(files_sorted)
    for idx, fn in enumerate(files_sorted):
        S = loadmat(fn, squeeze_me=True)
        curr = np.atleast_1d(S['current'])
        voltage = np.atleast_1d(S['voltage'])
        srs_temps = np.atleast_1d(S['srs_temps'])
        power2 = np.atleast_1d(S['power2'])
        power3 = np.atleast_1d(S['power3'])
        power4 = np.atleast_1d(S['power4'])
        color = cmap(color_frac * idx / max(num_curves - 1, 1))
        temp_idx = np.arange(0, len(curr), 10)[:len(srs_temps)]
        volt_idx = np.arange(5, len(curr), 10)[:len(voltage)]
        axes[0].plot(curr[volt_idx], voltage, '-.', linewidth=2, color=color)
        axes[1].plot(curr[temp_idx], srs_temps, '-.', linewidth=2, color=color)
        p2norm = (power2 - np.min(power2)) / (np.max(power2) - np.min(power2)) if np.max(power2) != np.min(power2) else power2
        axes[2].plot(curr, 1 - p2norm, '-.', linewidth=2, color=color)
        p3norm = (power3 - np.min(power3)) / (np.max(power3) - np.min(power3)) if np.max(power3) != np.min(power3) else power3
        axes[3].plot(curr, 1 - p3norm, '-.', linewidth=2, color=color)
        p4norm = (power4 - np.min(power4)) / (np.max(power4) - np.min(power4)) if np.max(power4) != np.min(power4) else power4
        axes[4].plot(curr, 1 - p4norm, '-.', linewidth=2, color=color)

def aggregate_and_plot_folders_custom_step(
    folders, axes, cmap, color_frac=0.8,
    temp_step=10, temp_start=0,
    volt_step=10, volt_start=5
):
    all_files = []
    for folder in folders:
        if not os.path.exists(folder):
            print(f"Warning: Folder does not exist: {folder}")
            continue
        files = [os.path.join(folder, f) for f in os.listdir(folder) if re.match(r'laser_sweep_\d+\.mat', f)]
        all_files.extend(files)
    if not all_files:
        print("No files found for aggregation.")
        return
    nums = [int(re.search(r'laser_sweep_(\d+)\.mat', os.path.basename(name)).group(1)) for name in all_files]
    sort_idx = np.argsort(nums)
    files_sorted = [all_files[i] for i in sort_idx]
    num_curves = len(files_sorted)
    for idx, fn in enumerate(files_sorted):
        S = loadmat(fn, squeeze_me=True)
        curr = np.atleast_1d(S['current'])
        voltage = np.atleast_1d(S['voltage'])
        srs_temps = np.atleast_1d(S['srs_temps'])
        power2 = np.atleast_1d(S['power2'])
        power3 = np.atleast_1d(S['power3'])
        power4 = np.atleast_1d(S['power4'])
        color = cmap(color_frac * idx / max(num_curves - 1, 1))
        temp_idx = np.arange(temp_start, len(curr), temp_step)[:len(srs_temps)]
        volt_idx = np.arange(volt_start, len(curr), volt_step)[:len(voltage)]
        axes[0].plot(curr[volt_idx], voltage, '-.', linewidth=2, color=color)
        axes[1].plot(curr[temp_idx], srs_temps, '-.', linewidth=2, color=color)
        # Channel 2: normalize and invert
        p2 = np.atleast_1d(S['power2'])
        p2norm = (p2 - np.min(p2)) / (np.max(p2) - np.min(p2)) if np.max(p2) != np.min(p2) else p2
        axes[2].plot(curr, 1 - p2norm, '-.', linewidth=2, color=color)
        # Channel 3: normalize and invert
        p3 = np.atleast_1d(S['power3'])
        p3norm = (p3 - np.min(p3)) / (np.max(p3) - np.min(p3)) if np.max(p3) != np.min(p3) else p3
        axes[3].plot(curr, 1 - p3norm, '-.', linewidth=2, color=color)
        # Channel 4: normalize and invert
        p4 = np.atleast_1d(S['power4'])
        p4norm = (p4 - np.min(p4)) / (np.max(p4) - np.min(p4)) if np.max(p4) != np.min(p4) else p4
        axes[4].plot(curr, 1 - p4norm, '-.', linewidth=2, color=color)

# Prepare figures
figs = [plt.figure(i+1) for i in range(5)]
axes = [figs[i].add_subplot(1,1,1) for i in range(5)]
axes[0].set(xlabel='Current (mA)', ylabel='Voltage(V)', xlim=[0.5, 49.96], title='Voltage Over Time')
axes[1].set(xlabel='Current (mA)', ylabel='Temperature (°C)', title='Temperature Over Time')
axes[2].set(xlabel='Current (mA)', ylabel='Power (ADC count)', title='LIV-Channel 2')
axes[3].set(xlabel='Current (mA)', ylabel='Power (ADC count)', title='Reflection Port-Channel 3')
axes[4].set(xlabel='Current (mA)', ylabel='Power (ADC count)', title='Transmission Port-Channel 4')

# Aggregate data_folder and datafolder2, plot with inferno colormap
aggregate_and_plot_folders([data_folder, datafolder2], axes, plt.get_cmap('inferno'), color_frac=0.8)

# Plot aggregated datafolder3 and datafolder4 with viridis colormap
aggregate_and_plot_folders([datafolder3, datafolder4], axes, plt.get_cmap('viridis'), color_frac=0.8)

# Plot aggregated datafolder5, datafolder6, datafolder7 with cividis colormap (step size 50)
aggregate_and_plot_folders_custom_step(
    [datafolder5, datafolder6, datafolder7],
    axes,
    plt.get_cmap('cividis'),
    color_frac=0.8,
    temp_step=50, temp_start=0,
    volt_step=50, volt_start=25  # 0.5mA = 25th index if step is 0.02mA, adjust if your current step is different!
)

# Add legends with custom labels for each colormap
legend_labels = [
    "500Sweeps_0.05",  # inferno (now aggregated 1+2)
    "200Sweeps_0.1",   # viridis
    "100Sweeps_0.02"   # cividis
]
legend_handles = []
legend_colors = [
    plt.get_cmap('inferno')(0.6),
    plt.get_cmap('viridis')(0.6),
    plt.get_cmap('cividis')(0.8)
]
for label, color in zip(legend_labels, legend_colors):
    handle = plt.Line2D([], [], color=color, linestyle='-.', linewidth=2, label=label)
    legend_handles.append(handle)

for ax in axes:
    ax.legend(handles=legend_handles, loc='best')

# Save each figure
for i, fig in enumerate(figs, 1):
    fig.savefig(os.path.join(output_dir, f'plot_{i}.png'), dpi=300, bbox_inches='tight')

plt.show()

# # Analyze both folders
# curr1, avg_power1, peak_currs1, peak_powers1 = analyze_channel4_peaks(data_folder)
# curr2, avg_power2, peak_currs2, peak_powers2 = analyze_channel4_peaks(datafolder2)

# # Plot average for both folders and mark peak ranges
# plt.figure()
# plt.plot(curr1, avg_power1, label='Inferno (avg)', color='orange')
# plt.plot(curr2, avg_power2, label='Gray (avg)', color='gray')

# # Mark the peak current and power range for both
# for peak_currs, peak_powers, color, label in [
#     (peak_currs1, peak_powers1, 'orange', 'Inferno'),
#     (peak_currs2, peak_powers2, 'gray', 'Gray')
# ]:
#     if len(peak_currs) > 0:
#         plt.axvspan(np.min(peak_currs), np.max(peak_currs), color=color, alpha=0.15)
#         plt.hlines([np.min(peak_powers), np.max(peak_powers)], xmin=np.min(curr1), xmax=np.max(curr1), colors=color, linestyles='dashed', alpha=0.5)
#         plt.scatter(peak_currs, peak_powers, color=color, s=20, label=f'{label} peaks')

# plt.xlabel('Current (mA)')
# plt.ylabel('Normalized Inverted Power (Ch. 4)')
# plt.title('Average Channel 4 with Peak Range')
# plt.legend()
# plt.grid(True)
# plt.show()

# # Use the new function for both folders
# curr1, avg_power1, peak_currs1, peak_powers1 = analyze_channel4_peaks_window(data_folder, 28, 33)
# curr2, avg_power2, peak_currs2, peak_powers2 = analyze_channel4_peaks_window(datafolder2, 28, 33)

# # Plot average for both folders and mark peak ranges (only in 28-33mA)
# plt.figure()
# plt.plot(curr1, avg_power1, label='Inferno (avg)', color='orange')
# plt.plot(curr2, avg_power2, label='Gray (avg)', color='gray')

# for peak_currs, peak_powers, color, label in [
#     (peak_currs1, peak_powers1, 'orange', 'Inferno'),
#     (peak_currs2, peak_powers2, 'gray', 'Gray')
# ]:
#     if len(peak_currs) > 0:
#         plt.axvspan(np.min(peak_currs), np.max(peak_currs), color=color, alpha=0.15)
#         plt.hlines([np.min(peak_powers), np.max(peak_powers)], xmin=np.min(curr1), xmax=np.max(curr1), colors=color, linestyles='dashed', alpha=0.5)
#         plt.scatter(peak_currs, peak_powers, color=color, s=20, label=f'{label} peaks (28-33mA)')

# plt.xlabel('Current (mA)')
# plt.ylabel('Normalized Inverted Power (Ch. 4)')
# plt.title('Average Channel 4 with Peak Range (28-33 mA)')
# plt.legend()
# plt.grid(True)
# plt.show()