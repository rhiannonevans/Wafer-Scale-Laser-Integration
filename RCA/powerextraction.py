import os
import csv
import scipy.io
# Plot font constants
PLOT_FONT_AXIS_LABEL = 18
PLOT_FONT_AXIS_TICKS = 18
PLOT_FONT_TITLE = 14
PLOT_FONT_LEGEND = 16
PLOT_FONT_TEXT = 9

#%%
# =============================================================================
# SECTION 1: Extract Power at Specific Wavelength (1550 nm)
# =============================================================================
# This section reads all .mat files in a user-specified folder and extracts
# the power values from 'channel_1' at exactly 1550 nm wavelength.
# Results are saved to a CSV file with filename and power value pairs.
# =============================================================================

# Prompt user for directory containing .mat files
folder = input("Enter the path to the folder containing .mat files: ")

# Initialize list to store results (filename, power)
results = []

# Loop through all .mat files in the folder
for filename in os.listdir(folder):
    if filename.endswith('.mat'):
        filepath = os.path.join(folder, filename)
        # Load MATLAB file
        mat_data = scipy.io.loadmat(filepath)

        # Extract wavelength and channel_1 data from .mat file
        # Assuming 'wavelength' and 'channel_1' are keys in the .mat file
        wavelength = mat_data.get('wavelength')
        channel_1 = mat_data.get('channel_1')

        if wavelength is not None and channel_1 is not None:
            # Flatten arrays if needed (convert from 2D to 1D)
            wavelength = wavelength.flatten()
            channel_1 = channel_1.flatten()
            
            # Find indices where wavelength is exactly 1550 nm
            indices = (wavelength == 1550)
            
            # Extract corresponding power values at those indices
            power_at_1550 = channel_1[indices]
            
            # Save each power value with its filename
            for power in power_at_1550:
                results.append([filename, power])
            print(f"{filename}: Power in channel 1 at 1550 nm: {power_at_1550}")
        else:
            print(f"{filename}: Required data not found in .mat file.")

