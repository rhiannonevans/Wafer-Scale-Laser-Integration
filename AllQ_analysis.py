#!/usr/bin/env python3
"""
================================================================================
Script: AllQ_analysis.py
Author: sheri and co-pilot
Date: 2025-10-28

PURPOSE:
--------
This script creates a dual y-axis comparison plot of laser performance metrics
across multiple chip IDs. It analyzes Q-factor and FSR (Free Spectral Range)
measurements from both benchtop and on-chip laser configurations.

WORKFLOW:
---------
1. DIRECTORY SELECTION:
   - Prompts user to select a parent directory containing chip subfolders
   - Each subfolder represents a unique chip ID (subfolder name = chip ID)

2. DATA EXTRACTION:
   - Searches each subfolder for .mat files (saved by Benchtop_vs_OnChip script)
   - Extracts 8 key metrics per chip:
     * benchtop_avg_Q      (average Q-factor from benchtop measurement)
     * benchtop_std_Q      (standard deviation of benchtop Q)
     * benchtop_avg_FSR    (average FSR from benchtop, in pm)
     * benchtop_std_FSR    (standard deviation of benchtop FSR)
     * onchip_avg_Q        (average Q-factor from on-chip measurement)
     * onchip_std_Q        (standard deviation of on-chip Q)
     * onchip_avg_FSR      (average FSR from on-chip, in pm)
     * onchip_std_FSR      (standard deviation of on-chip FSR)

3. VISUALIZATION:
   - Creates a dual y-axis plot:
     LEFT Y-AXIS:  FSR values with error bars (benchtop vs on-chip)
     RIGHT Y-AXIS: Average Q values with error bars (benchtop vs on-chip)
     X-AXIS:       Chip IDs (subfolder names)
   
   - Uses different markers for clarity:
     * Circle (o):    FSR benchtop
     * Square (s):    FSR on-chip
     * Triangle up (^):   Q benchtop
     * Triangle down (v): Q on-chip

4. ERROR HANDLING:
   - Skips subfolders without .mat files
   - Skips .mat files that fail to load
   - Skips chips missing required variables
   - Uses np.nan for missing data points

OUTPUT:
-------
Interactive matplotlib plot showing comparative performance across all chips.

REQUIREMENTS:
-------------
- Parent directory structure:
  Parent_Folder/
  ├── ChipID_1/
  │   └── results.mat (containing benchtop_avg_Q, onchip_avg_Q, etc.)
  ├── ChipID_2/
  │   └── results.mat
  └── ...

- Each .mat file must contain variables saved by Benchtop_vs_OnChip_Resonance_Analysis.py
================================================================================
"""

import os
import sys
from pathlib import Path
import numpy as np
import scipy.io
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, MaxNLocator
import tkinter as tk
from tkinter import filedialog
from scipy import stats
import seaborn as sns


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
AXIS_FONT_SIZE = 30
TICK_FONT_SIZE = 28
LEGEND_FONT_SIZE = 18
TITLE_FONT_SIZE = 22

# Bar plot figure size (use same for Q and FSR)
BAR_FIGSIZE = (16, 8)

# Individual chip plot figure size (same height as beeswarm, but narrower width)
CHIP_FIGSIZE = (14, 8)

def ask_directory():
    """
    Prompt user to select directory using GUI file dialog.
    Falls back to text input if GUI fails.
    
    Returns:
    --------
    str : Path to selected directory
    """
    try:
        root = tk.Tk()
        root.withdraw()
        d = filedialog.askdirectory(
            title="Select parent directory containing chip subfolders"
        )
        root.destroy()
        if d:
            return d
    except Exception:
        pass
    # Fallback to command-line input
    return input("Enter parent directory path containing chip subfolders: ").strip()


def squeeze_val(v):
    """
    Convert MATLAB arrays to Python scalars/arrays.
    Handles nested arrays and single-element arrays.
    
    Parameters:
    -----------
    v : any
        Value from scipy.io.loadmat (typically numpy array)
    
    Returns:
    --------
    float or numpy.ndarray : Squeezed value
    """
    v = np.array(v)
    v = np.squeeze(v)  # Remove single-dimensional entries
    # Convert 0-D arrays (scalars) to float
    if v.shape == ():
        return float(v)
    return v


