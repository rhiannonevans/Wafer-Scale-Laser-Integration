"""Compare RA-style peak drifts between benchtop and on-chip analyses.

This script loads the RA_result peak_shift.mat files produced by plot_spectrograms.py
for a benchtop dataset and an on-chip dataset, then overlays the cumulative and
per-step drift curves for convenient visual comparison.

The script defaults to the shared RA_result directory at
    C:/Users/jsheri1/Desktop/20251107_SiEPICfab_Shuksan_24_02_RepeatedSweeps/RA_Analysis/RA_result
and expects the files benchtop_spectrogram_peak_shift.mat and onchip_spectrogram_peak_shift.mat.

Usage (PowerShell example) with explicit override:
    python scripts/compare_drifts.py \
        --benchtop "C:/path/to/benchtop_peak_shift.mat" \
        --onchip   "C:/path/to/onchip_peak_shift.mat" \
        --output   "C:/path/to/output/drift_comparison.png"

If --output is omitted the plot is shown interactively.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
import scipy.io
from scipy import stats
import seaborn as sns
import tkinter as tk
from tkinter import filedialog, messagebox

AXIS_FONT_SIZE = 25
TICK_FONT_SIZE = 22
LEGEND_FONT_SIZE = 18
TITLE_FONT_SIZE = 22

BASE_RA_RESULT_DIR = Path(
    "C:/Users/jsheri1/Desktop/20251107_SiEPICfab_Shuksan_24_02_RepeatedSweeps/RA_Analysis/RA_result"
)
DEFAULT_BENCHTOP_PATH = BASE_RA_RESULT_DIR / "benchtop_spectrogram_peak_shift.mat"
DEFAULT_ONCHIP_PATH = BASE_RA_RESULT_DIR / "onchip_spectrogram_peak_shift.mat"


def load_ra_shift(path: str | Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load time axis and RA-style drift arrays from a peak_shift.mat file.

    Returns (time_minutes, cumulative_pm, per_step_pm).
    """
    path_str = os.fspath(path)

    if not os.path.isfile(path_str):
        raise FileNotFoundError(f"Missing MAT file: {path_str}")

    data = scipy.io.loadmat(path_str)

    # Time array saved as minutes in plot_spectrograms.py (t_array)
    if "t_array" not in data:
        raise KeyError(f"File {path_str} does not contain 't_array'")
    times_minutes = np.asarray(data["t_array"]).flatten()

    # RA drift arrays
    try:
        cumulative_pm = np.asarray(data["ra_delta_cumulative_pm"]).flatten()
    except KeyError as exc:
        raise KeyError(
            f"File {path_str} does not contain 'ra_delta_cumulative_pm'.\n"
            "Please rerun plot_spectrograms.py so that RA drift arrays are saved."
        ) from exc

    step_pm = np.asarray(data.get("ra_delta_step_pm", np.full_like(cumulative_pm, np.nan))).flatten()

    return times_minutes, cumulative_pm, step_pm