# Write all results to CSV file
csv_filename = "power_at_1550nm.csv"
with open(csv_filename, mode='w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    # Write header row
    writer.writerow(['mat_file', 'power_at_1550nm'])
    # Write all data rows
    writer.writerows(results)

print(f"Results saved to {csv_filename}")

#%%
# =============================================================================
# SECTION 2: Extract Maximum Power in Wavelength Range (1329-1331 nm)
# =============================================================================
# This section finds the maximum power value in 'channel_4' within the
# wavelength range of 1329-1331 nm for each .mat file in the specified folder.
# Useful for finding peak laser output in a specific wavelength band.
# Results are saved to a separate CSV file.
# =============================================================================

import os
import csv
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import numpy as np
from matplotlib import cm
import scipy.io

# Prompt user for directory containing .mat files for max power extraction
folder_max = input("Enter the path to the folder containing .mat files for max power extraction: ")

# Initialize list to store max power results
max_power_results = []

# Find maximum power in channel_4 within wavelength range 1329 nm to 1331 nm for each file
for filename in os.listdir(folder_max):
    if filename.endswith('.mat'):
        filepath = os.path.join(folder_max, filename)
        # Load MATLAB file
        mat_data = scipy.io.loadmat(filepath)

        # Extract wavelength and channel_4 data
        wavelength = mat_data.get('wavelength')
        channel_2 = mat_data.get('channel_2')

        if wavelength is not None and channel_2 is not None:
            # Flatten arrays to 1D
            wavelength = wavelength.flatten()
            channel_2 = channel_2.flatten()
            
            # Find indices where wavelength is within the range [1308, 1312] nm
            indices = (wavelength >= 1308) & (wavelength <= 1312)
            
            # Check if any data points exist in this range
            if indices.any():
                # Find maximum power value in this wavelength range
                max_power = channel_2[indices].max()
                max_power_results.append([filename, max_power])
                print(f"{filename}: Max power in channel 2 between 1329-1331 nm: {max_power}")
            else:
                print(f"{filename}: No data in wavelength range 1329-1331 nm.")
        else:
            print(f"{filename}: Required data not found in .mat file.")

# Write max power results to CSV
max_csv_filename = "reanalyzed_max_power_1329_1331nm.csv"
with open(max_csv_filename, mode='w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    # Write header
    writer.writerow(['mat_file', 'max_power_1329_1331nm'])
    # Write data
    writer.writerows(max_power_results)

print(f"Max power results saved to {max_csv_filename}")

#%%
# =============================================================================
# SECTION 3: Extract Maximum Power and Corresponding Current (Recursive Search)
# =============================================================================
# This section recursively searches through all subfolders for .mat files,
# finds the maximum power in 'channel_0', and records the corresponding current
# value at that maximum. Also converts power from mW to dBm.
# Useful for L-I (Light-Current) curve analysis and threshold current determination.
# Results include: filename, max power (mW), power (dBm), and corresponding current.
# =============================================================================

import scipy.io
import csv
import numpy as np
import os

def find_mat_files(root_folder):
    """
    Recursively find all .mat files in root_folder and its subfolders.
    
    Parameters:
    -----------
    root_folder : str
        Top-level directory to search
    
    Returns:
    --------
    list of str
        Full paths to all .mat files found
    """
    mat_files = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith('.mat'):
                mat_files.append(os.path.join(root, file))
    return mat_files

# Prompt user for top-level folder
folder = input("Enter the path to the folder containing .mat files (including subfolders): ")

# Initialize results list
results = []

# Find all .mat files recursively
mat_files = find_mat_files(folder)

# Process each .mat file
for filepath in mat_files:
    filename = os.path.basename(filepath)
    mat_data = scipy.io.loadmat(filepath)

    # Extract channel_0 (power) and current data
    channel1 = mat_data.get('channel_2')  #  channel_2 is laser output for resonator Qaud C and D. channel 1 and 3 is reflection and tranmission respectively
    current = mat_data.get('current')

    if channel1 is not None and current is not None:
        # Flatten to 1D arrays
        channel1 = channel1.flatten()
        current = current.flatten()
        
        # Find index of maximum power
        max_idx = channel1.argmax()
        max_power_mW = float(channel1[max_idx])
        corresponding_current = float(current[max_idx])

        # Convert mW to dBm: dBm = 10 * log10(mW)
        # Handle non-positive values (which would cause log errors)
        if max_power_mW > 0:
            power_dBm = 10.0 * np.log10(max_power_mW)
        else:
            power_dBm = np.nan  # Not a Number for invalid conversions

        # Store results
        results.append([filename, max_power_mW, power_dBm, corresponding_current])
        print(f"{filename}: Max power (mW) = {max_power_mW}, dBm = {power_dBm}, Current = {corresponding_current}")
    else:
        print(f"{filename}: Required data not found in .mat file.")

# Save results to CSV
csv_filename = "max_power_channel2_ybranch.csv"
with open(csv_filename, mode='w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    # Write header with column names
    writer.writerow(['mat_file', 'max_power_channel2_ybranch', 'power_dBm', 'corresponding_current'])
    # Write all data rows
    writer.writerows(results)

print(f"Results saved to {csv_filename}")

#%%
# =============================================================================
# SECTION 4: Generate Individual L-I Curve Plots (Recursive, Auto-Save)
# =============================================================================
# This section recursively searches all subfolders for .mat files and generates
# individual L-I (Light-Current) curve plots for each file. Each plot shows:
#   - Channel 0 (Loopback GC): Reference measurement
#   - Channel 2 (On-chip laser output): Actual laser performance
# 
# Features:
#   - Converts power from mW to dBm for better dynamic range visualization
#   - Removes invalid data points (-200 dBm sentinels and NaN values)
#   - Uses inferno colormap for professional appearance
#   - Auto-saves all plots to a central "plots" folder
#   - Handles subdirectory structure to avoid filename collisions
# =============================================================================

import scipy.io
import csv
import numpy as np
import os
import matplotlib.pyplot as plt

# Set default font sizes for all plots (global settings)
FONT_SIZE = 16
TITLE_SIZE = 16
LEGEND_SIZE = 12
plt.rcParams.update({'font.size': FONT_SIZE})

# Prompt user for top-level folder to search recursively
root_folder = input("Enter the path to the TOP-LEVEL folder containing .mat files (will scan subfolders): ")

def mW_to_dBm(arr):
    """
    Convert power from milliwatts (mW) to decibel-milliwatts (dBm).
    
    Formula: dBm = 10 * log10(mW)
    
    Parameters:
    -----------
    arr : array-like
        Power values in mW
    
    Returns:
    --------
    numpy array
        Power values in dBm (NaN for non-positive inputs)
    """
    arr = np.asarray(arr, dtype=float)
    out = np.full_like(arr, np.nan, dtype=float)
    mask = arr > 0  # Only convert positive values
    out[mask] = 10.0 * np.log10(arr[mask])
    return out

# Create a single top-level plots directory for all output plots
plots_dir = os.path.join(root_folder, "plots")
os.makedirs(plots_dir, exist_ok=True)

# Walk through all subdirectories recursively
for dirpath, dirnames, filenames in os.walk(root_folder):
    for filename in filenames:
        # Skip non-.mat files
        if not filename.endswith('.mat'):
            continue
            
        filepath = os.path.join(dirpath, filename)
        
        # Try to load .mat file
        try:
            mat_data = scipy.io.loadmat(filepath)
        except Exception as e:
            print(f"Skipping {filepath}: failed to load (.mat) — {e}")
            continue

        # Extract required data: channel_0 (loopback), channel_2 (laser output), current
        channel_1 = mat_data.get('channel_0')
        channel_3 = mat_data.get('channel_2')
        current = mat_data.get('current')

        # Check if all required data exists
        if channel_1 is None or channel_3 is None or current is None:
            print(f"{filepath}: Required data not found, skipping.")
            continue

        # Flatten arrays to 1D
        try:
            channel_1 = channel_1.flatten()
            channel_3 = channel_3.flatten()
            current = current.flatten()
        except Exception as e:
            print(f"{filepath}: Failed to flatten arrays — {e}")
            continue

        # Convert power from mW to dBm
        ch0_dbm = mW_to_dBm(channel_1)
        ch2_dbm = mW_to_dBm(channel_3)

        # Remove invalid data points:
        # - -200 dBm is used as a sentinel value for bad/missing data
        # - NaN values from non-positive power measurements
        mask0 = np.isfinite(ch0_dbm) & (ch0_dbm != -200)
        mask2 = np.isfinite(ch2_dbm) & (ch2_dbm != -200)
        
        # Apply masks separately to keep current aligned with each channel
        current_ch0 = current[mask0]
        ch0_dbm_clean = ch0_dbm[mask0]
        current_ch2 = current[mask2]
        ch2_dbm_clean = ch2_dbm[mask2]

        # Use inferno colormap for line colors (professional color scheme)
        cmap = plt.get_cmap('inferno')
        color0 = cmap(0.15)  # Darker color for channel 0
        color1 = cmap(0.65)  # Brighter color for channel 2

        # Create the plot
        plt.figure(figsize=(8, 5))
        plt.plot(current_ch0, ch0_dbm_clean, label='Loopback GC [dBm]', color=color0)
        plt.plot(current_ch2, ch2_dbm_clean, label='On-chip laser output [dBm]', color=color1)

        # Set axis labels and title with larger fonts
        plt.xlabel('Current (mA)', fontsize=FONT_SIZE)
        plt.ylabel('Power (dBm)', fontsize=FONT_SIZE)
        plt.title(f'{os.path.splitext(os.path.basename(filepath))[0]}', fontsize=TITLE_SIZE)
        plt.tick_params(axis='both', which='major', labelsize=FONT_SIZE)
        plt.legend(fontsize=LEGEND_SIZE)
        plt.grid(True)
        plt.tight_layout()

        # Build output filename:
        # Extract part after 'Chip.' if present, prefix with subfolder path to avoid collisions
        base = os.path.splitext(filename)[0]
        if "Chip." in base:
            tail = base.split("Chip.", 1)[1].strip() or base
        else:
            tail = base

        # Add relative directory path to filename to handle duplicates in different subfolders
        rel_dir = os.path.relpath(dirpath, root_folder)
        if rel_dir != ".":
            tail = f"{rel_dir.replace(os.sep, '_')}_{tail}"

        # Sanitize filename (replace spaces with underscores)
        tail = tail.replace(" ", "_")
        out_png = os.path.join(plots_dir, f"{tail}_dBm.png")
        
        # Save plot as PNG
        try:
            plt.savefig(out_png, dpi=300, bbox_inches='tight')
            print(f"Saved plot: {out_png}")
        except Exception as e:
            print(f"Failed to save plot for {filepath}: {e}")
        plt.close()

#%%
# =============================================================================
# SECTION 5: Generate Overlay Plots (All Files Combined)
# =============================================================================
# This section creates three overlay plots combining data from ALL .mat files:
#   1. Combined overlay: Both channels on same plot
#      - Channel 0 (Non-connected GCs): Grayscale, dashed lines
#      - Channel 1 (Laser output): Inferno colormap, solid lines
#   2. Channel 1 only: All laser outputs (inferno colormap)
#   3. Channel 0 only: All loopback measurements (grayscale)
#
# Features:
#   - Recursive search through all subfolders
#   - Filters out invalid -200 dBm sentinel values and NaNs
#   - Color-codes each file differently for easy identification
#   - Automatic legend (suppressed if >30 traces to avoid clutter)
#   - Saves high-resolution PNG files
# 
# Use case: Compare laser performance across multiple devices/measurements
# =============================================================================

import os
import numpy as np
import scipy.io
import matplotlib.pyplot as plt

# Set default font sizes
FONT_SIZE = 16
TITLE_SIZE = 16
LEGEND_SIZE = 12
plt.rcParams.update({'font.size': FONT_SIZE})

def mW_to_dBm(arr):
    """
    Convert power from mW to dBm.
    Returns NaN for non-positive values to handle log domain properly.
    """
    arr = np.asarray(arr, dtype=float)
    out = np.full_like(arr, np.nan, dtype=float)
    mask = arr > 0
    out[mask] = 10.0 * np.log10(arr[mask])
    return out

# Prompt user for top-level folder
root_folder = input("Enter the path to the TOP-LEVEL folder containing .mat files (will scan subfolders): ")

# Collect data from all files
# items: list of tuples (label, current_ch0, ch0_dbm_clean, current_ch2, ch2_dbm_clean)
items = []

# Walk through all subdirectories
for dirpath, _, filenames in os.walk(root_folder):
    for fname in filenames:
        # Skip non-.mat files
        if not fname.endswith('.mat'):
            continue
            
        fp = os.path.join(dirpath, fname)
        
        # Try to load .mat file
        try:
            md = scipy.io.loadmat(fp)
        except Exception as e:
            print(f"Skipping {fp}: load failed — {e}")
            continue

        # Extract data: channel_0, channel_1 (note: different from Section 4!), current
        ch0 = md.get('channel_0')
        ch2 = md.get('channel_1')  # Using channel_1 instead of channel_2
        current = md.get('current')
        
        # Check if all required data exists
        if ch0 is None or ch2 is None or current is None:
            print(f"Skipping {fp}: missing channel_0/channel_1/current")
            continue
            
        # Flatten arrays
        try:
            ch0 = ch0.flatten()
            ch2 = ch2.flatten()
            current = current.flatten()
        except Exception as e:
            print(f"Skipping {fp}: flatten failed — {e}")
            continue
            
        # Verify array sizes match
        if current.size != ch0.size or current.size != ch2.size:
            print(f"Skipping {fp}: size mismatch (current {current.size}, ch0 {ch0.size}, ch2 {ch2.size})")
            continue

        # Convert to dBm
        ch0_dbm = mW_to_dBm(ch0)
        ch2_dbm = mW_to_dBm(ch2)

        # Filter out sentinel -200 dBm values and NaNs for each channel separately
        # Note: Using != 0 condition (should probably be != -200 for consistency)
        mask0 = np.isfinite(ch0_dbm) & (ch0_dbm != 0)
        mask2 = np.isfinite(ch2_dbm) & (ch2_dbm != 0)

        # Apply masks to get clean data
        current_ch0 = current[mask0]
        ch0_dbm_clean = ch0_dbm[mask0]
        current_ch2 = current[mask2]
        ch2_dbm_clean = ch2_dbm[mask2]

        # Skip file if both channels have no valid points after filtering
        if current_ch0.size == 0 and current_ch2.size == 0:
            print(f"Skipping {fp}: no valid data after filtering (-200 dBm / NaN removed).")
            continue

        # Create label from filename (extract part after "Chip." if present)
        base = os.path.splitext(fname)[0]
        if "Chip." in base:
            label = base.split("Chip.", 1)[1].strip() or base
        else:
            label = base
        label = label.replace(os.sep, "_").replace(" ", "_")
        
        # Store data for this file
        items.append((label, current_ch0, ch0_dbm_clean, current_ch2, ch2_dbm_clean))

# Check if any valid files were found
if not items:
    print("No valid .mat files found.")
    raise SystemExit(1)

# Prepare colormaps for different channels
N = len(items)
greys = plt.get_cmap('Greys')(np.linspace(0.2, 0.8, N))      # Grayscale for channel 0
inferno = plt.get_cmap('inferno')(np.linspace(0.15, 0.85, N)) # Inferno for channel 1/2

# --- Plot 1: Combined overlay (both channels) ---
plt.figure(figsize=(8, 6))
for i, (label, current_ch0, ch0_dbm_clean, current_ch2, ch2_dbm_clean) in enumerate(items):
    # Plot channel_0 in grayscale with dashed line (background reference)
    if current_ch0.size > 0:
        plt.plot(current_ch0, ch0_dbm_clean, color=greys[i], linewidth=1, alpha=0.9, linestyle='--')
    
    # Plot channel_1/2 in inferno with solid line (main data)
    if current_ch2.size > 0:
        plt.plot(current_ch2, ch2_dbm_clean, color=inferno[i], linewidth=1.2, alpha=0.9, label=label)

plt.xlabel('Current (mA)', fontsize=FONT_SIZE)
plt.ylabel('Power (dBm)', fontsize=FONT_SIZE)
plt.title('Overlay: All Channels (Non-connected GCs = grayscale, Laser output = inferno)')
plt.grid(True)

# Show legend only if not too many traces (avoids clutter)
if N <= 30:
    plt.legend(ncol=2, fontsize='medium', loc='best')
else:
    print(f"{N} traces: legend suppressed (too many entries).")

plt.tight_layout()
out_png = os.path.join(root_folder, "overlay_all_dBm.png")
plt.savefig(out_png, dpi=300, bbox_inches='tight')
print(f"Saved overlay plot: {out_png}")
plt.show()
plt.close()

# --- Plot 2: Channel 1/2 only overlay (inferno colormap) ---
# Collect only items that have valid channel_1/2 data
items_ch2 = [(label, current_ch2, ch2_dbm_clean) for (label, _, _, current_ch2, ch2_dbm_clean) in items if current_ch2.size > 0]

if items_ch2:
    N2 = len(items_ch2)
    inferno_colors = plt.get_cmap('inferno')(np.linspace(0.15, 0.85, N2))
    
    plt.figure(figsize=(8, 6))
    for i, (label, current_ch2, ch2_dbm_clean) in enumerate(items_ch2):
        plt.plot(current_ch2, ch2_dbm_clean, color=inferno_colors[i], linewidth=1.2, alpha=0.9, label=label)
    
    plt.xlabel('Current (mA)', fontsize=FONT_SIZE)
    plt.ylabel('Power (dBm)', fontsize=FONT_SIZE)
    plt.title('On-chip Laser Output', fontsize=TITLE_SIZE)
    plt.grid(True)
    
    # Show legend if not too crowded
    if N2 <= 30:
        plt.legend(ncol=2, fontsize=LEGEND_SIZE, loc='best')
    else:
        print(f"{N2} channel_2 traces: legend suppressed (too many entries).")
    
    plt.tight_layout()
    out_ch2 = os.path.join(root_folder, "overlay_channel2_dBm.png")
    plt.savefig(out_ch2, dpi=300, bbox_inches='tight')
    print(f"Saved channel_2 overlay plot: {out_ch2}")
    plt.show()
    plt.close()
else:
    print("No valid channel_2 data to plot.")

# --- Plot 3: Channel 0 only overlay (grayscale) ---
# Collect only items that have valid channel_0 data
items_ch0 = [(label, current_ch0, ch0_dbm_clean) for (label, current_ch0, ch0_dbm_clean, _, _) in items if current_ch0.size > 0]

if items_ch0:
    N0 = len(items_ch0)
    greys = plt.get_cmap('Greys')(np.linspace(0.2, 0.8, N0))
    
    plt.figure(figsize=(8, 6))
    for i, (label, current_ch0, ch0_dbm_clean) in enumerate(items_ch0):
        plt.plot(current_ch0, ch0_dbm_clean, color=greys[i], linewidth=1.0, alpha=0.9, linestyle='--', label=label)
    
    plt.xlabel('Current (mA)', fontsize=FONT_SIZE)
    plt.ylabel('Power (dBm)', fontsize=FONT_SIZE)
    plt.title('Non-connected GCs', fontsize=TITLE_SIZE)
    plt.grid(True)
    
    # Show legend if not too crowded
    if N0 <= 30:
        plt.legend(ncol=2, fontsize=LEGEND_SIZE, loc='best')
    else:
        print(f"{N0} channel_0 traces: legend suppressed (too many entries).")
    
    plt.tight_layout()
    out_ch0 = os.path.join(root_folder, "overlay_channel0_dBm.png")
    plt.savefig(out_ch0, dpi=300, bbox_inches='tight')
    print(f"Saved channel_0 overlay plot: {out_ch0}")
    plt.show()
    plt.close()
else:
    print("No valid channel_0 data to plot.")
#%%
import scipy.io
import matplotlib.pyplot as plt
import numpy as np
import os
import re
from datetime import datetime

root_folder = input("Enter path to top-level benchtop measurement folder (will scan subfolders): ").strip()
if not root_folder:
    raise SystemExit("No folder provided.")

# Fixed wavelength parameters (no prompting)
center_nm = 1330.0
half_width = 0.5
low_nm = center_nm - half_width
high_nm = center_nm + half_width

items = []  # tuples (label, wavelength_slice, channel4_mW_slice, date_str)

def extract_date_from_filename(filename):
    """
    Extract date from filename and return compact 8-digit string.
    Handles formats like: 2025_04_06, 20250406, etc.
    """
    # Look for date patterns with underscores: YYYY_MM_DD
    date_match = re.search(r'(\d{4})_(\d{2})_(\d{2})', filename)
    if date_match:
        year, month, day = date_match.groups()
        return f"{year}{month}{day}"  # Return as YYYYMMDD
    
    # Look for compact 8-digit date pattern: YYYYMMDD
    date_match = re.search(r'(\d{8})', filename)
    if date_match:
        return date_match.group(1)
    
    return None

# Track unique dates for month numbering
unique_dates = set()
date_to_month = {}

# First pass: collect all unique dates
for dirpath, _, filenames in os.walk(root_folder):
    for fname in filenames:
        if fname.endswith(".mat"):
            date_str = extract_date_from_filename(fname)
            if date_str:  # Only if it's a valid date
                unique_dates.add(date_str)

# Sort dates and assign month numbers
sorted_dates = sorted(list(unique_dates))
for i, date in enumerate(sorted_dates, 1):
    date_to_month[date] = i

# Second pass: process files
for dirpath, _, filenames in os.walk(root_folder):
    for fname in filenames:
        if not fname.endswith(".mat"):
            continue
        fp = os.path.join(dirpath, fname)
        try:
            md = scipy.io.loadmat(fp)
        except Exception as e:
            print(f"Skipping {fp}: load failed — {e}")
            continue

        # Check for data arrays - fix the array logic
        wl = None
        ch4 = None
        
        # Check wavelength keys in order of preference
        if 'wavelength' in md:
            wl = md['wavelength']
        elif 'wavelength_nm' in md:
            wl = md['wavelength_nm']
        elif 'wls' in md:
            wl = md['wls']
        
        # Check channel 4 keys in order of preference
        if 'channel_4_mW' in md:
            ch4 = md['channel_4_mW']
        elif 'channel_4' in md:
            ch4 = md['channel_4']
        elif 'channel4' in md:
            ch4 = md['channel4']

        if wl is None or ch4 is None:
            print(f"Skipping {fp}: missing wavelength or channel_4_mW")
            print(f"  Available keys: {[k for k in md.keys() if not k.startswith('__')]}")
            continue

        try:
            wl = np.asarray(wl).flatten().astype(float)
            ch4 = np.asarray(ch4).flatten().astype(float)
        except Exception as e:
            print(f"Skipping {fp}: conversion/flatten failed — {e}")
            continue

        if wl.size != ch4.size:
            print(f"Skipping {fp}: size mismatch (wavelength {wl.size}, channel_4 {ch4.size})")
            continue

        mask = (wl >= low_nm) & (wl <= high_nm) & np.isfinite(ch4)
        if not mask.any():
            print(f"Skipping {fp}: no data in {low_nm}-{high_nm} nm range")
            continue

        wl_slice = wl[mask]
        ch4_slice = ch4[mask]
        
        # Extract date from filename
        date_str = extract_date_from_filename(fname)
        
        # Only process files with valid dates
        if date_str and date_str in date_to_month:
            label = f"Month{date_to_month[date_str]}-{date_str}"
            items.append((label, wl_slice, ch4_slice, date_str))
        else:
            print(f"Skipping {fp}: no valid date found in filename")

if not items:
    raise SystemExit("No valid traces found in the requested wavelength range.")

# Sort items by date for consistent coloring
items.sort(key=lambda x: x[3])  # Sort by date_str

# Plot overlay of wavelength vs channel_4_mW
N = len(items)
plt.figure(figsize=(12, 8))  # Larger figure for better readability

# Use inferno colormap but fix deprecated warning
colors = plt.colormaps['inferno'](np.linspace(0.15, 0.85, N))

for i, (label, wl_slice, ch4_slice, _) in enumerate(items):
    plt.plot(wl_slice, ch4_slice, color=colors[i], linewidth=1.5, label=label)

# Set larger font sizes
plt.xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
plt.ylabel("Channel 4 (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
plt.title(f"Channel 4 Power around {center_nm:.1f} nm [{low_nm:.1f}-{high_nm:.1f} nm]", 
          fontsize=PLOT_FONT_TITLE, fontweight='bold', pad=20)

# Set tick parameters
plt.tick_params(axis='both', which='major', labelsize=PLOT_FONT_AXIS_TICKS)
plt.grid(True, alpha=0.3)

# Legend with appropriate size
if N <= 30:
    plt.legend(fontsize=PLOT_FONT_LEGEND, ncol=2, loc='best', framealpha=0.9)
else:
    print(f"{N} traces: legend suppressed to avoid clutter.")

plt.tight_layout()

# Save with descriptive filename
out_png = os.path.join(root_folder, f"overlay_channel4_{int(low_nm)}-{int(high_nm)}nm_monthly.png")
try:
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    print(f"Saved overlay plot: {out_png}")
except Exception as e:
    print(f"Failed to save plot: {e}")

plt.show()
plt.close()

# Print summary of files processed
print(f"\nProcessed {N} files:")
for i, (label, _, _, date_str) in enumerate(items):
    print(f"  {i+1}. {label} (from {date_str})")

#%%

# =============================================================================
# SECTION 6: Grating Coupler Loss Analysis from CSV Files
# =============================================================================
# This section reads loss data from both GC and PWB CSV files
# (1310nm, 1330nm, 1550nm), divides each value by 2 (to account for
# bidirectional coupling loss), converts to loss magnitude, and visualizes:
#   1) GC distributions (boxplot + per-wavelength histograms)
#   2) GC boxplot with PWB mean ± std overlay and delta subplot
# Results and summary statistics are saved to a user-specified location.
# =============================================================================

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from tkinter import filedialog
import tkinter as tk
import os
import re

# Define CSV file paths (adjust these paths to match your file locations)
csv_files = {
    '1310nm': r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\GCpower_at_1310nm.csv',
    '1330nm': r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\GCpower_at_1330nm.csv',
    '1550nm': r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\GCpower_at_1550nm.csv',
    'PWB1310nm': r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\PWBloss_at_1310nm.csv',
    'PWB1330nm': r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\PWBloss_at_1330nm.csv',
    'PWB1550nm': r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\PWBloss_at_1550nm.csv',
    'CladdedPWB': r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\Cladded_PWBloss.csv',
    'UncladdedPWB': r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\Uncladded_PWBloss.csv',
    'Claddeschips': r"C:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\Claddeschips_GCpower.csv",
    'Uncladdeschips': r"C:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\Uncladdeschips_GCpower.csv",
    'Benchtop_Measured': r"C:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\Benchtop.csv",
    "Estimated": r"C:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\Estimated.csv",
    "Loss": r"C:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\Loss.csv"
}

AXIS_FONT_SIZE = 27
TICK_FONT_SIZE = 25
LEGEND_FONT_SIZE = 20
TITLE_FONT_SIZE = 20
PWB_OVERLAY_COLOR = '#d81b60'  # distinct magenta for PWB mean ± std

PLOT_FONT_AXIS_LABEL = AXIS_FONT_SIZE 
PLOT_FONT_AXIS_TICKS = TICK_FONT_SIZE
PLOT_FONT_LEGEND = LEGEND_FONT_SIZE
PLOT_FONT_TITLE = TITLE_FONT_SIZE

def extract_chip_id(name_tag):
    """Extract chip ID (e.g., D22) from strings like:
    - '1550nm D22_AOI_L1' (PWB format)
    - '1550nm_ChipD22_L0_data.mat' (GC format)
    """
    if not isinstance(name_tag, str):
        return None
    tag = name_tag.strip()
    
    # Try GC format first: 1550nm_ChipD22_L0_data.mat
    m = re.search(r'Chip([A-Z0-9]+)', tag, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    
    # Try PWB format: 1550nm D22_AOI_L1
    m = re.search(r'^\s*\d{4}\s*nm\s+([^_\s]+)', tag, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    
    return None

def extract_wavelength_nm(name_tag):
    """Extract wavelength token (e.g., 1310nm) from file/tag strings."""
    if not isinstance(name_tag, str):
        return None
    tag = name_tag.strip()
    m = re.search(r'(\d{4})\s*nm', tag, flags=re.IGNORECASE)
    if m:
        return f"{m.group(1)}nm"
    return None

# Read and process data from each CSV file
wavelength_data = {}
loss_data_by_type = {'GC': {}, 'PWB': {}}
pwb_chip_losses = {}
gc_wavelength_losses_from_clad = {}
gc_clad_unclad_losses_from_csv = {'Cladded': [], 'Uncladded': []}
loss_circuit_data = {}
loss_column_data = {'expected': [], 'measured': []}
for wavelength, csv_file in csv_files.items():
    if not os.path.exists(csv_file):
        print(f"Warning: {csv_file} not found. Skipping {wavelength}.")
        continue
    
    # Read CSV file
    df = pd.read_csv(csv_file)

    # Dedicated handling for Loss.csv:
    # column 1 = circuit label, column 2 = expected loss (dB), column 3 = measured loss (dB)
    if wavelength == 'Loss':
        if df.shape[1] < 3:
            print("Warning: Loss.csv has fewer than 3 columns. Skipping Loss point plot data.")
            continue

        circuit_col = df.columns[0]
        expected_col = df.columns[1]
        measured_col = df.columns[2]

        circuit_labels = df[circuit_col].astype(str).str.strip().values
        expected_all = pd.to_numeric(df[expected_col], errors='coerce').values
        measured_all = pd.to_numeric(df[measured_col], errors='coerce').values

        for circuit_label, expected_val, measured_val in zip(circuit_labels, expected_all, measured_all):
            if not circuit_label:
                continue
            bucket = loss_circuit_data.setdefault(circuit_label, {'expected': [], 'measured': []})
            if np.isfinite(expected_val):
                bucket['expected'].append(float(expected_val))
                loss_column_data['expected'].append(float(expected_val))
            if np.isfinite(measured_val):
                bucket['measured'].append(float(measured_val))
                loss_column_data['measured'].append(float(measured_val))

        exp_valid = expected_all[np.isfinite(expected_all)]
        meas_valid = measured_all[np.isfinite(measured_all)]
        if exp_valid.size > 0:
            print(f"\nLoss (Expected, column 2) Statistics:\n  N: {len(exp_valid)}\n  Mean: {np.mean(exp_valid):.2f} dB\n  Std Dev: {np.std(exp_valid):.2f} dB")
        if meas_valid.size > 0:
            print(f"Loss (Measured, column 3) Statistics:\n  N: {len(meas_valid)}\n  Mean: {np.mean(meas_valid):.2f} dB\n  Std Dev: {np.std(meas_valid):.2f} dB")
        continue
    
    # Extract numeric column
    name_column = df.columns[0]
    if wavelength in ['Benchtop_Measured', 'Estimated']:
        # Benchtop/Estimated CSVs may not have dB values in the 2nd column; pick the most numeric column
        numeric_counts = {
            col: pd.to_numeric(df[col], errors='coerce').notna().sum()
            for col in df.columns
        }
        power_column = max(numeric_counts, key=numeric_counts.get)
    else:
        power_column = df.columns[1]

    powers_all = pd.to_numeric(df[power_column], errors='coerce').values
    valid_mask = np.isfinite(powers_all)
    powers = powers_all[valid_mask]

    if powers.size == 0:
        print(f"Warning: {wavelength} has no valid numeric values in column '{power_column}'. Skipping.")
        continue
    
    # Convert power to loss:
    # - Most CSVs store two-port power (dBm), so use abs(power/2) as per-coupler loss (dB)
    # - Benchtop_Measured and Estimated are already in dB, so no conversion is applied
    if wavelength in ['Benchtop_Measured', 'Estimated']:
        losses_db = powers
    else:
        losses_db = np.abs(powers / 2.0)
    
    # Store in dictionary
    wavelength_data[wavelength] = losses_db
    loss_type = 'PWB' if (wavelength.startswith('PWB') or wavelength in ['CladdedPWB', 'UncladdedPWB']) else 'GC'
    wavelength_nm = wavelength.replace('PWB', '')
    loss_data_by_type[loss_type][wavelength_nm] = losses_db

    # For Claddeschips/Uncladdeschips GC CSVs: build GC per-wavelength data from first-column tags
    if wavelength in ['Claddeschips', 'Uncladdeschips'] and name_column in df.columns:
        name_tags = df[name_column].astype(str).values
        for tag, power_dbm in zip(name_tags, powers_all):
            if not np.isfinite(power_dbm):
                continue
            wl_tag = extract_wavelength_nm(tag)
            if not wl_tag:
                continue
            loss_val = abs(power_dbm / 2.0)
            gc_wavelength_losses_from_clad.setdefault(wl_tag, []).append(loss_val)
            if wavelength == 'Claddeschips':
                gc_clad_unclad_losses_from_csv['Cladded'].append(loss_val)
            elif wavelength == 'Uncladdeschips':
                gc_clad_unclad_losses_from_csv['Uncladded'].append(loss_val)

    # For PWB and GC files, collect per-chip losses using the first column name tags
    if name_column in df.columns:
        name_tags = df[name_column].astype(str).values
        for tag, power_dbm in zip(name_tags, powers_all):
            if not np.isfinite(power_dbm):
                continue
            chip_id = extract_chip_id(tag)
            if not chip_id:
                continue
            chip_loss_db = abs(power_dbm / 2.0)
            if wavelength.startswith('PWB') or wavelength in ['CladdedPWB', 'UncladdedPWB']:
                pwb_chip_losses.setdefault(chip_id, []).append(chip_loss_db)
            else:
                # GC files - add chip-ID based GC losses
                loss_data_by_type['GC'].setdefault('chip_losses', {}).setdefault(chip_id, []).append(chip_loss_db)
    
    print(f"\n{wavelength} Statistics:")
    print(f"  Number of measurements: {len(losses_db)}")
    print(f"  Mean: {np.mean(losses_db):.2f} dB")
    print(f"  Median: {np.median(losses_db):.2f} dB")
    print(f"  Std Dev: {np.std(losses_db):.2f} dB")
    print(f"  Min: {np.min(losses_db):.2f} dB")
    print(f"  Max: {np.max(losses_db):.2f} dB")

# Check if any data was loaded
if not wavelength_data:
    print("Error: No CSV files found. Please check file paths.")
    raise SystemExit(1)

# Override GC wavelength distributions using Claddeschips/Uncladdeschips parsed by first-column wavelength tags
if gc_wavelength_losses_from_clad:
    print("Using Claddeschips/Uncladdeschips first-column wavelength tags for GC wavelength plots.")
    for wl in ['1310nm', '1330nm', '1550nm']:
        vals = np.asarray(gc_wavelength_losses_from_clad.get(wl, []), dtype=float)
        if vals.size > 0:
            loss_data_by_type['GC'][wl] = vals
            wavelength_data[wl] = vals

# Keep GC wavelengths for histogram-based plots
preferred_wavelength_order = ['1310nm', '1330nm', '1550nm']
gc_wavelengths = [wl for wl in preferred_wavelength_order if wl in loss_data_by_type['GC']]
if not gc_wavelengths:
    print("Error: No GC CSV data loaded. At least one GC file is required for Section 6 plots.")
    raise SystemExit(1)

# Prompt user for save directory
root = tk.Tk()
root.withdraw()  # Hide the main window
save_dir = filedialog.askdirectory(title="Select folder to save GC loss analysis plots")
if not save_dir:
    print("No directory selected. Plots will not be saved.")
    save_dir = None
root.destroy()

# Get inferno colormap
cmap_inferno = plt.get_cmap('inferno')
wavelengths = gc_wavelengths
inferno_colors = cmap_inferno(np.linspace(0.2, 0.8, len(wavelengths)))

# Create figure with boxplot + individual histograms for each wavelength
# Layout: [Boxplot] [Histogram 1] [Histogram 2] [Histogram 3]
fig, axes = plt.subplots(1, len(wavelengths) + 1, figsize=(6*(len(wavelengths)+1), 5))

# --- First subplot: Boxplot for all wavelengths ---
ax_box = axes[0]
data_for_boxplot = [wavelength_data[wl] for wl in wavelengths]

bp = ax_box.boxplot(data_for_boxplot, 
                     labels=wavelengths,
                     notch=True,
                     patch_artist=True,
                     medianprops=dict(color='white', linewidth=2),
                     whiskerprops=dict(color='black', linewidth=1.5),
                     capprops=dict(color='black', linewidth=1.5),
                     flierprops=dict(marker='o', markerfacecolor='orange', markersize=6, alpha=0.6, markeredgecolor='black'))

cmaps = {
    '1310': plt.get_cmap('inferno'),
    '1330': plt.get_cmap('viridis'),
    '1550': plt.get_cmap('cividis')
}
tab_colors = plt.get_cmap('tab10').colors
color_map = {
    '1310': tab_colors[4],   # purple
    '1330': tab_colors[2],   # green
    '1550': tab_colors[0],   # blue
}
colors = []
for wl in wavelengths:
    wl_str = str(wl)
    if '1310' in wl_str:
        colors.append(color_map['1310'])
    elif '1330' in wl_str:
        colors.append(color_map['1330'])
    elif '1550' in wl_str:
        colors.append(color_map['1550'])
    else:
        colors.append('gray')

# Boxplot coloring
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.8)

ax_box.set_xlabel('Wavelength', fontsize=PLOT_FONT_AXIS_LABEL)
ax_box.set_ylabel('GC Loss (dB)', fontsize=PLOT_FONT_AXIS_LABEL)
ax_box.grid(True, alpha=0.3, axis='y')
ax_box.tick_params(axis='both', labelsize=14)

# --- Remaining subplots: Individual histograms for each wavelength ---
for idx, wl in enumerate(wavelengths):
    color = colors[idx]
    ax = axes[idx + 1]
    losses = wavelength_data[wl]
    ax.hist(losses, bins=20, alpha=0.8, edgecolor='black', color=color)
    mean_val = np.mean(losses)
    median_val = np.median(losses)
    wl_str = str(wl)
    if '1310' in wl_str:
        cmap = cmaps['1310']
        ax.axvline(mean_val, color=cmap(0.9), linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f} dB')
        ax.axvline(median_val, color=cmap(0.1), linestyle='--', linewidth=2, label=f'Median: {median_val:.2f} dB')
    elif '1330' in wl_str:
        cmap = cmaps['1330']
        ax.axvline(mean_val, color=cmap(0.9), linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f} dB')
        ax.axvline(median_val, color=cmap(0.1), linestyle='--', linewidth=2, label=f'Median: {median_val:.2f} dB')
    elif '1550' in wl_str:
        cmap = cmaps['1550']
        ax.axvline(mean_val, color=cmap(0.9), linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f} dB')
        ax.axvline(median_val, color=cmap(0.1), linestyle='--', linewidth=2, label=f'Median: {median_val:.2f} dB')
    else:
        ax.axvline(mean_val, color='black', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f} dB')
        ax.axvline(median_val, color='gray', linestyle='--', linewidth=2, label=f'Median: {median_val:.2f} dB')
    ax.set_xlabel('GC Loss (dB)', fontsize=PLOT_FONT_AXIS_LABEL)
    ax.set_ylabel('Count', fontsize=PLOT_FONT_AXIS_LABEL)
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.legend(fontsize=PLOT_FONT_LEGEND, loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()

# Create combined GC-only data for overall statistics
all_data = np.concatenate([wavelength_data[wl] for wl in gc_wavelengths])

# Save the figure if directory was selected
if save_dir:
    save_path = os.path.join(save_dir, 'GC_Loss_Analysis_Per_Wavelength.png')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {save_path}")

# Display the plots
plt.show()

# Create a summary text file with statistics
if save_dir:
    summary_path = os.path.join(save_dir, 'GC_Loss_Statistics.txt')
    summary_labels = list(gc_wavelengths)
    with open(summary_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write("GRATING COUPLER LOSS ANALYSIS SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write("Note: Input values are power in dBm (typically negative).\n")
        f.write("      Reported values are loss magnitude in dB, computed as\n")
        f.write("      abs(power_dBm / 2) for bidirectional coupling loss.\n\n")
        
        for wavelength in summary_labels:
            data = wavelength_data[wavelength]
            f.write(f"\n{wavelength} Wavelength Statistics:\n")
            f.write("-" * 50 + "\n")
            f.write(f"  Number of measurements: {len(data)}\n")
            f.write(f"  Mean:                   {np.mean(data):.2f} dB\n")
            f.write(f"  Median:                 {np.median(data):.2f} dB\n")
            f.write(f"  Standard Deviation:     {np.std(data):.2f} dB\n")
            f.write(f"  Minimum:                {np.min(data):.2f} dB\n")
            f.write(f"  Maximum:                {np.max(data):.2f} dB\n")
            f.write(f"  Range (Max - Min):      {np.max(data) - np.min(data):.2f} dB\n")
            f.write(f"  25th Percentile:        {np.percentile(data, 25):.2f} dB\n")
            f.write(f"  75th Percentile:        {np.percentile(data, 75):.2f} dB\n")
            f.write(f"  IQR (75th - 25th):      {np.percentile(data, 75) - np.percentile(data, 25):.2f} dB\n")
        
        f.write("\n" + "="*70 + "\n")
        f.write("OVERALL STATISTICS (All Wavelengths Combined):\n")
        f.write("="*70 + "\n")
        f.write(f"  Total measurements:     {len(all_data)}\n")
        f.write(f"  Mean:                   {np.mean(all_data):.2f} dB\n")
        f.write(f"  Median:                 {np.median(all_data):.2f} dB\n")
        f.write(f"  Standard Deviation:     {np.std(all_data):.2f} dB\n")
        f.write(f"  Minimum:                {np.min(all_data):.2f} dB\n")
        f.write(f"  Maximum:                {np.max(all_data):.2f} dB\n")
        f.write(f"  Range:                  {np.max(all_data) - np.min(all_data):.2f} dB\n")
        
        # Add PWB chip-ID statistics if available
        if pwb_chip_losses:
            f.write("\n" + "="*70 + "\n")
            f.write("PWB CHIP-ID LOSS STATISTICS:\n")
            f.write("="*70 + "\n")
            for cid in sorted(pwb_chip_losses.keys()):
                losses = np.asarray(pwb_chip_losses[cid], dtype=float)
                f.write(f"\nChip {cid}:\n")
                f.write("-" * 50 + "\n")
                f.write(f"  Number of measurements: {len(losses)}\n")
                f.write(f"  Mean:                   {np.mean(losses):.2f} dB\n")
                f.write(f"  Median:                 {np.median(losses):.2f} dB\n")
                f.write(f"  Standard Deviation:     {np.std(losses):.2f} dB\n")
                f.write(f"  Minimum:                {np.min(losses):.2f} dB\n")
                f.write(f"  Maximum:                {np.max(losses):.2f} dB\n")
                f.write(f"  Range (Max - Min):      {np.max(losses) - np.min(losses):.2f} dB\n")
                f.write(f"  25th Percentile:        {np.percentile(losses, 25):.2f} dB\n")
                f.write(f"  75th Percentile:        {np.percentile(losses, 75):.2f} dB\n")
                f.write(f"  IQR (75th - 25th):      {np.percentile(losses, 75) - np.percentile(losses, 25):.2f} dB\n")
        
        # Add GC chip-ID statistics if available
        gc_chip_losses = loss_data_by_type['GC'].get('chip_losses', {})
        if gc_chip_losses:
            f.write("\n" + "="*70 + "\n")
            f.write("GC CHIP-ID LOSS STATISTICS:\n")
            f.write("="*70 + "\n")
            for cid in sorted(gc_chip_losses.keys()):
                losses = np.asarray(gc_chip_losses[cid], dtype=float)
                f.write(f"\nChip {cid}:\n")
                f.write("-" * 50 + "\n")
                f.write(f"  Number of measurements: {len(losses)}\n")
                f.write(f"  Mean:                   {np.mean(losses):.2f} dB\n")
                f.write(f"  Median:                 {np.median(losses):.2f} dB\n")
                f.write(f"  Standard Deviation:     {np.std(losses):.2f} dB\n")
                f.write(f"  Minimum:                {np.min(losses):.2f} dB\n")
                f.write(f"  Maximum:                {np.max(losses):.2f} dB\n")
                f.write(f"  Range (Max - Min):      {np.max(losses) - np.min(losses):.2f} dB\n")
                f.write(f"  25th Percentile:        {np.percentile(losses, 25):.2f} dB\n")
                f.write(f"  75th Percentile:        {np.percentile(losses, 75):.2f} dB\n")
                f.write(f"  IQR (75th - 25th):      {np.percentile(losses, 75) - np.percentile(losses, 25):.2f} dB\n")

        # Add Loss.csv expected vs measured column-wise statistics if available
        if loss_column_data['expected'] or loss_column_data['measured']:
            expected_all = np.array(loss_column_data['expected'], dtype=float)
            measured_all = np.array(loss_column_data['measured'], dtype=float)

            f.write("\n" + "="*70 + "\n")
            f.write("LOSS CSV: COLUMN-WISE EXPECTED VS MEASURED\n")
            f.write("="*70 + "\n")

            if expected_all.size > 0:
                f.write("\nExpected (column 2):\n")
                f.write("-" * 50 + "\n")
                f.write(f"  N:                      {len(expected_all)}\n")
                f.write(f"  Mean:                   {np.mean(expected_all):.2f} dB\n")
                f.write(f"  Standard Deviation:     {np.std(expected_all):.2f} dB\n")

            if measured_all.size > 0:
                f.write("\nMeasured (column 3):\n")
                f.write("-" * 50 + "\n")
                f.write(f"  N:                      {len(measured_all)}\n")
                f.write(f"  Mean:                   {np.mean(measured_all):.2f} dB\n")
                f.write(f"  Standard Deviation:     {np.std(measured_all):.2f} dB\n")
    
    print(f"Statistics summary saved to: {summary_path}")

print("\nGrating Coupler Loss Analysis Complete!")


# --- Replace overlay histogram with stacked subplots (3 separate histograms sharing x-axis) ---

# Use same inferno color mapping as multi_LIV.py for wavelengths
cmap_inferno = plt.get_cmap('gray')  # Use grayscale for consistent coloring of GC histograms
wavelength_order = ['1310nm', '1330nm', '1550nm']
inferno_colors_mapping = cmap_inferno(np.linspace(0.2, 0.8, len(wavelength_order)))
inferno_color_map = dict(zip(wavelength_order, inferno_colors_mapping))

# Map wavelengths to their inferno colors
colors_inferno = [inferno_color_map[wl] for wl in wavelengths]

# Create stacked subplots with different y-axis scales
fig_stacked, axes_stacked = plt.subplots(3, 1, figsize=(9, 7), sharex=True, sharey=False)

# Calculate common bin edges across all wavelengths
all_losses = np.concatenate([np.round(wavelength_data[wl], 1) for wl in wavelengths])
bin_edges = np.histogram_bin_edges(all_losses, bins=20)

# Define y-axis max values for each wavelength (to make comparable scaling)
y_max_values = {'1310nm': 25, '1330nm': 15, '1550nm': 5}

# Plot each wavelength in its own subplot
for idx, (wl, color) in enumerate(zip(wavelengths, colors_inferno)):
    ax = axes_stacked[idx]
    losses = np.round(wavelength_data[wl], 1)
    # Add space between value and unit for display
    wl_display = wl.replace('nm', ' nm')
    ax.hist(losses, bins=bin_edges, alpha=0.8, color=color, edgecolor='black', linewidth=0.4, label=wl_display)
    
    # Calculate mean/median but don't display in legend
    mean_val = np.mean(losses)
    median_val = np.median(losses)
    
    # Use consistent colors for mean and median across all subplots
    ax.axvline(mean_val, color='darkred', linestyle='--', linewidth=2)
    ax.axvline(median_val, color='darkblue', linestyle='--', linewidth=2)
    
    # Only add y-label to middle subplot
    if idx == 1:
        ax.set_ylabel('GC Counts', fontsize=AXIS_FONT_SIZE+2, fontweight='normal')
    
    # Add wavelength label inside the plot area (top-right corner)
    #ax.text(0.98, 0.95, wl, transform=ax.transAxes, fontsize=TITLE_FONT_SIZE, 
     #       fontweight='normal', va='top', ha='right')  
    ax.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE+2)
    ax.legend(fontsize=LEGEND_FONT_SIZE, loc='upper right', framealpha=0)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=0.7)
    
    # Set comparable y-axis scaling
    ax.set_ylim(0, y_max_values[wl])

# Only set x-label on bottom subplot
axes_stacked[-1].set_xlabel('GC Loss (dB)', fontsize=AXIS_FONT_SIZE, fontweight='normal')

plt.tight_layout()
if save_dir:
    stacked_path = os.path.join(save_dir, 'GC_Loss_Stacked_Histograms.png')
    plt.savefig(stacked_path, dpi=300, bbox_inches='tight')
    print(f"\nStacked histograms saved to: {stacked_path}")
plt.show()

# --- Clear comparison plot: GC boxplots + PWB median/std ---
fig_compare, ax_top = plt.subplots(figsize=(9, 7))

data_for_boxplot = [wavelength_data[wl] for wl in wavelengths]
wavelength_labels = [wl.replace('nm', '') for wl in wavelengths]
positions = np.arange(1, len(wavelengths) + 1)

bp = ax_top.boxplot(
    data_for_boxplot,
    positions=positions,
    labels=wavelength_labels,
    notch=True,
    patch_artist=True
)
for patch, color in zip(bp['boxes'], colors_inferno):
    patch.set_facecolor(color)
    patch.set_alpha(0.8)
    patch.set_edgecolor('black')
    patch.set_linewidth(0.5)
for median in bp['medians']:
    median.set_color('yellow')
    median.set_linewidth(2)

ax_top.set_ylabel('GC Loss (dB)', fontsize=AXIS_FONT_SIZE, fontweight='normal')
ax_top.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE)
ax_top.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=0.7)
ax_top.set_xlabel('Wavelength (nm)', fontsize=AXIS_FONT_SIZE, fontweight='normal')
ax_top.set_xticks(positions)
ax_top.set_xticklabels(wavelength_labels)

plt.tight_layout()
if save_dir:
    boxplot_path = os.path.join(save_dir, 'Loss_Boxplot_with_PWB_MedianStd.png')
    plt.savefig(boxplot_path, dpi=300, bbox_inches='tight')
    print(f"\nGC/PWB comparison plot saved to: {boxplot_path}")
plt.show()

# --- Cladded vs Uncladded PWB and GC loss comparison (notched boxplot) ---
cladded_vals = wavelength_data.get('CladdedPWB')
uncladded_vals = wavelength_data.get('UncladdedPWB')
estimated_vals = wavelength_data.get('Estimated')
benchtop_vals = wavelength_data.get('Benchtop_Measured')

# Extract cladded/uncladded GC directly from dedicated CSV sources
cladded_gc_vals = np.asarray(gc_clad_unclad_losses_from_csv.get('Cladded', []), dtype=float)
uncladded_gc_vals = np.asarray(gc_clad_unclad_losses_from_csv.get('Uncladded', []), dtype=float)

if cladded_vals is not None and len(cladded_vals) > 0 and uncladded_vals is not None and len(uncladded_vals) > 0:
    # Prepare data for boxplots: Cladded PWB, Uncladded PWB, Cladded GC, Uncladded GC, (optional) Benchtop
    boxplot_data = [cladded_vals, uncladded_vals]
    boxplot_labels = ['Cladded\nPWB', 'Uncladded\nPWB']

    print(
        f"Comparison plot datasets -> Cladded PWB: {len(cladded_vals)}, "
        f"Uncladded PWB: {len(uncladded_vals)}, "
        f"Estimated: {0 if estimated_vals is None else len(estimated_vals)}, "
        f"Benchtop: {0 if benchtop_vals is None else len(benchtop_vals)}, "
        f"Cladded GC: {len(cladded_gc_vals)}, Uncladded GC: {len(uncladded_gc_vals)}"
    )
    
    # Add GC data if available
    if len(cladded_gc_vals) > 0 and len(uncladded_gc_vals) > 0:
        boxplot_data.extend([cladded_gc_vals, uncladded_gc_vals])
        boxplot_labels.extend(['Cladded\nChip GC', 'Uncladded\nChip GC'])

    # Add estimated data (already in dB)
    if estimated_vals is not None and len(estimated_vals) > 0:
        boxplot_data.append(estimated_vals)
        boxplot_labels.append('Estimated')

    # Add benchtop data (already in dB) as the LAST plotted category
    if benchtop_vals is not None and len(benchtop_vals) > 0:
        boxplot_data.append(benchtop_vals)
        boxplot_labels.append('Benchtop\nMeasured')

    # Wider figure to prevent x-label overlap
    fig_width = max(12, 2.8 * len(boxplot_data))
    fig_clad_compare, ax_clad_compare = plt.subplots(figsize=(fig_width, 6.5))
    
    bp_clad = ax_clad_compare.boxplot(
        boxplot_data,
        labels=boxplot_labels,
        notch=True,
        patch_artist=True,
        medianprops=dict(color='white', linewidth=2),
        whiskerprops=dict(color='black', linewidth=1.5),
        capprops=dict(color='black', linewidth=1.5),
        flierprops=dict(marker='o', markerfacecolor='orange', markersize=5, alpha=0.6, markeredgecolor='black')
    )

    # Inferno color style for all categories in this comparison plot
    cmap_inferno = plt.get_cmap('inferno')
    compare_colors = cmap_inferno(np.linspace(0.2, 0.85, len(bp_clad['boxes'])))
    for patch, color in zip(bp_clad['boxes'], compare_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
        patch.set_edgecolor('black')
        patch.set_linewidth(1.0)

    ax_clad_compare.set_ylabel('Loss (dB)', fontsize=AXIS_FONT_SIZE)
    ax_clad_compare.tick_params(axis='x', which='major', labelsize=max(12, TICK_FONT_SIZE - 5))
    ax_clad_compare.tick_params(axis='y', which='major', labelsize=TICK_FONT_SIZE)
    ax_clad_compare.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=0.7)

    plt.tight_layout()
    fig_clad_compare.subplots_adjust(bottom=0.22)
    if save_dir:
        clad_compare_path = os.path.join(save_dir, 'PWB_GC_Estimated_Benchtop_Cladded_vs_Uncladded_Notched_Boxplot.png')
        plt.savefig(clad_compare_path, dpi=300, bbox_inches='tight')
        print(f"Cladded vs Uncladded PWB/GC/Estimated/Benchtop plot saved to: {clad_compare_path}")
    plt.show()

    # --- Additional Plot 1: ONLY cladded/uncladded PWB and GC (notched) ---
    boxplot_data_core = [cladded_vals, uncladded_vals]
    boxplot_labels_core = ['Cladded\nPWB', 'Uncladded\nPWB']
    if len(cladded_gc_vals) > 0 and len(uncladded_gc_vals) > 0:
        boxplot_data_core.extend([cladded_gc_vals, uncladded_gc_vals])
        boxplot_labels_core.extend(['Cladded\nChip GC', 'Uncladded\nChip GC'])

    fig_width_core = max(10, 2.8 * len(boxplot_data_core))
    fig_core, ax_core = plt.subplots(figsize=(fig_width_core, 6.5))
    bp_core = ax_core.boxplot(
        boxplot_data_core,
        labels=boxplot_labels_core,
        notch=True,
        patch_artist=True,
        medianprops=dict(color='white', linewidth=2),
        whiskerprops=dict(color='black', linewidth=1.5),
        capprops=dict(color='black', linewidth=1.5),
        flierprops=dict(marker='o', markerfacecolor='orange', markersize=5, alpha=0.6, markeredgecolor='black')
    )
    cmap_inferno = plt.get_cmap('inferno')
    cmap_gray = plt.get_cmap('gray')
    n_pwb = sum('GC' not in lbl for lbl in boxplot_labels_core)
    n_gc = sum('GC' in lbl for lbl in boxplot_labels_core)
    pwb_colors = cmap_inferno(np.linspace(0.25, 0.75, max(1, n_pwb)))
    gc_colors = cmap_gray(np.linspace(0.35, 0.75, max(1, n_gc)))
    i_pwb, i_gc = 0, 0
    core_colors = []
    for lbl in boxplot_labels_core:
        if 'GC' in lbl:
            core_colors.append(gc_colors[i_gc])
            i_gc += 1
        else:
            core_colors.append(pwb_colors[i_pwb])
            i_pwb += 1

    for patch, color in zip(bp_core['boxes'], core_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
        patch.set_edgecolor('black')
        patch.set_linewidth(1.0)

    ax_core.set_ylabel('Loss (dB)', fontsize=AXIS_FONT_SIZE)
    ax_core.tick_params(axis='x', which='major', labelsize=max(12, TICK_FONT_SIZE - 5))
    ax_core.tick_params(axis='y', which='major', labelsize=TICK_FONT_SIZE)
    ax_core.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=0.7)
    plt.tight_layout()
    fig_core.subplots_adjust(bottom=0.22)
    if save_dir:
        core_path = os.path.join(save_dir, 'PWB_GC_Cladded_vs_Uncladded_Notched_Boxplot.png')
        plt.savefig(core_path, dpi=300, bbox_inches='tight')
        print(f"Cladded vs Uncladded PWB/GC-only plot saved to: {core_path}")
    plt.show()

    # --- Additional Plot 2: ONLY Estimated and Benchtop (notched) ---
    boxplot_data_ref = []
    boxplot_labels_ref = []
    if estimated_vals is not None and len(estimated_vals) > 0:
        boxplot_data_ref.append(estimated_vals)
        boxplot_labels_ref.append('Estimated')
    if benchtop_vals is not None and len(benchtop_vals) > 0:
        boxplot_data_ref.append(benchtop_vals)
        boxplot_labels_ref.append('Benchtop\nMeasured')

    if boxplot_data_ref:
        fig_width_ref = max(8, 3.2 * len(boxplot_data_ref))
        fig_ref, ax_ref = plt.subplots(figsize=(fig_width_ref, 6.5))
        bp_ref = ax_ref.boxplot(
            boxplot_data_ref,
            labels=boxplot_labels_ref,
            notch=True,
            patch_artist=True,
            medianprops=dict(color='white', linewidth=2),
            whiskerprops=dict(color='black', linewidth=1.5),
            capprops=dict(color='black', linewidth=1.5),
            flierprops=dict(marker='o', markerfacecolor='orange', markersize=5, alpha=0.6, markeredgecolor='black')
        )
        ref_colors = cmap_inferno(np.linspace(0.2, 0.85, len(bp_ref['boxes'])))
        for patch, color in zip(bp_ref['boxes'], ref_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.85)
            patch.set_edgecolor('black')
            patch.set_linewidth(1.0)

        ax_ref.set_ylabel('Loss (dB)', fontsize=AXIS_FONT_SIZE)
        ax_ref.tick_params(axis='x', which='major', labelsize=max(12, TICK_FONT_SIZE - 5))
        ax_ref.tick_params(axis='y', which='major', labelsize=TICK_FONT_SIZE)
        ax_ref.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=0.7)
        plt.tight_layout()
        fig_ref.subplots_adjust(bottom=0.22)
        if save_dir:
            ref_path = os.path.join(save_dir, 'Estimated_vs_Benchtop_Notched_Boxplot.png')
            plt.savefig(ref_path, dpi=300, bbox_inches='tight')
            print(f"Estimated vs Benchtop plot saved to: {ref_path}")
        plt.show()
    else:
        print("Estimated/Benchtop-only plot skipped: no valid Estimated or Benchtop data.")

    # --- Additional Plot 3: GC vs PWB notched boxplots for each wavelength ---
    shared_wavelengths = [
        wl for wl in preferred_wavelength_order
        if wl in loss_data_by_type['GC'] and wl in loss_data_by_type['PWB']
    ]
    if shared_wavelengths:
        wl_boxplot_data = []
        wl_boxplot_labels = []
        for wl in shared_wavelengths:
            wl_boxplot_data.extend([
                np.asarray(loss_data_by_type['GC'][wl], dtype=float),
                np.asarray(loss_data_by_type['PWB'][wl], dtype=float)
            ])
            wl_boxplot_labels.extend([f'GC\n{wl}', f'PWB\n{wl}'])

        fig_width_wl = max(10, 1.8 * len(wl_boxplot_data))
        fig_wl_cmp, ax_wl_cmp = plt.subplots(figsize=(fig_width_wl, 6.5))
        bp_wl = ax_wl_cmp.boxplot(
            wl_boxplot_data,
            labels=wl_boxplot_labels,
            notch=True,
            patch_artist=True,
            medianprops=dict(color='white', linewidth=2),
            whiskerprops=dict(color='black', linewidth=1.5),
            capprops=dict(color='black', linewidth=1.5),
            flierprops=dict(marker='o', markerfacecolor='orange', markersize=5, alpha=0.6, markeredgecolor='black')
        )

        # GC in grayscale, PWB in inferno
        gc_gray = plt.get_cmap('gray')(np.linspace(0.35, 0.75, len(shared_wavelengths)))
        pwb_inferno = plt.get_cmap('inferno')(np.linspace(0.25, 0.85, len(shared_wavelengths)))
        wl_colors = []
        for i in range(len(shared_wavelengths)):
            wl_colors.extend([gc_gray[i], pwb_inferno[i]])
        for patch, color in zip(bp_wl['boxes'], wl_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.88)
            patch.set_edgecolor('black')
            patch.set_linewidth(1.0)

        ax_wl_cmp.set_ylabel('Loss (dB)', fontsize=AXIS_FONT_SIZE)
        ax_wl_cmp.tick_params(axis='x', which='major', labelsize=max(12, TICK_FONT_SIZE - 5))
        ax_wl_cmp.tick_params(axis='y', which='major', labelsize=TICK_FONT_SIZE)
        ax_wl_cmp.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=0.7)
        plt.tight_layout()
        fig_wl_cmp.subplots_adjust(bottom=0.24)
        if save_dir:
            wl_cmp_path = os.path.join(save_dir, 'GC_PWB_PerWavelength_Notched_Boxplot.png')
            plt.savefig(wl_cmp_path, dpi=300, bbox_inches='tight')
            print(f"GC vs PWB per-wavelength notch plot saved to: {wl_cmp_path}")
        plt.show()
    else:
        print("GC vs PWB per-wavelength notch plot skipped: missing overlapping wavelength data.")
else:
    print("Cladded/Uncladded comparison skipped: PWB datasets were not found.")

# --- Loss.csv point plot: column-wise expected vs measured (mean ± SD) ---
if loss_column_data['expected'] or loss_column_data['measured']:
    expected_all = np.array(loss_column_data['expected'], dtype=float)
    measured_all = np.array(loss_column_data['measured'], dtype=float)

    categories = []
    means = []
    sds = []
    markers = []
    colors = []

    cmap_inferno = plt.get_cmap('inferno')
    if expected_all.size > 0:
        categories.append('Expected PIC\nLoss with GCs')
        means.append(np.mean(expected_all))
        sds.append(np.std(expected_all))
        markers.append('o')
        colors.append(cmap_inferno(0.35))
    if measured_all.size > 0:
        categories.append('Measured PIC\nLoss with GCs')
        means.append(np.mean(measured_all))
        sds.append(np.std(measured_all))
        markers.append('s')
        colors.append(cmap_inferno(0.75))

    if len(categories) == 2:
        x_pos = np.array([0.0, 0.45])
    else:
        x_pos = np.arange(len(categories), dtype=float)
    fig_loss_cmp, ax_loss_cmp = plt.subplots(figsize=(8.5, 6.5))

    for i in range(len(categories)):
        ax_loss_cmp.errorbar(
            x_pos[i],
            means[i],
            yerr=sds[i],
            fmt=markers[i],
            color=colors[i],
            ecolor=colors[i],
            elinewidth=2.6,
            capsize=5,
            markersize=8,
            markerfacecolor='white',
            markeredgewidth=2.2
        )

    ax_loss_cmp.set_ylabel('Circuit Loss (dB)', fontsize=AXIS_FONT_SIZE)
    ax_loss_cmp.set_xlabel('')
    ax_loss_cmp.set_xticks(x_pos)
    ax_loss_cmp.set_xticklabels(categories, rotation=0, ha='center')
    if len(x_pos) > 0:
        ax_loss_cmp.set_xlim(np.min(x_pos) - 0.12, np.max(x_pos) + 0.12)
    ax_loss_cmp.tick_params(axis='x', which='major', labelsize=AXIS_FONT_SIZE)
    ax_loss_cmp.tick_params(axis='y', which='major', labelsize=TICK_FONT_SIZE)
    ax_loss_cmp.grid(True, alpha=0.3, axis='y', linestyle='--', linewidth=0.7)
    plt.tight_layout()

    if save_dir:
        loss_cmp_path = os.path.join(save_dir, 'Loss_Expected_vs_Measured_Mean_SD_PointPlot.png')
        plt.savefig(loss_cmp_path, dpi=300, bbox_inches='tight')
        print(f"Loss expected vs measured point plot saved to: {loss_cmp_path}")
    plt.show()
else:
    print("Loss expected/measured point plot skipped: no valid Loss.csv expected/measured data found.")

# --- Chip-ID summary: overlay GC and PWB data on point-range plot ---
# Extract GC chip losses from the nested structure
gc_chip_losses = loss_data_by_type['GC'].get('chip_losses', {})

if pwb_chip_losses or gc_chip_losses:
    # Get union of all chip IDs from both GC and PWB
    all_chip_ids = set(pwb_chip_losses.keys()) | set(gc_chip_losses.keys())
    chip_ids_sorted = sorted(all_chip_ids)
    x_pos = np.arange(len(chip_ids_sorted))
    
    # Compute PWB statistics
    pwb_chip_median = []
    pwb_chip_iqr_low = []
    pwb_chip_iqr_high = []
    for cid in chip_ids_sorted:
        if cid in pwb_chip_losses:
            data = np.asarray(pwb_chip_losses[cid], dtype=float)
            median = np.median(data)
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            pwb_chip_median.append(median)
            pwb_chip_iqr_low.append(median - q1)
            pwb_chip_iqr_high.append(q3 - median)
        else:
            pwb_chip_median.append(np.nan)
            pwb_chip_iqr_low.append(0)
            pwb_chip_iqr_high.append(0)
    pwb_chip_median = np.array(pwb_chip_median)
    pwb_chip_iqr_low = np.array(pwb_chip_iqr_low)
    pwb_chip_iqr_high = np.array(pwb_chip_iqr_high)
    
    # Compute GC statistics
    gc_chip_median = []
    gc_chip_iqr_low = []
    gc_chip_iqr_high = []
    for cid in chip_ids_sorted:
        if cid in gc_chip_losses:
            data = np.asarray(gc_chip_losses[cid], dtype=float)
            median = np.median(data)
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            gc_chip_median.append(median)
            gc_chip_iqr_low.append(median - q1)
            gc_chip_iqr_high.append(q3 - median)
        else:
            gc_chip_median.append(np.nan)
            gc_chip_iqr_low.append(0)
            gc_chip_iqr_high.append(0)
    gc_chip_median = np.array(gc_chip_median)
    gc_chip_iqr_low = np.array(gc_chip_iqr_low)
    gc_chip_iqr_high = np.array(gc_chip_iqr_high)
    
    # Publication-style point-range plot: median ± IQR with both GC and PWB overlaid
    fig_point_iqr, ax_point_iqr = plt.subplots(figsize=(max(10, len(chip_ids_sorted) * 0.55), 6))
    
    # Offset positions for overlaid points
    offset = 0.12
    x_pos_pwb = x_pos - offset
    x_pos_gc = x_pos + offset
    
    # Plot PWB data
    pwb_valid = ~np.isnan(pwb_chip_median)
    ax_point_iqr.errorbar(
        x_pos_pwb[pwb_valid],
        pwb_chip_median[pwb_valid],
        yerr=np.vstack([pwb_chip_iqr_low[pwb_valid], pwb_chip_iqr_high[pwb_valid]]),
        fmt='o',
        color='#d81b60',  # Magenta for PWB
        ecolor='#d81b60',
        elinewidth=2.8,
        capsize=4,
        markersize=7,
        markerfacecolor='white',
        markeredgewidth=2.4,
        label='PWB'
    )
    
    # Plot GC data
    gc_valid = ~np.isnan(gc_chip_median)
    ax_point_iqr.errorbar(
        x_pos_gc[gc_valid],
        gc_chip_median[gc_valid],
        yerr=np.vstack([gc_chip_iqr_low[gc_valid], gc_chip_iqr_high[gc_valid]]),
        fmt='s',
        color='#2ca02c',  # Green for GC
        ecolor='#2ca02c',
        elinewidth=2.8,
        capsize=4,
        markersize=7,
        markerfacecolor='white',
        markeredgewidth=2.4,
        label='GC'
    )
    
    ax_point_iqr.set_xlabel('Chip ID', fontsize=AXIS_FONT_SIZE+2)
    ax_point_iqr.set_ylabel('Insertion loss (dB)', fontsize=AXIS_FONT_SIZE)
    ax_point_iqr.set_xticks(x_pos)
    ax_point_iqr.set_xticklabels(chip_ids_sorted, rotation=60, ha='center')
    ax_point_iqr.set_xlim(-0.5, len(chip_ids_sorted) - 0.5)
    ax_point_iqr.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE)
    ax_point_iqr.grid(True, alpha=0.3, axis='y')
    ax_point_iqr.legend(fontsize=LEGEND_FONT_SIZE, loc='best', framealpha=0.9)
    plt.tight_layout()
    if save_dir:
        point_iqr_path = os.path.join(save_dir, 'ChipID_Median_IQR_GCvsPWB_PointRange.png')
        plt.savefig(point_iqr_path, dpi=300, bbox_inches='tight')
        print(f"Chip median±IQR point-range plot (GC vs PWB) saved to: {point_iqr_path}")
    plt.show()
    
    # PWB-only point-range plot (excluding chip IDs with no PWB data)
    if pwb_chip_losses:
        # Filter to only chip IDs that have PWB data
        pwb_only_chip_ids = sorted([cid for cid in chip_ids_sorted if cid in pwb_chip_losses])
        pwb_only_indices = [i for i, cid in enumerate(chip_ids_sorted) if cid in pwb_chip_losses]
        x_pos_pwb_only = np.arange(len(pwb_only_chip_ids))
        
        fig_pwb_only, ax_pwb_only = plt.subplots(figsize=(max(10, len(pwb_only_chip_ids) * 0.55), 6))
        ax_pwb_only.errorbar(
            x_pos_pwb_only,
            pwb_chip_median[pwb_only_indices],
            yerr=np.vstack([pwb_chip_iqr_low[pwb_only_indices], pwb_chip_iqr_high[pwb_only_indices]]),
            fmt='o',
            color="#241d1f",  # Dark color for PWB
            ecolor="#241d1f",
            elinewidth=2.8,
            capsize=4,
            markersize=7,
            markerfacecolor='white',
            markeredgewidth=2.4,
            label='PWB'
        )
        ax_pwb_only.set_xlabel('Chip ID', fontsize=AXIS_FONT_SIZE+2)
        ax_pwb_only.set_ylabel('PWB Insertion Loss (dB)', fontsize=AXIS_FONT_SIZE)
        ax_pwb_only.set_xticks(x_pos_pwb_only)
        ax_pwb_only.set_xticklabels(pwb_only_chip_ids, rotation=60, ha='center')
        ax_pwb_only.set_xlim(-0.5, len(pwb_only_chip_ids) - 0.5)
        ax_pwb_only.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE)
        ax_pwb_only.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        if save_dir:
            pwb_only_path = os.path.join(save_dir, 'PWB_ChipID_Median_IQR_PointRange.png')
            plt.savefig(pwb_only_path, dpi=300, bbox_inches='tight')
            print(f"PWB-only chip median±IQR point-range plot saved to: {pwb_only_path}")
        plt.show()

    # Notched boxplot for PWB loss at 3 wavelengths using inferno colormap
    pwb_wavelength_order = [wl for wl in ['1310nm', '1330nm', '1550nm'] if wl in loss_data_by_type['PWB']]
    if pwb_wavelength_order:
        cmap_inferno = plt.get_cmap('inferno')
        wavelength_order = ['1310nm', '1330nm', '1550nm']
        inferno_colors_mapping = cmap_inferno(np.linspace(0.2, 0.8, len(wavelength_order)))
        inferno_color_map = dict(zip(wavelength_order, inferno_colors_mapping))

        fig_pwb_notch, ax_pwb_notch = plt.subplots(figsize=(9, 6))
        pwb_wavelength_data = [loss_data_by_type['PWB'][wl] for wl in pwb_wavelength_order]
        bp_pwb = ax_pwb_notch.boxplot(
            pwb_wavelength_data,
            labels=pwb_wavelength_order,
            notch=True,
            patch_artist=True,
            medianprops=dict(color='white', linewidth=2),
            whiskerprops=dict(color='black', linewidth=1.5),
            capprops=dict(color='black', linewidth=1.5),
            flierprops=dict(marker='o', markerfacecolor='orange', markersize=5, alpha=0.6, markeredgecolor='black')
        )

        for patch, wl in zip(bp_pwb['boxes'], pwb_wavelength_order):
            patch.set_facecolor(inferno_color_map[wl])
            patch.set_alpha(0.85)

        ax_pwb_notch.set_xlabel('Wavelength', fontsize=AXIS_FONT_SIZE)
        ax_pwb_notch.set_ylabel('Estimated PWB Loss (dB)', fontsize=AXIS_FONT_SIZE)
       # ax_pwb_notch.set_title('PWB Loss by Wavelength (Notched Boxplot)', fontsize=TITLE_FONT_SIZE)
        ax_pwb_notch.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE)
        ax_pwb_notch.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        if save_dir:
            pwb_notch_path = os.path.join(save_dir, 'PWB_Loss_Notched_Boxplot_Inferno.png')
            plt.savefig(pwb_notch_path, dpi=300, bbox_inches='tight')
            print(f"PWB notched boxplot saved to: {pwb_notch_path}")
        plt.show()