def extract_values_from_mat(mat):
    """
    Extract benchtop and on-chip Q and FSR values from .mat file.
    
    Searches for EXPLICIT variable names:
    - benchtop_avg_Q, benchtop_std_Q, benchtop_avg_FSR, benchtop_std_FSR
    - onchip_avg_Q, onchip_std_Q, onchip_avg_FSR, onchip_std_FSR
    - benchtop_Q_factors, benchtop_FSRs (raw arrays for beeswarm plots)
    - onchip_Q_factors, onchip_FSRs (raw arrays for beeswarm plots)
    
    Parameters:
    -----------
    mat : dict
        Dictionary returned by scipy.io.loadmat()
    
    Returns:
    --------
    dict or None:
        Dictionary with keys:
        - 'FSR_bench', 'FSR_bench_dev', 'FSR_onchip', 'FSR_onchip_dev'
        - 'Q_bench', 'Q_bench_dev', 'Q_onchip', 'Q_onchip_dev'
        - 'Q_bench_raw', 'Q_onchip_raw', 'FSR_bench_raw', 'FSR_onchip_raw' (arrays)
        Returns None if required variables not found.
    """
    out = {}
    
    # EXPLICIT SEARCH for benchtop variables
    out['FSR_bench'] = mat.get('benchtop_avg_FSR')
    out['FSR_bench_dev'] = mat.get('benchtop_std_FSR')
    out['Q_bench'] = mat.get('benchtop_avg_Q')
    out['Q_bench_dev'] = mat.get('benchtop_std_Q')
    
    # EXPLICIT SEARCH for on-chip variables
    out['FSR_onchip'] = mat.get('onchip_avg_FSR')
    out['FSR_onchip_dev'] = mat.get('onchip_std_FSR')
    out['Q_onchip'] = mat.get('onchip_avg_Q')
    out['Q_onchip_dev'] = mat.get('onchip_std_Q')
    
    # EXPLICIT SEARCH for raw arrays (for beeswarm plots)
    out['Q_bench_raw'] = mat.get('benchtop_Q_factors')
    out['Q_onchip_raw'] = mat.get('onchip_Q_factors')
    out['FSR_bench_raw'] = mat.get('benchtop_FSRs')
    out['FSR_onchip_raw'] = mat.get('onchip_FSRs')
    
    # Convert all values to scalars using squeeze_val (except raw arrays)
    for k, v in list(out.items()):
        if v is not None:
            try:
                if k.endswith('_raw'):
                    # For raw arrays, squeeze but keep as array
                    out[k] = np.squeeze(np.array(v)).flatten()
                else:
                    out[k] = squeeze_val(v)
            except Exception as e:
                print(f"Warning: Could not convert {k}: {e}")
                out[k] = None
    
    # Check if minimum required data is present
    required_keys = ['FSR_bench', 'FSR_onchip', 'Q_bench', 'Q_onchip']
    if all(out.get(k) is None for k in required_keys):
        return None
    
    # Replace None with np.nan for missing optional values (std deviations)
    for k in ['FSR_bench_dev', 'FSR_onchip_dev', 'Q_bench_dev', 'Q_onchip_dev']:
        if out.get(k) is None:
            out[k] = 0.0  # Zero error bar if std not available
    
    # Replace None with empty arrays for missing raw data
    for k in ['Q_bench_raw', 'Q_onchip_raw', 'FSR_bench_raw', 'FSR_onchip_raw']:
        if out.get(k) is None:
            out[k] = np.array([])
    
    return out