def calc_windowed_stability(times: np.ndarray, data: np.ndarray, window_min: float = 20.0) -> Tuple[np.ndarray, np.ndarray, float, float, float, float]:
    """Calculate stability standard deviation and drift rates in time windows.
    
    For each window:
    1. Extract data points within the window
    2. Calculate std dev of raw peak positions (stability)
    3. Fit a linear trend to calculate drift rate (slope)
    
    This separates:
    - Drift rates (slopes from linear fits in each window)
    - Stability (std dev of raw peak positions in each window)
    
    Parameters:
    -----------
    times : np.ndarray
        Time array in minutes
    data : np.ndarray
        Data array (e.g., cumulative drift in pm)
    window_min : float
        Window size in minutes (default: 20 min)
    
    Returns:
    --------
    window_stds : np.ndarray
        Standard deviation of raw peak positions within each window
    window_drifts : np.ndarray
        Drift rates (slopes) from each window in pm/min
    mean_std : float
        Mean of all window standard deviations
    std_of_stds : float
        Standard deviation of the window standard deviations
    mean_drift : float
        Mean of all window drift rates
    std_of_drifts : float
        Standard deviation of the window drift rates
    """
    if len(times) < 2:
        return np.array([]), np.array([]), 0.0, 0.0, 0.0, 0.0
    
    total_duration = times[-1] - times[0]
    
    # If data is shorter than one window, compute std for entire dataset
    if total_duration < window_min:
        overall_std = np.std(data)  # Raw std dev of peak positions
        if len(times) >= 3:  # Need at least 3 points for meaningful linear fit
            coeffs = np.polyfit(times, data, 1)
            overall_drift = coeffs[0]  # slope
        else:
            overall_drift = 0.0
        return np.array([overall_std]), np.array([overall_drift]), overall_std, 0.0, overall_drift, 0.0
    
    # Calculate number of windows
    n_windows = int(np.ceil(total_duration / window_min))
    window_stds = []
    window_drifts = []
    
    for i in range(n_windows):
        t_start = times[0] + i * window_min
        t_end = t_start + window_min
        
        # Find data points in this window
        mask = (times >= t_start) & (times < t_end)
        window_times = times[mask]
        window_data = data[mask]
        
        if len(window_data) >= 3:  # Need at least 3 points for linear fit
            # Calculate std dev of raw peak positions (stability)
            window_stds.append(np.std(window_data))
            
            # Fit linear trend to get drift rate (slope)
            coeffs = np.polyfit(window_times, window_data, 1)
            window_drifts.append(coeffs[0])
        elif len(window_data) >= 2:  # Need at least 2 points for std
            window_stds.append(np.std(window_data))
            window_drifts.append(0.0)
    
    window_stds = np.array(window_stds)
    window_drifts = np.array(window_drifts)
    
    if len(window_stds) == 0:
        return np.array([]), np.array([]), 0.0, 0.0, 0.0, 0.0
    
    mean_std = np.mean(window_stds)
    std_of_stds = np.std(window_stds) if len(window_stds) > 1 else 0.0
    
    mean_drift = np.mean(window_drifts)
    std_of_drifts = np.std(window_drifts) if len(window_drifts) > 1 else 0.0
    
    return window_stds, window_drifts, mean_std, std_of_stds, mean_drift, std_of_drifts


