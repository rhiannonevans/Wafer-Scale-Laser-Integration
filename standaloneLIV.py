import os
from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.io

# Plot font constants
PLOT_FONT_AXIS_LABEL = 18
PLOT_FONT_AXIS_TICKS = 18
PLOT_FONT_TITLE = 14
PLOT_FONT_LEGEND = 16
PLOT_FONT_TEXT = 9

def extract_current_and_ch0(csv_path, skiprows_guess=24):
    """
    Try to extract 'Current', 'Voltage', 'Temperature', and channel '0' rows from a CSV similar to WLM/LIV format.
    Returns (current_mA, voltage, temperature, ch0_mW) as numpy arrays or (None, None, None, None) on failure.
    """
    try:
        df = pd.read_csv(csv_path, header=None, on_bad_lines="skip", engine="python", skiprows=0)
    except Exception:
        return None, None, None, None

    # find row indices where first column mentions the terms
    search_terms = {
        "current": r'Current',
        "voltage": r'Voltage',
        #"wavelength": r'Wavelength',
        "temperature": r'Temperature',
        "ch0": r'channel\s*0'  # Matches "channel 0" or "channel0"
    }

    indices = {}
    for key, term in search_terms.items():
        matches = df[0].astype(str).str.contains(term, case=False, na=False)
        indices[key] = int(matches.idxmax()) if matches.any() else None

    # require current and ch0
    if indices["current"] is None or indices["ch0"] is None:
        # try a fallback: skip a header block (guess) and re-read
        try:
            df2 = pd.read_csv(csv_path, header=None, on_bad_lines="skip", engine="python", skiprows=skiprows_guess)
            df = df2
            for key, term in search_terms.items():
                matches = df[0].astype(str).str.contains(term, case=False, na=False)
                indices[key] = int(matches.idxmax()) if matches.any() else None
        except Exception:
            return None, None, None, None

    if indices["current"] is None or indices["ch0"] is None:
        return None, None, None, None

    # remove label column then read numeric rows
    try:
        # drop the column used for labels and use remaining columns as data points
        label_col = df[0].copy()
        data = df.drop(columns=[0])
        current_row = data.loc[indices["current"]].apply(pd.to_numeric, errors='coerce').dropna()
        ch0_row = data.loc[indices["ch0"]].apply(pd.to_numeric, errors='coerce').dropna()
        
        # Extract voltage and temperature if available
        voltage_row = None
        temperature_row = None
        if indices["voltage"] is not None:
            voltage_row = data.loc[indices["voltage"]].apply(pd.to_numeric, errors='coerce').dropna()
        if indices["temperature"] is not None:
            temperature_row = data.loc[indices["temperature"]].apply(pd.to_numeric, errors='coerce').dropna()
        
        # align lengths by taking intersection of column indices
        common_cols = current_row.index.intersection(ch0_row.index)
        if voltage_row is not None:
            common_cols = common_cols.intersection(voltage_row.index)
        if temperature_row is not None:
            common_cols = common_cols.intersection(temperature_row.index)
            
        if len(common_cols) == 0:
            return None, None, None, None
            
        current = current_row.loc[common_cols].values.astype(float)
        ch0 = ch0_row.loc[common_cols].values.astype(float)
        voltage = voltage_row.loc[common_cols].values.astype(float) if voltage_row is not None else np.full_like(current, np.nan)
        temperature = temperature_row.loc[common_cols].values.astype(float) if temperature_row is not None else np.full_like(current, np.nan)
    except Exception:
        return None, None, None, None

    # convert current to mA if values look like amps (max < 10)
    if np.nanmax(np.abs(current)) < 10:
        current_mA = current * 1000.0
    else:
        current_mA = current

    return current_mA, voltage, temperature, ch0