def find_mat_file_in_folder(folder):
    """
    Find the most recent .mat file in a folder.
    
    Parameters:
    -----------
    folder : Path
        Directory to search
    
    Returns:
    --------
    Path or None : Path to .mat file, or None if not found
    """
    mats = sorted(Path(folder).glob('*.mat'))
    if not mats:
        return None
    # Return most recent file (last in sorted list)
    return mats[-1]


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main function to:
    1. Prompt for parent directory
    2. Loop through chip subfolders
    3. Extract Q and FSR data from .mat files
    4. Generate dual y-axis comparison plot
    """
    
    # Step 1: Get parent directory from user
    parent = ask_directory()
    if not parent:
        print("No directory provided. Exiting.")
        return

    parent = Path(parent)
    if not parent.is_dir():
        print("Provided path is not a directory. Exiting.")
        return

    print(f"\nScanning directory: {parent}")
    print("=" * 80)
    
    # Initialize data storage lists
    chip_names = []
    fsr_bench = []
    fsr_bench_dev = []
    fsr_on = []
    fsr_on_dev = []
    q_bench = []
    q_bench_dev = []
    q_on = []
    q_on_dev = []
    
    # Storage for raw arrays (for beeswarm plots)
    q_bench_raw_list = []
    q_on_raw_list = []
    fsr_bench_raw_list = []
    fsr_on_raw_list = []

    # For normalized power vs wavelength plotting
    wb_bench_list = []            # wavelengthBenchtopLimited per chip
    pb_bench_list = []            # powerBenchtopNormalized per chip
    w_onchip_list = []            # wavelengthOnChip per chip
    p_onchip_list = []            # powerFilteredNormalized per chip

    # Step 2: Loop through all subfolders (each = one chip)
    for sub in sorted(parent.iterdir()):
        if not sub.is_dir():
            continue
        
        # Find .mat file in this chip's folder
        matpath = find_mat_file_in_folder(sub)
        if matpath is None:
            print(f"⚠ Skipping {sub.name}: no .mat file found")
            continue
        
        # Try to load .mat file
        try:
            mat = scipy.io.loadmat(str(matpath))
        except Exception as e:
            print(f"⚠ Skipping {sub.name}: failed to load {matpath.name} ({e})")
            continue

        # Extract Q and FSR values
        vals = extract_values_from_mat(mat)
        if vals is None:
            print(f"⚠ Skipping {sub.name}: required variables not found in {matpath.name}")
            print(f"  Available keys: {', '.join([k for k in mat.keys() if not k.startswith('__')])}")
            continue

        # Store extracted values
        chip_names.append(sub.name)
        fsr_bench.append(vals.get('FSR_bench', np.nan))
        fsr_bench_dev.append(vals.get('FSR_bench_dev', 0.0))
        fsr_on.append(vals.get('FSR_onchip', np.nan))
        fsr_on_dev.append(vals.get('FSR_onchip_dev', 0.0))
        q_bench.append(vals.get('Q_bench', np.nan))
        q_bench_dev.append(vals.get('Q_bench_dev', 0.0))
        q_on.append(vals.get('Q_onchip', np.nan))
        q_on_dev.append(vals.get('Q_onchip_dev', 0.0))
        
        # Store raw arrays for beeswarm plots
        q_bench_raw_list.append(vals.get('Q_bench_raw', np.array([])))
        q_on_raw_list.append(vals.get('Q_onchip_raw', np.array([])))
        fsr_bench_raw_list.append(vals.get('FSR_bench_raw', np.array([])))
        fsr_on_raw_list.append(vals.get('FSR_onchip_raw', np.array([])))
        
        print(f"✓ Loaded {sub.name}: Q_bench={vals.get('Q_bench', 'N/A'):.0f}, "
              f"Q_onchip={vals.get('Q_onchip', 'N/A'):.0f}, "
              f"FSR_bench={vals.get('FSR_bench', 'N/A'):.1f}pm, "
              f"FSR_onchip={vals.get('FSR_onchip', 'N/A'):.1f}pm")

        # Attempt to extract wavelength/power arrays for normalized-power plotting
        # Variables: wavelengthOnChip, wavelengthBenchtopLimited, powerFilteredNormalized, powerBenchtopNormalized
        def _safe_get_array(mat, key):
            if key in mat:
                try:
                    arr = np.squeeze(np.array(mat[key]))
                    # Ensure 1D numpy array
                    if np.ndim(arr) == 0:
                        return np.array([arr])
                    return arr
                except Exception:
                    return None
            return None

        # load mat file for these arrays if present
        try:
            mat_for_arrays = scipy.io.loadmat(str(matpath))
        except Exception:
            mat_for_arrays = {}

        wb = _safe_get_array(mat_for_arrays, 'wavelengthBenchtopLimited')
        pb = _safe_get_array(mat_for_arrays, 'powerBenchtopNormalized')
        wo = _safe_get_array(mat_for_arrays, 'wavelengthOnChip')
        po = _safe_get_array(mat_for_arrays, 'powerFilteredNormalized')

        wb_bench_list.append(wb)
        pb_bench_list.append(pb)
        w_onchip_list.append(wo)
        p_onchip_list.append(po)

    # Check if any valid data was found
    if not chip_names:
        print("\n❌ No valid chip data found. Exiting.")
        return

    print(f"\n✓ Successfully loaded {len(chip_names)} chips")
    print("=" * 80)
    

  # Replace the bar plot sections with these updated versions:

    # =============================================================================
    # CREATE SEPARATE BAR PLOTS - Q-FACTORS AND FSR COMPARISON (GRAYSCALE)
    # =============================================================================
    print("\n--- Creating Separate Bar Plot Comparisons ---")
    
    # Convert lists to numpy arrays for easier handling
    fsr_bench_arr = np.array(fsr_bench)
    fsr_bench_dev_arr = np.array(fsr_bench_dev)
    fsr_on_arr = np.array(fsr_on)
    fsr_on_dev_arr = np.array(fsr_on_dev)
    q_bench_arr = np.array(q_bench)
    q_bench_dev_arr = np.array(q_bench_dev)
    q_on_arr = np.array(q_on)
    q_on_dev_arr = np.array(q_on_dev)
    
    # =============================================================================
    # STATISTICAL SIGNIFICANCE TESTING
    # =============================================================================
    print("\n--- Statistical Significance Analysis ---")
    
    # Remove NaN values for testing
    q_valid_mask = ~(np.isnan(q_bench_arr) | np.isnan(q_on_arr))
    fsr_valid_mask = ~(np.isnan(fsr_bench_arr) | np.isnan(fsr_on_arr))
    
    q_bench_valid = q_bench_arr[q_valid_mask]
    q_on_valid = q_on_arr[q_valid_mask]
    fsr_bench_valid = fsr_bench_arr[fsr_valid_mask]
    fsr_on_valid = fsr_on_arr[fsr_valid_mask]
    
    # Perform Mann-Whitney U-test (independent samples, non-parametric)
    if len(q_bench_valid) >= 2 and len(q_on_valid) >= 2:
        stat_q, p_q = stats.mannwhitneyu(q_bench_valid, q_on_valid, alternative='two-sided')
        print(f"\nQ-Factor Comparison:")
        print(f"  Benchtop: n={len(q_bench_valid)} measurements")
        print(f"  On-chip: n={len(q_on_valid)} measurements")
        print(f"  Mann-Whitney U-statistic: {stat_q:.3f}")
        print(f"  p-value: {p_q:.4f}")
        if p_q < 0.001:
            sig_q = "highly significant (p < 0.001)"
        elif p_q < 0.01:
            sig_q = "very significant (p < 0.01)"
        elif p_q < 0.05:
            sig_q = "significant (p < 0.05)"
        else:
            sig_q = "not significant (p ≥ 0.05)"
        print(f"  Result: Difference is {sig_q}")
        print(f"  Median Q (benchtop): {np.median(q_bench_valid):.0f}")
        print(f"  Median Q (on-chip): {np.median(q_on_valid):.0f}")
    else:
        p_q = None
        print(f"\nQ-Factor: Insufficient data for significance test")
    
    if len(fsr_bench_valid) >= 2 and len(fsr_on_valid) >= 2:
        stat_fsr, p_fsr = stats.mannwhitneyu(fsr_bench_valid, fsr_on_valid, alternative='two-sided')
        print(f"\nFSR Comparison:")
        print(f"  Benchtop: n={len(fsr_bench_valid)} measurements")
        print(f"  On-chip: n={len(fsr_on_valid)} measurements")
        print(f"  Mann-Whitney U-statistic: {stat_fsr:.3f}")
        print(f"  p-value: {p_fsr:.4f}")
        if p_fsr < 0.001:
            sig_fsr = "highly significant (p < 0.001)"
        elif p_fsr < 0.01:
            sig_fsr = "very significant (p < 0.01)"
        elif p_fsr < 0.05:
            sig_fsr = "significant (p < 0.05)"
        else:
            sig_fsr = "not significant (p ≥ 0.05)"
        print(f"  Result: Difference is {sig_fsr}")
        print(f"  Median FSR (benchtop): {np.median(fsr_bench_valid):.1f} pm")
        print(f"  Median FSR (on-chip): {np.median(fsr_on_valid):.1f} pm")
    else:
        p_fsr = None
        print(f"\nFSR: Insufficient data for significance test")
    
    print("=" * 80)
    
    # Create summary text file
    summary_lines = []
    summary_lines.append("="*70)
    summary_lines.append("LASER PERFORMANCE COMPARISON SUMMARY")
    summary_lines.append("Benchtop vs On-Chip Measurements")
    summary_lines.append("="*70)
    summary_lines.append("")
    summary_lines.append(f"Total chips analyzed: {len(chip_names)}")
    summary_lines.append(f"Chip IDs: {', '.join(chip_names)}")
    summary_lines.append("")
    summary_lines.append("-" * 70)
    summary_lines.append("Q-FACTOR ANALYSIS")
    summary_lines.append("-" * 70)
    if len(q_bench_valid) >= 2 and len(q_on_valid) >= 2:
        summary_lines.append(f"Benchtop measurements: n={len(q_bench_valid)}")
        summary_lines.append(f"  Mean Q: {np.mean(q_bench_valid):.0f}")
        summary_lines.append(f"  Median Q: {np.median(q_bench_valid):.0f}")
        summary_lines.append(f"  Std Dev: {np.std(q_bench_valid):.0f}")
        summary_lines.append("")
        summary_lines.append(f"On-chip measurements: n={len(q_on_valid)}")
        summary_lines.append(f"  Mean Q: {np.mean(q_on_valid):.0f}")
        summary_lines.append(f"  Median Q: {np.median(q_on_valid):.0f}")
        summary_lines.append(f"  Std Dev: {np.std(q_on_valid):.0f}")
        summary_lines.append("")
        summary_lines.append("Statistical Comparison (Mann-Whitney U-test):")
        summary_lines.append(f"  U-statistic: {stat_q:.3f}")
        summary_lines.append(f"  p-value: {p_q:.4f}")
        summary_lines.append(f"  Result: {sig_q}")
    else:
        summary_lines.append("Insufficient data for Q-factor analysis")
    summary_lines.append("")
    summary_lines.append("-" * 70)
    summary_lines.append("FSR ANALYSIS")
    summary_lines.append("-" * 70)
    if len(fsr_bench_valid) >= 2 and len(fsr_on_valid) >= 2:
        summary_lines.append(f"Benchtop measurements: n={len(fsr_bench_valid)}")
        summary_lines.append(f"  Mean FSR: {np.mean(fsr_bench_valid):.2f} pm")
        summary_lines.append(f"  Median FSR: {np.median(fsr_bench_valid):.2f} pm")
        summary_lines.append(f"  Std Dev: {np.std(fsr_bench_valid):.2f} pm")
        summary_lines.append("")
        summary_lines.append(f"On-chip measurements: n={len(fsr_on_valid)}")
        summary_lines.append(f"  Mean FSR: {np.mean(fsr_on_valid):.2f} pm")
        summary_lines.append(f"  Median FSR: {np.median(fsr_on_valid):.2f} pm")
        summary_lines.append(f"  Std Dev: {np.std(fsr_on_valid):.2f} pm")
        summary_lines.append("")
        summary_lines.append("Statistical Comparison (Mann-Whitney U-test):")
        summary_lines.append(f"  U-statistic: {stat_fsr:.3f}")
        summary_lines.append(f"  p-value: {p_fsr:.4f}")
        summary_lines.append(f"  Result: {sig_fsr}")
    else:
        summary_lines.append("Insufficient data for FSR analysis")
    summary_lines.append("")
    summary_lines.append("="*70)
    
    # Save summary to text file
    summary_file = parent / "Chip_Comparison_Summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(summary_lines))
    print(f"\n✓ Summary statistics saved to: {summary_file}")
    
    # Inferno colormap colors (avoiding light colors)
    cmap_inferno = plt.get_cmap('inferno')
    # Use 0.2 and 0.65 positions to avoid extremely light colors
    benchtop_color = cmap_inferno(0.2)   # darker inferno color for benchtop
    onchip_color = cmap_inferno(0.65)    # mid-range inferno color for on-chip
         # light purple for step-loss bars
         


    
    # =============================================================================
    # Q-FACTOR BAR PLOT (SEPARATE FIGURE)
    # =============================================================================
    fig_q, ax_q_bar = plt.subplots(1, 1, figsize=BAR_FIGSIZE)
    
    x_pos = np.arange(len(chip_names))
    width = 0.35  # Width of bars
    
    # Plot Q-factor bars
    bars_q1 = ax_q_bar.bar(x_pos - width/2, q_bench_arr, width, 
                           color=benchtop_color, 
                           alpha=0.8, 
                           label='Benchtop Laser')
    
    bars_q2 = ax_q_bar.bar(x_pos + width/2, q_on_arr, width,
                           color=onchip_color, 
                           alpha=0.8,
                           label='On-Chip Laser')
    
    # Add error bars separately for Q-factor
    ax_q_bar.errorbar(x_pos - width/2, q_bench_arr, 
                      yerr=q_bench_dev_arr, 
                      fmt='none', 
                      capsize=8,
                      capthick=1.5,
                      color='black',
                      linewidth=1)
    
    ax_q_bar.errorbar(x_pos + width/2, q_on_arr, 
                      yerr=q_on_dev_arr, 
                      fmt='none', 
                      capsize=8,
                      capthick=1.5,
                      color='black',
                      linewidth=1)
    
    # Customize Q-factor bar plot with global fonts
    ax_q_bar.set_xlabel('Chip ID', fontsize=AXIS_FONT_SIZE, labelpad=15)
    ax_q_bar.set_ylabel('Average Q-Factor', fontsize=AXIS_FONT_SIZE, labelpad=15)
    
    # Add p-value to title if available
    if p_q is not None:
        if p_q < 0.001:
            p_text = "p < 0.001"
        else:
            p_text = f"p = {p_q:.4f}"
        title_q = f'Q-Factor Comparison: Benchtop vs On-Chip Lasers\n({p_text})'
    else:
        title_q = 'Q-Factor Comparison: Benchtop vs On-Chip Lasers'
    
    #ax_q_bar.set_title(title_q, fontsize=TITLE_FONT_SIZE, fontweight='bold', pad=25)
    ax_q_bar.set_xticks(x_pos)
    ax_q_bar.set_xticklabels(chip_names, rotation=0, ha='center', fontsize=TICK_FONT_SIZE)
    ax_q_bar.legend(fontsize=LEGEND_FONT_SIZE, loc='upper right')
    ax_q_bar.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax_q_bar.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE, width=2, length=8)
    
    # Calculate max height for label positioning
    max_q_height = max(np.nanmax(q_bench_arr + q_bench_dev_arr), 
                       np.nanmax(q_on_arr + q_on_dev_arr))
    
    # # Add value labels on Q-factor bars horizontally with staggered heights
    # for i, (bar, value, std) in enumerate(zip(bars_q1, q_bench_arr, q_bench_dev_arr)):
    #     if not np.isnan(value) and value > 0:
    #         height = bar.get_height()
    #         # Position benchtop labels lower
    #         label_y = height + std + max_q_height * 0.15
    #         ax_q_bar.text(bar.get_x() + bar.get_width()/2., label_y,
    #                      f'{value:.0f}±{std:.0f}',
    #                      ha='center', va='bottom', fontsize=LEGEND_FONT_SIZE-2,
    #                      bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # for i, (bar, value, std) in enumerate(zip(bars_q2, q_on_arr, q_on_dev_arr)):
    #     if not np.isnan(value) and value > 0:
    #         height = bar.get_height()
    #         # Position on-chip labels higher to create vertical separation
    #         label_y = height + std + max_q_height * 0.05
    #         ax_q_bar.text(bar.get_x() + bar.get_width()/2., label_y,
    #                      f'{value:.0f}±{std:.0f}',
    #                      ha='center', va='bottom', fontsize=LEGEND_FONT_SIZE-2,
    #                      bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # # Adjust y-axis limits to accommodate labels
    # ax_q_bar.set_ylim(0, max_q_height * 1.35)
    
    # # Adjust layout and save Q-factor plot
    # plt.tight_layout()
    # plt.subplots_adjust(bottom=0.15)  # Extra space for rotated labels
    
    # Save Q-factor bar plot figure
    output_file_q = parent / "Chip_Comparison_Q_BarPlot.png"
    plt.savefig(output_file_q, dpi=300, bbox_inches='tight')
    print(f"✓ Q-factor bar plot saved to: {output_file_q}")
    
    # Show Q-factor plot
    plt.show()
    
    
    
    # =============================================================================
    # FSR BAR PLOT (SEPARATE FIGURE)
    # =============================================================================
    fig_fsr, ax_fsr_bar = plt.subplots(1, 1, figsize=BAR_FIGSIZE)  # Larger figure size
    
    # Plot FSR bars
    bars_fsr1 = ax_fsr_bar.bar(x_pos - width/2, fsr_bench_arr, width,
                               color=benchtop_color,
                               alpha=0.8,
                               label='Benchtop Laser')
    
    bars_fsr2 = ax_fsr_bar.bar(x_pos + width/2, fsr_on_arr, width,
                               color=onchip_color,
                               alpha=0.8,
                               label='On-Chip Laser')
    
    # Add error bars separately for FSR
    ax_fsr_bar.errorbar(x_pos - width/2, fsr_bench_arr, 
                        yerr=fsr_bench_dev_arr, 
                        fmt='none', 
                        capsize=8,
                        capthick=1.5,
                        color='black',
                        linewidth=1)
    
    ax_fsr_bar.errorbar(x_pos + width/2, fsr_on_arr, 
                        yerr=fsr_on_dev_arr, 
                        fmt='none', 
                        capsize=8,
                        capthick=1.5,
                        color='black',
                        linewidth=1)
    
    # Customize FSR bar plot with global fonts
    ax_fsr_bar.set_xlabel('Chip ID', fontsize=AXIS_FONT_SIZE, labelpad=15)
    ax_fsr_bar.set_ylabel('Average FSR (pm)', fontsize=AXIS_FONT_SIZE, labelpad=15)
    
    # Add p-value to title if available
    if p_fsr is not None:
        if p_fsr < 0.001:
            p_text = "p < 0.001"
        else:
            p_text = f"p = {p_fsr:.4f}"
        title_fsr = f'Free Spectral Range (FSR) Comparison: Benchtop vs On-Chip Lasers\n({p_text})'
    else:
        title_fsr = 'Free Spectral Range (FSR) Comparison: Benchtop vs On-Chip Lasers'
    
    #ax_fsr_bar.set_title(title_fsr, fontsize=TITLE_FONT_SIZE, fontweight='bold', pad=25)
    ax_fsr_bar.set_xticks(x_pos)
    ax_fsr_bar.set_xticklabels(chip_names, rotation=0, ha='center', fontsize=TICK_FONT_SIZE)
    #ax_fsr_bar.legend(fontsize=LEGEND_FONT_SIZE, loc='upper right')
    ax_fsr_bar.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax_fsr_bar.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE, width=2, length=8)
    
    # Calculate max height for label positioning
    max_fsr_height = max(np.nanmax(fsr_bench_arr + fsr_bench_dev_arr), 
                         np.nanmax(fsr_on_arr + fsr_on_dev_arr))
    
    # # Add value labels on FSR bars horizontally
    # for i, (bar, value, std) in enumerate(zip(bars_fsr1, fsr_bench_arr, fsr_bench_dev_arr)):
    #     if not np.isnan(value) and value > 0:
    #         height = bar.get_height()
    #         # Position labels higher to avoid overlap
    #         label_y = height + std + max_fsr_height * 0.005
    #         ax_fsr_bar.text(bar.get_x() + bar.get_width()/2., label_y,
    #                        f'{value:.1f}±{std:.1f}',
    #                        ha='center', va='bottom', fontsize=LEGEND_FONT_SIZE,
    #                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # for i, (bar, value, std) in enumerate(zip(bars_fsr2, fsr_on_arr, fsr_on_dev_arr)):
    #     if not np.isnan(value) and value > 0:
    #         height = bar.get_height()
    #         # Position labels higher to avoid overlap
    #         label_y = height + std + max_fsr_height * 0.05
    #         ax_fsr_bar.text(bar.get_x() + bar.get_width()/2., label_y,
    #                        f'{value:.1f}±{std:.1f}',
    #                        ha='center', va='bottom', fontsize=LEGEND_FONT_SIZE,
    #                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # # Adjust y-axis limits to accommodate labels
    # ax_fsr_bar.set_ylim(0, max_fsr_height * 1.25)
    
    # Adjust layout and save FSR plot
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)  # Extra space for rotated labels
    
    # Save FSR bar plot figure
    output_file_fsr = parent / "Chip_Comparison_FSR_BarPlot.png"
    plt.savefig(output_file_fsr, dpi=300, bbox_inches='tight')
    print(f"✓ FSR bar plot saved to: {output_file_fsr}")
    
    # Show FSR plot
    plt.show()

    # =============================================================================
    # BEESWARM PLOTS - Q-FACTORS AND FSR COMPARISON
    # =============================================================================
    print("\n--- Creating Beeswarm Plot Comparisons ---")
    
    # =============================================================================
    # Q-FACTOR BEESWARM PLOT (SEPARATE FIGURE)
    # =============================================================================
    fig_q_swarm, ax_q_swarm = plt.subplots(1, 1, figsize=BAR_FIGSIZE)
    
    # Prepare data for beeswarm plot
    q_swarm_data = []
    q_swarm_labels = []
    q_swarm_colors = []
    q_swarm_positions = []
    
    # For each chip, add benchtop and on-chip data
    for i, name in enumerate(chip_names):
        base_pos = i * 2  # Space out chip groups
        
        # Benchtop data
        q_bench_vals = q_bench_raw_list[i]
        if len(q_bench_vals) > 0:
            for val in q_bench_vals:
                q_swarm_data.append(val)
                q_swarm_labels.append(f"{name}\nBenchtop")
                q_swarm_colors.append(benchtop_color)
                q_swarm_positions.append(base_pos - 0.3)
        
        # On-chip data
        q_on_vals = q_on_raw_list[i]
        if len(q_on_vals) > 0:
            for val in q_on_vals:
                q_swarm_data.append(val)
                q_swarm_labels.append(f"{name}\nOn-Chip")
                q_swarm_colors.append(onchip_color)
                q_swarm_positions.append(base_pos + 0.3)
    
    # Create beeswarm plot using seaborn
    if len(q_swarm_data) > 0:
        import pandas as pd
        df_q = pd.DataFrame({
            'Q-Factor': q_swarm_data,
            'Group': q_swarm_labels,
            'Position': q_swarm_positions,
            'Color': q_swarm_colors
        })
        
        # Plot swarm for each chip
        x_pos = np.arange(len(chip_names)) * 2  # Spacing between chips to match bar plots
        width = 0.5  # Increased spacing between benchtop and on-chip
        
        for i, name in enumerate(chip_names):
            # Benchtop swarm at x_pos[i] - width/2
            q_bench_vals = q_bench_raw_list[i]
            if len(q_bench_vals) > 0:
                x_bench_pos = x_pos[i] - width/2
                # Use adaptive jitter based on number of points to avoid overlap
                np.random.seed(42 + i)  # Reproducible jitter
                max_jitter = min(0.25, 0.08 * np.sqrt(len(q_bench_vals)))  # Increased jitter range
                x_jitter = np.random.uniform(-max_jitter, max_jitter, len(q_bench_vals))
                x_positions = x_bench_pos + x_jitter
                # Plot individual points with larger size
                ax_q_swarm.scatter(x_positions, q_bench_vals,
                                 color=benchtop_color, alpha=0.7, s=350, zorder=5)
                # Add mean ± std error bar
                mean_val = np.mean(q_bench_vals)
                std_val = np.std(q_bench_vals, ddof=1)
                ax_q_swarm.errorbar(x_bench_pos, mean_val, yerr=std_val,
                                  fmt='D', color='black', alpha=0.8, markersize=6,
                                  capsize=8, capthick=2, linewidth=2,
                                  markeredgewidth=1.5, markerfacecolor='white', zorder=10)
            
            # On-chip swarm at x_pos[i] + width/2
            q_on_vals = q_on_raw_list[i]
            if len(q_on_vals) > 0:
                x_on_pos = x_pos[i] + width/2
                # Use adaptive jitter based on number of points to avoid overlap
                np.random.seed(100 + i)  # Reproducible jitter
                max_jitter = min(0.25, 0.08 * np.sqrt(len(q_on_vals)))  # Increased jitter range
                x_jitter = np.random.uniform(-max_jitter, max_jitter, len(q_on_vals))
                x_positions = x_on_pos + x_jitter
                # Plot individual points with larger size
                ax_q_swarm.scatter(x_positions, q_on_vals,
                                 color=onchip_color, alpha=0.7, s=350, zorder=5)
                # Add mean ± std error bar
                mean_val = np.mean(q_on_vals)
                std_val = np.std(q_on_vals, ddof=1)
                ax_q_swarm.errorbar(x_on_pos, mean_val, yerr=std_val,
                                  fmt='D', color='black', alpha=0.8, markersize=6,
                                  capsize=8, capthick=2, linewidth=2,
                                  markeredgewidth=1.5, markerfacecolor='white', zorder=10)
        
        # Customize Q-factor beeswarm plot
        ax_q_swarm.set_xlabel('Chip ID', fontsize=AXIS_FONT_SIZE, labelpad=15)
        ax_q_swarm.set_ylabel('Q-Factor', fontsize=AXIS_FONT_SIZE, labelpad=15)
        
        # Set x-ticks to chip names (same as bar plots)
        ax_q_swarm.set_xticks(x_pos)
        ax_q_swarm.set_xticklabels(chip_names, rotation=0, ha='center', fontsize=TICK_FONT_SIZE)
        
        ax_q_swarm.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax_q_swarm.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE, width=2, length=8)
        
        # Remove top and right spines
        ax_q_swarm.spines['top'].set_visible(False)
        ax_q_swarm.spines['right'].set_visible(False)
        
        # Add legend
        from matplotlib.patches import Patch
        # legend_elements = [
        #     Patch(facecolor=benchtop_color, alpha=0.8, label='Benchtop Laser'),
        #     Patch(facecolor=onchip_color, alpha=0.8, label='On-Chip Laser'),
        #     plt.Line2D([0], [0], marker='D', color='black', linestyle='None',
        #               markersize=6, markerfacecolor='white', markeredgewidth=1.5,
        #               label='Mean ± Std Dev')
        # ]
        # ax_q_swarm.legend(handles=legend_elements, fontsize=LEGEND_FONT_SIZE, loc='upper right')
        
        # Save Q-factor beeswarm plot
        plt.tight_layout()
        output_file_q_swarm = parent / "Chip_Comparison_Q_Beeswarm.png"
        plt.savefig(output_file_q_swarm, dpi=300, bbox_inches='tight')
        print(f"✓ Q-factor beeswarm plot saved to: {output_file_q_swarm}")
        plt.show()
    else:
        print("⚠ No Q-factor raw data available for beeswarm plot")
    
    # =============================================================================
    # FSR BEESWARM PLOT (SEPARATE FIGURE)
    # =============================================================================
    fig_fsr_swarm, ax_fsr_swarm = plt.subplots(1, 1, figsize=BAR_FIGSIZE)
    
    # Prepare data for FSR beeswarm plot
    fsr_swarm_data = []
    fsr_swarm_labels = []
    fsr_swarm_colors = []
    fsr_swarm_positions = []
    
    # For each chip, add benchtop and on-chip data
    for i, name in enumerate(chip_names):
        base_pos = i * 2  # Space out chip groups
        
        # Benchtop data
        fsr_bench_vals = fsr_bench_raw_list[i]
        if len(fsr_bench_vals) > 0:
            for val in fsr_bench_vals:
                fsr_swarm_data.append(val)
                fsr_swarm_labels.append(f"{name}\nBenchtop")
                fsr_swarm_colors.append(benchtop_color)
                fsr_swarm_positions.append(base_pos - 0.3)
        
        # On-chip data
        fsr_on_vals = fsr_on_raw_list[i]
        if len(fsr_on_vals) > 0:
            for val in fsr_on_vals:
                fsr_swarm_data.append(val)
                fsr_swarm_labels.append(f"{name}\nOn-Chip")
                fsr_swarm_colors.append(onchip_color)
                fsr_swarm_positions.append(base_pos + 0.3)
    
    # Create beeswarm plot using seaborn
    if len(fsr_swarm_data) > 0:
        import pandas as pd
        df_fsr = pd.DataFrame({
            'FSR': fsr_swarm_data,
            'Group': fsr_swarm_labels,
            'Position': fsr_swarm_positions,
            'Color': fsr_swarm_colors
        })
        
        # Plot swarm for each chip
        x_pos = np.arange(len(chip_names)) * 2  # Spacing between chips to match bar plots
        width = 0.5  # Increased spacing between benchtop and on-chip
        
        for i, name in enumerate(chip_names):
            # Benchtop swarm at x_pos[i] - width/2
            fsr_bench_vals = fsr_bench_raw_list[i]
            if len(fsr_bench_vals) > 0:
                x_bench_pos = x_pos[i] - width/2
                # Use adaptive jitter based on number of points to avoid overlap
                np.random.seed(42 + i)  # Reproducible jitter
                max_jitter = min(0.25, 0.08 * np.sqrt(len(fsr_bench_vals)))  # Increased jitter range
                x_jitter = np.random.uniform(-max_jitter, max_jitter, len(fsr_bench_vals))
                x_positions = x_bench_pos + x_jitter
                # Plot individual points with larger size
                ax_fsr_swarm.scatter(x_positions, fsr_bench_vals,
                                   color=benchtop_color, alpha=0.7, s=350, zorder=5)
                # Add mean ± std error bar
                mean_val = np.mean(fsr_bench_vals)
                std_val = np.std(fsr_bench_vals, ddof=1)
                ax_fsr_swarm.errorbar(x_bench_pos, mean_val, yerr=std_val,
                                    fmt='D', color='black', alpha=0.8, markersize=6,
                                    capsize=8, capthick=2, linewidth=2,
                                    markeredgewidth=1.5, markerfacecolor='white', zorder=10)
            
            # On-chip swarm at x_pos[i] + width/2
            fsr_on_vals = fsr_on_raw_list[i]
            if len(fsr_on_vals) > 0:
                x_on_pos = x_pos[i] + width/2
                # Use adaptive jitter based on number of points to avoid overlap
                np.random.seed(100 + i)  # Reproducible jitter
                max_jitter = min(0.25, 0.08 * np.sqrt(len(fsr_on_vals)))  # Increased jitter range
                x_jitter = np.random.uniform(-max_jitter, max_jitter, len(fsr_on_vals))
                x_positions = x_on_pos + x_jitter
                # Plot individual points with larger size
                ax_fsr_swarm.scatter(x_positions, fsr_on_vals,
                                   color=onchip_color, alpha=0.7, s=350, zorder=5)
                # Add mean ± std error bar
                mean_val = np.mean(fsr_on_vals)
                std_val = np.std(fsr_on_vals, ddof=1)
                ax_fsr_swarm.errorbar(x_on_pos, mean_val, yerr=std_val,
                                    fmt='D', color='black', alpha=0.8, markersize=6,
                                    capsize=8, capthick=2, linewidth=2,
                                    markeredgewidth=1.5, markerfacecolor='white', zorder=10)
        
        # Customize FSR beeswarm plot
        ax_fsr_swarm.set_xlabel('Chip ID', fontsize=AXIS_FONT_SIZE, labelpad=15)
        ax_fsr_swarm.set_ylabel('FSR (pm)', fontsize=AXIS_FONT_SIZE, labelpad=15)
        
        # Set x-ticks to chip names (same as bar plots)
        ax_fsr_swarm.set_xticks(x_pos)
        ax_fsr_swarm.set_xticklabels(chip_names, rotation=0, ha='center', fontsize=TICK_FONT_SIZE)
        
        ax_fsr_swarm.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax_fsr_swarm.tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE, width=2, length=8)
        
        # Remove top and right spines
        ax_fsr_swarm.spines['top'].set_visible(False)
        ax_fsr_swarm.spines['right'].set_visible(False)
        
        # Add legend
        from matplotlib.patches import Patch
        # legend_elements = [
        #     Patch(facecolor=benchtop_color, alpha=0.8, label='Benchtop Laser'),
        #     Patch(facecolor=onchip_color, alpha=0.8, label='On-Chip Laser'),
        #     plt.Line2D([0], [0], marker='D', color='black', linestyle='None',
        #               markersize=6, markerfacecolor='white', markeredgewidth=1.5,
        #               label='Mean ± Std Dev')
        # ]
        # ax_fsr_swarm.legend(handles=legend_elements, fontsize=LEGEND_FONT_SIZE, loc='upper right')
        
        # Save FSR beeswarm plot
        plt.tight_layout()
        output_file_fsr_swarm = parent / "Chip_Comparison_FSR_Beeswarm.png"
        plt.savefig(output_file_fsr_swarm, dpi=300, bbox_inches='tight')
        print(f"✓ FSR beeswarm plot saved to: {output_file_fsr_swarm}")
        plt.show()
    else:
        print("⚠ No FSR raw data available for beeswarm plot")

    # =============================================================================
    # PER-CHIP OVERLAYED NORMALIZED POWER vs WAVELENGTH PLOTS
    # For each chip, overlay benchtop and on-chip normalized power (if present)
    # using the grayscale colors defined above (`benchtop_color`, `onchip_color`).
    # =============================================================================
    print('\n--- Creating Per-Chip Overlayed Normalized Power Plots ---')

    for i, name in enumerate(chip_names):
        wb = wb_bench_list[i]
        pb = pb_bench_list[i]
        wo = w_onchip_list[i]
        po = p_onchip_list[i]

        # Skip if neither dataset is available
        if (wb is None or pb is None) and (wo is None or po is None):
            print(f"⚠ Skipping overlay for {name}: no normalized-power arrays found")
            continue

        fig_c, ax_c = plt.subplots(figsize=CHIP_FIGSIZE)

        plotted = False
        if wb is not None and pb is not None:
            try:
                ax_c.plot(wb, pb, linestyle='-', color=benchtop_color,
                          label='Benchtop (normalized)')
                plotted = True
            except Exception:
                print(f"⚠ Failed plotting benchtop data for {name}")

        if wo is not None and po is not None:
            try:
                ax_c.plot(wo, po, linestyle='-', color=onchip_color,
                          label='On-Chip (normalized)')
                plotted = True
            except Exception:
                print(f"⚠ Failed plotting on-chip data for {name}")

        if not plotted:
            plt.close(fig_c)
            print(f"⚠ No plottable normalized-power data for {name}")
            continue

        ax_c.set_xlabel('Wavelength (nm)', fontsize=AXIS_FONT_SIZE, labelpad=15)
        ax_c.set_ylabel('Normalized Power', fontsize=AXIS_FONT_SIZE, labelpad=15)
        #ax_c.set_title(f'{name}: Benchtop vs On-Chip Normalized Power', fontsize=TITLE_FONT_SIZE)
        ax_c.grid(True, alpha=0.25)
        ax_c.tick_params(axis='both', labelsize=TICK_FONT_SIZE)
       # ax_c.legend(['Benchtop', 'On-Chip'], fontsize=LEGEND_FONT_SIZE, loc='best')

        # Format x-axis to show full wavelength numbers (no offset) and reduce ticks
        try:
            ax_c.xaxis.set_major_locator(MaxNLocator(nbins=6))
            ax_c.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            ax_c.ticklabel_format(style='plain', axis='x', useOffset=False)
        except Exception:
            pass
        ax_c.set_xlim(1330.05,1330.45) # Example limits; adjust as needed

        save_name = parent / f"{name}_NormalizedPower_overlay.png"
        fig_c.tight_layout()
        fig_c.savefig(save_name, dpi=300, bbox_inches='tight')
        plt.close(fig_c)
        print(f'✓ Saved overlay plot for {name}: {save_name}')

    # Show the original dual y-axis plot (if interactive session)
    plt.show()
    


if __name__ == "__main__":
    main()