def prompt_significance_test_choice() -> str:
    """Prompt user to select statistical test type using tkinter GUI.
    
    Returns:
    --------
    test_type : str
        Either 'mannwhitneyu' or 'wilcoxon'
    """
    # Try GUI first
    try:
        root = tk.Tk()
        root.withdraw()
        
        dialog = tk.Toplevel(root)
        dialog.title('Statistical Test Selection')
        dialog.attributes('-topmost', True)
        dialog.lift()
        dialog.focus_force()
        dialog.minsize(500, 350)
        dialog.grab_set()
        
        var = tk.StringVar(value='mannwhitneyu')
        
        # Title
        title_label = tk.Label(dialog, text='Select Statistical Significance Test', 
                              font=('Arial', 14, 'bold'))
        title_label.pack(padx=20, pady=(15, 10))
        
        # Instructions frame
        inst_frame = tk.Frame(dialog)
        inst_frame.pack(padx=20, pady=10, fill='both', expand=True)
        
        # Mann-Whitney option
        mw_frame = tk.LabelFrame(inst_frame, text='Option 1: Mann-Whitney U-test (INDEPENDENT)', 
                                 font=('Arial', 10, 'bold'), padx=10, pady=5)
        mw_frame.pack(fill='x', pady=5)
        
        tk.Radiobutton(mw_frame, text='Use for independent samples', 
                      variable=var, value='mannwhitneyu', font=('Arial', 10)).pack(anchor='w')
        tk.Label(mw_frame, text='• Different chips, times, or conditions', 
                font=('Arial', 9), fg='gray30').pack(anchor='w', padx=20)
        tk.Label(mw_frame, text='• No pairing relationship between groups', 
                font=('Arial', 9), fg='gray30').pack(anchor='w', padx=20)
        tk.Label(mw_frame, text='Example: Chip A (benchtop) vs Chip B (on-chip)', 
                font=('Arial', 9, 'italic'), fg='blue').pack(anchor='w', padx=20)
        
        # Wilcoxon option
        wil_frame = tk.LabelFrame(inst_frame, text='Option 2: Wilcoxon Test (PAIRED)', 
                                  font=('Arial', 10, 'bold'), padx=10, pady=5)
        wil_frame.pack(fill='x', pady=5)
        
        tk.Radiobutton(wil_frame, text='Use for paired/matched samples', 
                      variable=var, value='wilcoxon', font=('Arial', 10)).pack(anchor='w')
        tk.Label(wil_frame, text='• Same chip in both setups', 
                font=('Arial', 9), fg='gray30').pack(anchor='w', padx=20)
        tk.Label(wil_frame, text='• Before/after or matched measurements', 
                font=('Arial', 9), fg='gray30').pack(anchor='w', padx=20)
        tk.Label(wil_frame, text='Example: Chip A (benchtop) vs Chip A (on-chip)', 
                font=('Arial', 9, 'italic'), fg='blue').pack(anchor='w', padx=20)
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(padx=20, pady=(10, 15))
        
        def on_ok():
            dialog.selected = var.get()
            dialog.destroy()
            root.destroy()
        
        def on_cancel():
            dialog.selected = None
            dialog.destroy()
            root.destroy()
        
        tk.Button(btn_frame, text='OK', width=12, command=on_ok, 
                 font=('Arial', 10)).pack(side='left', padx=6)
        tk.Button(btn_frame, text='Cancel', width=12, command=on_cancel, 
                 font=('Arial', 10)).pack(side='left')
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
        root.wait_window(dialog)
        selected = getattr(dialog, 'selected', None)
        
        if selected:
            print(f"\n✓ Selected: {'Mann-Whitney U-test (independent)' if selected == 'mannwhitneyu' else 'Wilcoxon signed-rank test (paired)'}")
            return selected
    
    except Exception as e:
        print(f"\nGUI failed ({e}), falling back to console input...")
    
    # Console fallback
    print("\n" + "="*70)
    print("STATISTICAL TEST SELECTION")
    print("="*70)
    print("\nChoose statistical significance test:")
    print("\n1. Mann-Whitney U-test (INDEPENDENT samples)")
    print("   - Use when: Benchtop and on-chip measurements are from DIFFERENT")
    print("               chips, different times, or different environmental conditions")
    print("   - Assumption: Two groups are independent (no pairing relationship)")
    print("   - Example: Comparing chip A (benchtop) vs chip B (on-chip)")
    print("\n2. Wilcoxon signed-rank test (PAIRED samples)")
    print("   - Use when: Same chip measured in BOTH benchtop and on-chip setups")
    print("   - Assumption: Measurements are paired (before/after, matched samples)")
    print("   - Example: Comparing chip A (benchtop) vs chip A (on-chip)")
    print("\n" + "="*70)
    
    while True:
        choice = input("\nEnter choice (1 for Mann-Whitney, 2 for Wilcoxon): ").strip()
        if choice == '1':
            print("\n✓ Selected: Mann-Whitney U-test (independent samples)")
            return 'mannwhitneyu'
        elif choice == '2':
            print("\n✓ Selected: Wilcoxon signed-rank test (paired samples)")
            return 'wilcoxon'
        else:
            print("Invalid choice. Please enter 1 or 2.")