else:
    print("No valid chip IDs parsed from CSV first-column tags; chip-ID summary plots were skipped.")
# %%
#Section 7
# Survival-Style Yield Curve and Step-Loss Analysis
# =============================================================================

import matplotlib.pyplot as plt
import numpy as np

# ============================
# USER INPUT SECTION
# ============================
AXIS_FONT_SIZE = 20
TICK_FONT_SIZE = 18
LEGEND_FONT_SIZE = 18
TITLE_FONT_SIZE = 20
# 1) Names of process steps, in order
steps = [
    "Lasers under test",
    "Fab",
    "Die bond",
    "EWB",
    "PWB write",
    "PWB dev.",
    "Accidental fall",
    "PWB clad",
    "Stealth dicing",
    "Test setup",
    "Test",
    "Data analysis",
    "Final"
]

# 2) Total number of lasers under test at each stage
#    (this is the "Bonded Laser Dies Under Test" column)
n_total = np.array([101,101, 95, 90, 90, 90, 84,83, 83, 83, 82, 76,76])

# 3) Number of "good" lasers at each stage
#    (this is the "Good Bonded Laser Under Test" column)
n_good = np.array([101, 95, 90, 90, 90, 84, 83, 83, 83, 82, 76, 69, 69])

# ============================
# DERIVED QUANTITIES
# ============================