def process_and_save_liv(csv_path, overwrite=False):
    """
    Process a single LIV CSV file:
    1. Extract current, voltage, temperature, and channel 0 data
    2. Plot and save Current-Voltage curve
    3. Plot and save Current-Ch0 Power curve
    4. Save all parameters to .mat file with same name as CSV
    
    Parameters:
    - csv_path: Path to CSV file
    - overwrite: If False, skip if .mat file already exists
    
    Returns: True if successful, False otherwise
    """
    csv_path = Path(csv_path)
    mat_path = csv_path.with_suffix('.mat')
    
    # Check if already processed
    if not overwrite and mat_path.exists():
        print(f"  → Skipping {csv_path.name} (already processed)")
        return False
    
    # Extract data
    print(f"  → Processing {csv_path.name}")
    current_mA, voltage, temperature, ch0 = extract_current_and_ch0(csv_path)
    
    if current_mA is None or ch0 is None:
        print(f"  → Failed to extract data from {csv_path.name}")
        return False
    
    # Save folder is same as CSV location
    save_folder = csv_path.parent
    base_name = csv_path.stem
    
    # Create plots
    fig_iv, ax_iv = plt.subplots(figsize=(10, 7))
    ax_iv.plot(current_mA, voltage, marker='o', linewidth=2, color='blue')
    ax_iv.set_xlabel("Current (mA)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax_iv.set_ylabel("Voltage (V)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax_iv.set_title(f"Voltage vs Current - {base_name}", fontsize=PLOT_FONT_TITLE, fontweight='bold')
    ax_iv.grid(True, alpha=0.3)
    ax_iv.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
    fig_iv.tight_layout()
    
    iv_png = save_folder / f"{base_name}_IV.png"
    fig_iv.savefig(iv_png, dpi=300, bbox_inches='tight')
    plt.close(fig_iv)
    print(f"    ✓ Saved I-V plot: {iv_png.name}")
    
    # Plot Current vs Ch0 Power
    fig_li, ax_li = plt.subplots(figsize=(10, 7))
    ax_li.plot(current_mA, ch0, marker='o', linewidth=2, color='red')
    ax_li.set_xlabel("Current (mA)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax_li.set_ylabel("Channel 0 Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax_li.set_title(f"Channel 0 Power vs Current - {base_name}", fontsize=PLOT_FONT_TITLE, fontweight='bold')
    ax_li.grid(True, alpha=0.3)
    ax_li.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
    fig_li.tight_layout()
    
    li_png = save_folder / f"{base_name}_LI.png"
    fig_li.savefig(li_png, dpi=300, bbox_inches='tight')
    plt.close(fig_li)
    print(f"    ✓ Saved L-I plot: {li_png.name}")
    
    # Find peak power and corresponding values
    peak_idx = np.argmax(ch0)
    peak_power = ch0[peak_idx]
    peak_power_I = current_mA[peak_idx]
    peak_power_V = voltage[peak_idx]
    
    # Save to .mat file
    mat_data = {
        'current_mA': current_mA,
        'voltage_V': voltage,
        'temperature_C': temperature,
        'power_mW': ch0,
    }
    
    scipy.io.savemat(mat_path, mat_data)
    print(f"    ✓ Saved .mat data: {mat_path.name} in {save_folder.name}/")
    print(f"    → Peak power: {peak_power:.3f} mW at I={peak_power_I:.2f} mA, V={peak_power_V:.2f} V")
    
    return True

def plot_all_ch0_vs_current(parent_folder, out_png=None, process_individual=True, overwrite=False):
    """
    Plot all Channel 0 vs Current curves from CSV files in parent folder.
    
    Parameters:
    - parent_folder: Root folder to search for CSVs
    - out_png: Optional output filename for combined plot
    - process_individual: If True, also process and save individual plots/data for each CSV
    - overwrite: If True, reprocess files even if .mat exists
    """
    parent = Path(parent_folder)
    if not parent.exists():
        raise FileNotFoundError(parent_folder)

    traces = []
    for csv_path in parent.rglob("*.csv"):
        # Process individual file if requested
        if process_individual:
            process_and_save_liv(csv_path, overwrite=overwrite)
        
        # Extract data for combined plot
        current_mA, voltage, temperature, ch0 = extract_current_and_ch0(csv_path)
        if current_mA is None or ch0 is None:
            continue
        # name by folder or file stem
        name = csv_path.parent.name if csv_path.parent != parent else csv_path.stem
        traces.append((name, current_mA, ch0, csv_path))

    if not traces:
        print("No valid CSV traces with Current and channel 0 found.")
        return

    plt.figure(figsize=(10, 7))
    for name, current_mA, ch0, csv_path in traces:
        plt.plot(current_mA, ch0, marker='o', linewidth=1.2, label=name)

    plt.xlabel("Current (mA)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    plt.ylabel("Channel 0 Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    plt.title("Channel 0 vs Current (all CSVs)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)

    # set x ticks to steps of 5 mA (0,5,10,...)
    all_currents = np.concatenate([c for _, c, _, _ in traces])
    min_c = float(np.nanmin(all_currents))
    max_c = float(np.nanmax(all_currents))
    # round outwards to nearest multiple of 5
    start = int(np.floor(min_c / 5.0) * 5)
    end = int(np.ceil(max_c / 5.0) * 5)
    if start == end:
        end = start + 5
    xticks = np.arange(start, end + 1, 5)
    ax = plt.gca()
    ax.set_xticks(xticks)
    ax.set_xlim(start, end)
    ax.set_xticklabels([str(int(t)) for t in xticks], fontsize=PLOT_FONT_AXIS_TICKS)

    if len(traces) <= 30:
        plt.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
    else:
        print(f"{len(traces)} traces: legend suppressed.")
    plt.tight_layout()

    if out_png is None:
        out_png = str(parent / "Channel0_vs_Current.png")
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    print(f"Saved plot to {out_png}")
    plt.show()
    

if __name__ == "__main__":
    parent_folder = r"C:\Users\jsheri1\Documents\TA\202509ELEC413\ELEC413_Lab_2025_Fall\Group8\LIV"
    
    # Process all CSVs: create individual plots and .mat files, plus combined plot
    print("Processing LIV data...")
    plot_all_ch0_vs_current(parent_folder, out_png=None, process_individual=True, overwrite=False)
    print("\nProcessing complete!")