def perform_significance_test(benchtop_stds: np.ndarray, onchip_stds: np.ndarray, test_type: str = 'mannwhitneyu') -> Tuple[float, float, str, str]:
    """Perform statistical significance test comparing two sets of standard deviations.
    
    Parameters:
    -----------
    benchtop_stds : np.ndarray
        Standard deviations from benchtop measurements
    onchip_stds : np.ndarray
        Standard deviations from on-chip measurements
    test_type : str
        'mannwhitneyu' for independent samples or 'wilcoxon' for paired samples
    
    Returns:
    --------
    statistic : float
        Test statistic (U-statistic for Mann-Whitney, W-statistic for Wilcoxon)
    p_value : float
        P-value for two-tailed test
    interpretation : str
        Text interpretation of the result
    test_name : str
        Name of the test used
    """
    if len(benchtop_stds) < 2 or len(onchip_stds) < 2:
        return 0.0, 1.0, "Insufficient data for statistical test", test_type
    
    if test_type == 'wilcoxon':
        # Wilcoxon signed-rank test (paired samples)
        if len(benchtop_stds) != len(onchip_stds):
            print(f"\n⚠ WARNING: Wilcoxon test requires equal sample sizes.")
            print(f"  Benchtop windows: {len(benchtop_stds)}, On-chip windows: {len(onchip_stds)}")
            print(f"  Falling back to Mann-Whitney U-test (independent samples)")
            test_type = 'mannwhitneyu'
        else:
            statistic, p_value = stats.wilcoxon(benchtop_stds, onchip_stds, alternative='two-sided')
            test_name = "Wilcoxon signed-rank test"
    
    if test_type == 'mannwhitneyu':
        # Mann-Whitney U-test (independent samples)
        statistic, p_value = stats.mannwhitneyu(benchtop_stds, onchip_stds, alternative='two-sided')
        test_name = "Mann-Whitney U-test"
    
    # Interpret results
    if p_value < 0.001:
        sig_level = "highly significant (p < 0.001)"
    elif p_value < 0.01:
        sig_level = "very significant (p < 0.01)"
    elif p_value < 0.05:
        sig_level = "significant (p < 0.05)"
    else:
        sig_level = "not significant (p ≥ 0.05)"
    
    # Determine which is more stable (lower median std = more stable)
    benchtop_median = np.median(benchtop_stds)
    onchip_median = np.median(onchip_stds)
    
    if benchtop_median < onchip_median:
        better = "Benchtop shows better stability"
    else:
        better = "On-chip shows better stability"
    
    interpretation = f"{better}, difference is {sig_level}"
    
    return statistic, p_value, interpretation, test_name