# Initial population (for survival baseline)
n_initial = n_total[0]

# Cumulative survival (cumulative yield) at each stage
# relative to the initial population
survival = n_good / n_initial * 100.0  # in %

# Step loss (how many are lost at each stage vs previous stage)
# using "good" counts only
step_loss = np.empty_like(n_good, dtype=float)
step_loss[0] = n_initial - n_good[0]              # loss at first stage vs initial
step_loss[1:] = n_good[:-1] - n_good[1:]          # subsequent drops

# Step yield (percentage that survive each step)
# Calculate yield for each step as: (good at stage / good at previous stage) * 100
step_yield = np.empty_like(n_good, dtype=float)
step_yield[0] = (n_good[0] / n_initial) * 100.0   # first stage vs initial
for i in range(1, len(n_good)):
    if n_good[i-1] > 0:
        step_yield[i] = (n_good[i] / n_good[i-1]) * 100.0
    else:
        step_yield[i] = 0.0

# Print step yield calculations for verification
print("\nStep Yield Calculations:")
print("=" * 70)
print(f"{'Step':<25} {'Good (prev)':<15} {'Good (curr)':<15} {'Step Yield (%)':<15}")
print("-" * 70)
print(f"{steps[0]:<25} {n_initial:<15} {n_good[0]:<15} {step_yield[0]:<15.2f}")
for i in range(1, len(steps)):
    print(f"{steps[i]:<25} {n_good[i-1]:<15} {n_good[i]:<15} {step_yield[i]:<15.2f}")
print("=" * 70 + "\n")

# For plotting on x-axis
x = np.arange(len(steps))

# ============================
# PLOT 1: SURVIVAL CURVE (SMOOTHED + STYLED)
# ============================

# Visual styling
bar_color = '#E8D5F8'      # light purple for step-loss bars
curve_color = "#471E47"    # dark purple for yield curve #22132B" 

plt.figure(figsize=(14, 5))

# Make y-axis tick labels larger for readability on subsequent plots
plt.rcParams['ytick.labelsize'] = AXIS_FONT_SIZE

# Plot the survival curve using the original stepwise style (where='post')
# but keep the improved styling (colors, markers, and y-limits).
plt.step(x, survival, where='post', color=curve_color, linewidth=2.5, zorder=3)
# Mark the actual stage points
plt.plot(x, survival, 'o', color=curve_color, markeredgecolor='white', markersize=8, zorder=4)

plt.xticks(x, steps, rotation=45, ha='right', fontsize=TICK_FONT_SIZE-1)
plt.ylabel("Cumulative yield (%)", fontsize=AXIS_FONT_SIZE-2)

# Improve vertical limits so the 100% -> ~68% range is not squeezed
if np.min(survival) >= 60:
    y_min = 0
else:
    y_min = max(0, np.min(survival) - 5)