def plot_comparison(
    benchtop: Tuple[np.ndarray, np.ndarray, np.ndarray],
    onchip: Tuple[np.ndarray, np.ndarray, np.ndarray],
    output: str | None,
    data_dir: str | Path | None = None,
) -> None:
    benchtop_time, benchtop_cum, benchtop_step = benchtop
    onchip_time, onchip_cum, onchip_step = onchip

    # Calculate drift rates (pm/min) from cumulative data using linear fit
    def calc_drift_rate(times: np.ndarray, cumulative: np.ndarray) -> float:
        """Calculate drift rate in pm/min via linear regression."""
        if len(times) < 2:
            return 0.0
        coeffs = np.polyfit(times, cumulative, 1)
        return coeffs[0]  # slope in pm/min
    
    benchtop_rate = calc_drift_rate(benchtop_time, benchtop_cum)
    onchip_rate = calc_drift_rate(onchip_time, onchip_cum)

    # Calculate windowed stability and drift metrics
    (benchtop_stds, benchtop_drifts, benchtop_mean_std, benchtop_std_of_stds, 
     benchtop_mean_drift, benchtop_std_of_drifts) = calc_windowed_stability(
        benchtop_time, benchtop_cum, window_min=20.0
    )
    (onchip_stds, onchip_drifts, onchip_mean_std, onchip_std_of_stds,
     onchip_mean_drift, onchip_std_of_drifts) = calc_windowed_stability(
        onchip_time, onchip_cum, window_min=20.0
    )
    
    # Prompt user for statistical test choice
    test_type = prompt_significance_test_choice()
    
    # Perform significance tests
    stat_stab, p_value_stab, interpretation_stab, test_name_stab = perform_significance_test(benchtop_stds, onchip_stds, test_type)
    stat_drift, p_value_drift, interpretation_drift, test_name_drift = perform_significance_test(benchtop_drifts, onchip_drifts, test_type)
    
    # Create summary text
    summary_text = []
    summary_text.append("="*70)
    summary_text.append("STABILITY ANALYSIS SUMMARY")
    summary_text.append("="*70)
    summary_text.append("")
    summary_text.append("Benchtop:")
    summary_text.append(f"  Global drift rate: {benchtop_rate:.3f} pm/min (from all data)")
    summary_text.append(f"  Windowed drift rate: {benchtop_mean_drift:.3f} ± {benchtop_std_of_drifts:.3f} pm/min")
    summary_text.append(f"  Stability (windowed std): {benchtop_mean_std:.3f} ± {benchtop_std_of_stds:.3f} pm")
    summary_text.append(f"  Median stability: {np.median(benchtop_stds):.3f} pm")
    summary_text.append(f"  Number of windows: {len(benchtop_stds)}")
    summary_text.append("")
    summary_text.append("On-chip:")
    summary_text.append(f"  Global drift rate: {onchip_rate:.3f} pm/min (from all data)")
    summary_text.append(f"  Windowed drift rate: {onchip_mean_drift:.3f} ± {onchip_std_of_drifts:.3f} pm/min")
    summary_text.append(f"  Stability (windowed std): {onchip_mean_std:.3f} ± {onchip_std_of_stds:.3f} pm")
    summary_text.append(f"  Median stability: {np.median(onchip_stds):.3f} pm")
    summary_text.append(f"  Number of windows: {len(onchip_stds)}")
    summary_text.append("")
    summary_text.append(f"Statistical Comparison - Windowed Drift ({test_name_drift}):")
    summary_text.append(f"  Test statistic: {stat_drift:.3f}")
    summary_text.append(f"  p-value: {p_value_drift:.4f}")
    summary_text.append(f"  Result: {interpretation_drift}")
    summary_text.append("")
    summary_text.append(f"Statistical Comparison - Stability ({test_name_stab}):")
    summary_text.append(f"  Test statistic: {stat_stab:.3f}")
    summary_text.append(f"  p-value: {p_value_stab:.4f}")
    summary_text.append(f"  Result: {interpretation_stab}")
    summary_text.append("="*70)
    summary_text.append("")
    summary_text.append("INTERPRETATION:")
    summary_text.append("-" * 70)
    summary_text.append("Global Drift Rate: Quantifies overall baseline drift over entire measurement")
    summary_text.append("  - Computed from linear least-squares fit to ALL cumulative drift data")
    summary_text.append("  - Represents the overall wavelength drift trend (pm/min)")
    summary_text.append("  - Shown in cumulative drift plot legend")
    summary_text.append("")
    summary_text.append("Windowed Drift Rate: Quantifies drift rate consistency across time windows")
    summary_text.append("  - Data divided into 20-minute windows")
    summary_text.append("  - Linear fit computed for each window separately")
    summary_text.append("  - Mean ± std of all window drift rates")
    summary_text.append("  - Lower std indicates more consistent drift behavior over time")
    summary_text.append("  - Shown in bar plot for comparison")
    summary_text.append("")
    summary_text.append("Stability (Windowed Std Dev): Quantifies total variation in peak position")
    summary_text.append("  - Data divided into 20-minute windows")
    summary_text.append("  - Within each window:")
    summary_text.append("    * Calculate std dev of raw peak positions")
    summary_text.append("  - This captures total variation (drift + noise) within each window")
    summary_text.append("  - Lower values indicate more stable measurements with less variation")
    summary_text.append("")
    summary_text.append("Together, these metrics capture:")
    summary_text.append("  1. Overall baseline drift (global drift rate)")
    summary_text.append("  2. Drift consistency (windowed drift rate variability)")
    summary_text.append("  3. Total variation (windowed std of peak positions)")
    summary_text.append("="*70)
    
    # Print to console
    print("\n" + "\n".join(summary_text) + "\n")
    
    # Use inferno colormap matching powerextraction.py style
    cmap_inferno = plt.get_cmap('inferno')
    # Use 0.2 and 0.65 positions to match AllQ_analysis style
    color_benchtop = cmap_inferno(0.2)   # darker inferno color for benchtop
    color_onchip = cmap_inferno(0.65)    # mid-range inferno color for on-chip
    
    # Cumulative drift plot
    fig_cum, ax_cum = plt.subplots(figsize=(10, 6))
    ax_cum.plot(benchtop_time, benchtop_cum, "o-", 
                label=f"Benchtop", 
                linewidth=1.8, color=color_benchtop, markersize=5)
    ax_cum.plot(onchip_time, onchip_cum, "o-", 
                label=f"On-chip", 
                linewidth=1.8, color=color_onchip, markersize=5)
    ax_cum.set_xlabel("Time (min)", fontsize=AXIS_FONT_SIZE)
    ax_cum.set_ylabel("Cumulative Δλ (pm)", fontsize=AXIS_FONT_SIZE)
    ax_cum.set_title("Cumulative Drift Comparison", fontsize=TITLE_FONT_SIZE)
    ax_cum.grid(True, linestyle="--", alpha=0.3)
    ax_cum.legend(fontsize=LEGEND_FONT_SIZE)
    ax_cum.tick_params(axis="both", which="major", labelsize=TICK_FONT_SIZE)
    fig_cum.tight_layout()

    # Per-sweep drift plot
    fig_step, ax_step = plt.subplots(figsize=(10, 6))
    ax_step.plot(benchtop_time, benchtop_step, "o-", label="Benchtop", 
                 linewidth=1.5, color=color_benchtop, markersize=5)
    ax_step.plot(onchip_time, onchip_step, "o-", label="On-chip", 
                 linewidth=1.5, color=color_onchip, markersize=5)
    ax_step.set_xlabel("Time (min)", fontsize=AXIS_FONT_SIZE)
    ax_step.set_ylabel("Δλ per sweep (pm)", fontsize=AXIS_FONT_SIZE)
    ax_step.set_title("Per-sweep Drift Comparison", fontsize=TITLE_FONT_SIZE)
    ax_step.grid(True, linestyle="--", alpha=0.3)
    ax_step.legend(fontsize=LEGEND_FONT_SIZE)
    ax_step.tick_params(axis="both", which="major", labelsize=TICK_FONT_SIZE)
    fig_step.tight_layout()

    # Create drift rate beeswarm plot
    fig_drift, ax_drift = plt.subplots(figsize=(8, 6))
    
    # Windowed drift rate beeswarm plot
    sns.swarmplot(data=[benchtop_drifts, onchip_drifts], 
                  palette=[color_benchtop, color_onchip],
                  size=15, alpha=0.7, ax=ax_drift)
    
    # Overlay mean with error bars for drift
    positions = [0, 1]
    ax_drift.errorbar(positions, 
                     [benchtop_mean_drift, onchip_mean_drift],
                     yerr=[benchtop_std_of_drifts, onchip_std_of_drifts],
                     fmt='D', markersize=6, color='black', 
                     linewidth=1, capsize=4, capthick=2, zorder=10)
    
    ax_drift.set_xticks(positions)
    ax_drift.set_xticklabels(['Benchtop', 'On-chip'])
    ax_drift.set_ylabel(r'Drift Rate (pm/min)', fontsize=AXIS_FONT_SIZE)
    #ax_drift.set_title('Windowed Drift Rate Distribution\n(20-min windows)', fontsize=TITLE_FONT_SIZE)
    ax_drift.tick_params(axis='both', labelsize=TICK_FONT_SIZE)
    ax_drift.grid(axis='y', linestyle='--', alpha=0.3)
    ax_drift.set_xlim(-0.5, 1.5)
    
    fig_drift.tight_layout()

    # Create stability beeswarm plot
    fig_stab, ax_stab = plt.subplots(figsize=(8, 6))
    
    # Plot stability beeswarm
    sns.swarmplot(data=[benchtop_stds, onchip_stds], 
                  palette=[color_benchtop, color_onchip],
                  size=15, alpha=0.7, ax=ax_stab)
    
    # Overlay mean with error bars
    ax_stab.errorbar(positions, 
                    [benchtop_mean_std, onchip_mean_std],
                    yerr=[benchtop_std_of_stds, onchip_std_of_stds],
                    fmt='D', markersize=6, color='black', 
                    linewidth=1, capsize=4, capthick=2, zorder=10)
    
    ax_stab.set_xticks(positions)
    ax_stab.set_xticklabels(['Benchtop', 'On-chip'])
    ax_stab.set_ylabel(r'Stability $\sigma_{\Delta\lambda}$ (pm)', fontsize=AXIS_FONT_SIZE)
    #ax_stab.set_title('Windowed Stability Distribution\n(20-min windows)', fontsize=TITLE_FONT_SIZE)
    ax_stab.tick_params(axis='both', labelsize=TICK_FONT_SIZE)
    ax_stab.grid(axis='y', linestyle='--', alpha=0.3)
    ax_stab.set_xlim(-0.5, 1.5)
    
    fig_stab.tight_layout()

    if output:
        # Save plots with suffixes
        output_path = Path(output)
        cum_output = output_path.parent / f"{output_path.stem}_cumulative{output_path.suffix}"
        step_output = output_path.parent / f"{output_path.stem}_perstep{output_path.suffix}"
        drift_output = output_path.parent / f"{output_path.stem}_drift{output_path.suffix}"
        stability_output = output_path.parent / f"{output_path.stem}_stability{output_path.suffix}"
        txt_output = output_path.parent / f"{output_path.stem}_summary.txt"
        
        fig_cum.savefig(cum_output, dpi=300)
        print(f"Saved cumulative drift plot to {cum_output}")
        
        fig_step.savefig(step_output, dpi=300)
        print(f"Saved per-sweep drift plot to {step_output}")
        
        fig_drift.savefig(drift_output, dpi=300)
        print(f"Saved drift rate beeswarm plot to {drift_output}")
        
        fig_stab.savefig(stability_output, dpi=300)
        print(f"Saved stability beeswarm plot to {stability_output}")
        
        # Save summary text file
        with open(txt_output, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary_text))
        print(f"Saved summary statistics to {txt_output}")
    else:
        # Save to parent folder of data directory
        if data_dir:
            output_dir = Path(data_dir).parent
        else:
            output_dir = BASE_RA_RESULT_DIR.parent
        cum_output = output_dir / "drift_comparison_cumulative.png"
        step_output = output_dir / "drift_comparison_perstep.png"
        drift_output = output_dir / "drift_comparison_drift.png"
        stability_output = output_dir / "drift_comparison_stability.png"
        txt_output = output_dir / "drift_comparison_summary.txt"
        
        fig_cum.savefig(cum_output, dpi=300)
        print(f"Saved cumulative drift plot to {cum_output}")
        
        fig_step.savefig(step_output, dpi=300)
        print(f"Saved per-sweep drift plot to {step_output}")
        
        fig_drift.savefig(drift_output, dpi=300)
        print(f"Saved drift rate beeswarm plot to {drift_output}")
        
        fig_stab.savefig(stability_output, dpi=300)
        print(f"Saved stability beeswarm plot to {stability_output}")
        
        # Save summary text file
        with open(txt_output, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary_text))
        print(f"Saved summary statistics to {txt_output}")