y_max = min(105, np.max(survival) + 20)
plt.ylim(y_min, y_max)

plt.grid(True, linestyle='--', alpha=0.35)
plt.title("Survival-style yield curve across process stages", fontsize=TITLE_FONT_SIZE)
plt.tight_layout()
# Ensure output folder exists and save plots
save_dir = r"C:\Users\jsheri1\Desktop\Analysis"
try:
    os.makedirs(save_dir, exist_ok=True)
except Exception:
    pass
survival_path = os.path.join(save_dir, 'Survival_Yield_Curve.png')
plt.savefig(survival_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved survival plot to: {survival_path}")
plt.show()

# Also create a version without x-axis tick labels (clean for presentations)
fig_no_xt, ax_no_xt = plt.subplots(figsize=(14, 5))

# Scale x positions to make grid spacing wider
x_scaled = x * 1.5  # Increase spacing between grid lines

# Slightly thicker line and larger markers to make the plot "box" visually bigger
ax_no_xt.step(x_scaled, survival, where='post', color=curve_color, linewidth=3.0, zorder=3)
ax_no_xt.plot(x_scaled, survival, 'o', color=curve_color, markersize=6, zorder=4)
ax_no_xt.set_ylabel("Cumulative yield (%)", fontsize=AXIS_FONT_SIZE)
ax_no_xt.set_ylim(y_min, 115)

# Remove whitespace on both ends - set xlim to exactly match data range
ax_no_xt.set_xlim(x_scaled[0], x_scaled[-1])

# Place major x-ticks at the scaled stage positions (we'll hide labels) so vertical
# gridlines align with the stages
ax_no_xt.set_xticks(x_scaled)
ax_no_xt.tick_params(axis='x', which='both', length=0, labelbottom=False)
ax_no_xt.set_axisbelow(True)
# Draw both horizontal and vertical major gridlines with the same style
ax_no_xt.grid(which='major', axis='y', linestyle='--', alpha=0.35)
ax_no_xt.grid(which='major', axis='x', linestyle='-', alpha=0.35)
#ax_no_xt.set_title("Survival-style yield curve (no x-ticks)", fontsize=TITLE_FONT_SIZE)

# Set y-axis ticks explicitly to exclude 115
current_yticks = ax_no_xt.get_yticks()
# Filter out any tick at or above 115
filtered_yticks = [tick for tick in current_yticks if tick < 115]
ax_no_xt.set_yticks(filtered_yticks)

ax_no_xt.tick_params(axis='y', labelsize=AXIS_FONT_SIZE)
fig_no_xt.tight_layout()
survival_no_xticks_path = os.path.join(save_dir, 'Survival_Yield_NoXTicks.png')
try:
    fig_no_xt.savefig(survival_no_xticks_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved survival (no x-ticks) plot to: {survival_no_xticks_path}")
except Exception:
    pass
plt.show()

# ============================
# PLOT 2: STEP-LOSS BAR CHART (STYLED)
# ============================

plt.figure(figsize=(14, 5))
# Increase spacing by using scaled x positions (spacing_factor > 1 increases gaps)
spacing_factor = 1.5
x_pos = np.arange(len(steps)) * spacing_factor
# Make bars narrower to add gaps between them (bar width is in data units)
bar_width = 0.6
bars = plt.bar(x_pos, step_loss, width=bar_width, color=bar_color, edgecolor='#A78FBF', align='center')

# Prepare x-tick labels: break two-word labels into two lines (replace first space with newline)
def split_label_once(s):
    if isinstance(s, str) and ' ' in s:
        return s.replace(' ', '\n', 1)
    return s

# Wrap labels and remove the 'Initial' label entirely (use empty string)
labels_wrapped = [ ('' if isinstance(s, str) and s.strip().lower() == 'initial' else split_label_once(s)) for s in steps ]

# Set horizontal, centered x-ticks but skip the first position (remove empty 'Initial' tick)
tick_positions = x_pos[1:]
tick_labels = labels_wrapped[1:]
plt.xticks(tick_positions, tick_labels, rotation=0, ha='center', fontsize=TICK_FONT_SIZE)

# Tighten x-limits and make right-side whitespace symmetric with the left
# Left margin is half the bar width; set right margin equal to left margin
# Compute margin relative to the first VISIBLE bar (we skipped the 'Initial' tick)
first_visible_index = 1 if len(x_pos) > 1 else 0
margin = spacing_factor * 0.5
# Set x-limits so left/right whitespace around visible bars is symmetric
plt.xlim(x_pos[first_visible_index] - margin, x_pos[-1] + margin)

plt.ylabel("Loss count per step", fontsize=AXIS_FONT_SIZE)
#plt.title("Per-step loss of good lasers", fontsize=TITLE_FONT_SIZE)
plt.grid(True, axis='y', linestyle='--', alpha=0.35)

# Add value labels above bars for clarity
#for b in bars:
 #   h = b.get_height()
  #  plt.text(b.get_x() + b.get_width()/2.0, h + 0.5, f'{int(h)}', ha='center', va='bottom', fontsize=LEGEND_FONT_SIZE-2)

# Increase y-tick label size for the bar chart and set y-axis max to 8 (inclusive)
ax = plt.gca()
ax.tick_params(axis='y', labelsize=AXIS_FONT_SIZE)
ax.set_ylim(0, 8)
ax.set_yticks(np.arange(0, 9, 1))

plt.tight_layout()
step_loss_path = os.path.join(save_dir, 'Step_Loss_BarChart.png')
plt.savefig(step_loss_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved step-loss plot to: {step_loss_path}")
plt.show()

# ============================
# PLOT 3: GOOD LASERS BAR CHART (STYLED)
# ============================

plt.figure(figsize=(14, 5))
# Use same spacing and styling as step-loss chart
spacing_factor = 1.5
# Exclude "Final" from this chart
steps_no_final = steps[:-1]
n_good_no_final = n_good[:-1]
x_pos = np.arange(len(steps_no_final)) * spacing_factor
bar_width = 0.6
bars = plt.bar(x_pos, n_good_no_final, width=bar_width, color=bar_color, edgecolor='#A78FBF', align='center')

# Same label wrapping as step-loss chart
labels_wrapped = [split_label_once(s) for s in steps_no_final]

# Include all positions (including Initial)
plt.xticks(x_pos, labels_wrapped, rotation=0, ha='center', fontsize=TICK_FONT_SIZE)

# Symmetric margins including the first bar
margin = spacing_factor * 0.5
plt.xlim(x_pos[0] - margin, x_pos[-1] + margin)

plt.ylabel("Laser count per step", fontsize=AXIS_FONT_SIZE)
plt.grid(True, axis='y', linestyle='--', alpha=0.35)

# Increase y-tick label size and set appropriate y-axis limits
ax = plt.gca()
ax.tick_params(axis='y', labelsize=AXIS_FONT_SIZE)
# Set y-axis to go from 0 to slightly above max value
y_max = int(np.ceil(np.max(n_good) / 10) * 10)
ax.set_ylim(0, y_max)

plt.tight_layout()
good_lasers_path = os.path.join(save_dir, 'Good_Lasers_BarChart.png')
plt.savefig(good_lasers_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved good lasers plot to: {good_lasers_path}")
plt.show()

# ============================
# PLOT 4: STEP YIELD BAR CHART (STYLED)
# ============================

plt.figure(figsize=(14, 5))
# Use same spacing and styling
spacing_factor = 1.5
# Exclude first ("Lasers under test") and last ("Final") from this chart
steps_trimmed = steps[1:-1]
step_yield_trimmed = step_yield[1:-1]
x_pos = np.arange(len(steps_trimmed)) * spacing_factor
bar_width = 0.6
bars = plt.bar(x_pos, step_yield_trimmed, width=bar_width, color=bar_color, edgecolor='#A78FBF', align='center')

# Same label wrapping
labels_wrapped = [split_label_once(s) for s in steps_trimmed]

# Include all positions
plt.xticks(x_pos, labels_wrapped, rotation=0, ha='center', fontsize=TICK_FONT_SIZE)

# Symmetric margins
margin = spacing_factor * 0.5
plt.xlim(x_pos[0] - margin, x_pos[-1] + margin)

plt.ylabel("Step yield (%)", fontsize=AXIS_FONT_SIZE)
plt.grid(True, axis='y', linestyle='--', alpha=0.35)

# Set y-axis from 0 to 100% for yield
ax = plt.gca()
ax.tick_params(axis='y', labelsize=AXIS_FONT_SIZE)
ax.set_ylim(0, 105)
ax.set_yticks(np.arange(0, 101, 10))

plt.tight_layout()
step_yield_path = os.path.join(save_dir, 'Step_Yield_BarChart.png')
plt.savefig(step_yield_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved step yield plot to: {step_yield_path}")
plt.show()

# ============================
# PLOT 5: OVERLAY OF CUMULATIVE AND STEP YIELD
# ============================

plt.figure(figsize=(18, 6))
spacing_factor = 2.0
x_pos = np.arange(len(steps)) * spacing_factor

# Same label wrapping as other charts
labels_wrapped = [split_label_once(s) for s in steps]

# Plot step yield as bars first (so it's in the background)
# Wider bars (0.8) for better visibility
bar_width = 0.8
bar_color_overlay = '#E8D5F8'  # Light gray-blue for better contrast with purple line '#D0D0E0'
bars = plt.bar(x_pos, step_yield, width=bar_width, color=bar_color_overlay, 
               edgecolor="#5A2A4B", alpha=0.5, label='Step yield', align='center', zorder=2)# '#9090B0'

# Plot cumulative yield as a step function starting from the left edge of bars
# Shift x positions to left edge of bars for step plot
x_pos_step = x_pos - bar_width/2
# Extend to the right edge of the final bar
x_pos_step_extended = np.append(x_pos_step, x_pos[-1] + bar_width/2)
survival_extended = np.append(survival, survival[-1])
plt.step(x_pos_step_extended, survival_extended, where='post', color=curve_color, linewidth=3.0, 
         label='Cumulative yield', zorder=3)

# Set x-ticks with wrapped labels
plt.xticks(x_pos, labels_wrapped, rotation=0, ha='center', fontsize=TICK_FONT_SIZE)

# Start from left edge (no initial margin), keep right margin for symmetry
margin = spacing_factor * 0.5
plt.xlim(-bar_width/2, x_pos[-1] + margin)

plt.ylabel("Yield (%)", fontsize=AXIS_FONT_SIZE+2, labelpad=10)
# Add framealpha for transparent legend background
plt.legend(fontsize=LEGEND_FONT_SIZE, loc='upper right', framealpha=0.01)
plt.grid(True, axis='y', linestyle='--', alpha=0.35)

# Set y-axis from 0 to 115% to accommodate legend at top
ax = plt.gca()
ax.tick_params(axis='y', labelsize=AXIS_FONT_SIZE)
ax.tick_params(axis='x', labelsize=AXIS_FONT_SIZE)
ax.set_ylim(0, 115)
# Set y-axis ticks explicitly to exclude 115
ax.set_yticks(np.arange(0, 101, 10))

# Make the figure border (spines) thinner and less prominent
for spine in ax.spines.values():
    spine.set_linewidth(0.5)
    spine.set_color('#CCCCCC')
# Add padding to prevent x-axis label from overlapping with y-axis label
plt.subplots_adjust(bottom=0.15)


plt.tight_layout()
overlay_yield_path = os.path.join(save_dir, 'Overlay_Cumulative_Step_Yield.png')
plt.savefig(overlay_yield_path, dpi=300, bbox_inches='tight')
print(f"✓ Saved overlay yield plot to: {overlay_yield_path}")
# Also save as PDF
overlay_yield_pdf_path = os.path.join(save_dir, 'Overlay_Cumulative_Step_Yield.pdf')
plt.savefig(overlay_yield_pdf_path, bbox_inches='tight')
print(f"✓ Saved overlay yield plot (PDF) to: {overlay_yield_pdf_path}")
plt.show()


# %%