def prompt_file_selection() -> Tuple[str, str, str | None, str | None]:
    """Prompt user to select base directory using tkinter GUI.
    
    Returns:
    --------
    benchtop_path : str
        Path to benchtop .mat file
    onchip_path : str
        Path to on-chip .mat file
    output_path : str | None
        Path to save output files (None for default location)
    data_dir : str | None
        Path to the selected data directory
    """
    # Try GUI first
    try:
        root = tk.Tk()
        root.withdraw()
        
        print("\n" + "="*70)
        print("DIRECTORY SELECTION")
        print("="*70)
        print("\nA folder dialog will appear. Please select the RA_result directory")
        print("containing benchtop_spectrogram_peak_shift.mat and")
        print("onchip_spectrogram_peak_shift.mat files.")
        print("="*70 + "\n")
        
        # Select base directory
        base_dir = filedialog.askdirectory(
            title="Select RA_result Directory (containing both .mat files)",
            initialdir=str(BASE_RA_RESULT_DIR)
        )
        
        if not base_dir:
            print("❌ No directory selected. Using default location.")
            base_path = BASE_RA_RESULT_DIR
        else:
            base_path = Path(base_dir)
            print(f"✓ Selected directory: {base_path}")
        
        # Construct file paths
        benchtop_path = str(base_path / "benchtop_spectrogram_peak_shift.mat")
        onchip_path = str(base_path / "onchip_spectrogram_peak_shift.mat")
        
        # Output will be saved to parent directory by default
        output_path = None
        data_dir = str(base_path)
        
        root.destroy()
        return benchtop_path, onchip_path, output_path, data_dir
    
    except Exception as e:
        print(f"\nGUI failed ({e}), using command-line arguments...")
        return None, None, None, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Overlay RA drift curves for benchtop vs on-chip analyses")
    parser.add_argument(
        "--benchtop",
        default=None,
        help=f"Path to benchtop peak_shift.mat (default: {DEFAULT_BENCHTOP_PATH})",
    )
    parser.add_argument(
        "--onchip",
        default=None,
        help=f"Path to on-chip peak_shift.mat (default: {DEFAULT_ONCHIP_PATH})",
    )
    parser.add_argument("--output", help="Optional path to save the overlay PNG")
    parser.add_argument("--gui", action="store_true", help="Use GUI for file selection")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    # Use GUI for file selection if --gui flag or no arguments provided
    if args.gui or (args.benchtop is None and args.onchip is None):
        benchtop_path, onchip_path, output_path, data_dir = prompt_file_selection()
        
        # Fall back to defaults if GUI was cancelled
        if benchtop_path is None:
            benchtop_path = args.benchtop or str(DEFAULT_BENCHTOP_PATH)
        if onchip_path is None:
            onchip_path = args.onchip or str(DEFAULT_ONCHIP_PATH)
        if output_path is None:
            output_path = args.output
        if data_dir is None:
            data_dir = str(DEFAULT_BENCHTOP_PATH.parent)  # Use default data dir
    else:
        benchtop_path = args.benchtop or str(DEFAULT_BENCHTOP_PATH)
        onchip_path = args.onchip or str(DEFAULT_ONCHIP_PATH)
        output_path = args.output
        # Infer data_dir from benchtop path
        data_dir = str(Path(benchtop_path).parent)
    
    print(f"\n📁 Loading data:")
    print(f"   Benchtop: {benchtop_path}")
    print(f"   On-chip:  {onchip_path}")
    
    benchtop_data = load_ra_shift(benchtop_path)
    onchip_data = load_ra_shift(onchip_path)
    plot_comparison(benchtop_data, onchip_data, output_path, data_dir)


if __name__ == "__main__":
    main()
