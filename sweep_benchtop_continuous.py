import os
from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import filedialog
import tkinter as tk
import multi_select

from standaloneLIV import extract_current_and_ch0

# Plot font constants
PLOT_FONT_AXIS_LABEL = 18
PLOT_FONT_AXIS_TICKS = 18
PLOT_FONT_TITLE = 14
PLOT_FONT_LEGEND = 16
PLOT_FONT_TEXT = 9

def extract_wavelength_and_ch3(csv_path):
    """
    Try to extract 'Wavelength' and channel '3' rows from a benchtop CSV file.
    Returns (wavelength, ch3) as numpy arrays or (None, None) on failure.
    """
    try:
        # Read the file line by line to handle variable column counts
        with open(csv_path, 'r') as f:
            lines = f.readlines()
        
        wavelength = None
        ch3 = None
        
        for line in lines:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
                
            label = parts[0].lower()
            
            # Check for wavelength row
            if 'wavelength' in label and '(nm)' in label:
                # Extract numeric values from the rest of the row
                wavelength = np.array([float(x) for x in parts[1:] if x and x.replace('.', '').replace('-', '').replace('e', '').replace('+', '').isdigit() or 'e' in x.lower()])
            
            # Check for channel 3 row
            if 'channel' in label and '3' in label:
                # Extract numeric values from the rest of the row
                ch3 = np.array([float(x) for x in parts[1:] if x and x.replace('.', '').replace('-', '').replace('e', '').replace('+', '').isdigit() or 'e' in x.lower()])
        
        if wavelength is None or ch3 is None:
            return None, None
            
        # Make sure they have the same length
        min_len = min(len(wavelength), len(ch3))
        return wavelength[:min_len], ch3[:min_len]
        
    except Exception as e:
        print(f"  → Error extracting data: {e}")
        return None, None

def plot_all_ch3_vs_wavelength(parent_folder, selected_files=None, out_png=None, wl_min=1330.3, wl_max=1330.9):
    """
    Plot wavelength vs channel 3 power for all CSVs in subfolders.
    
    Parameters:
    - parent_folder: Root folder to search for CSVs
    - selected_files: List of specific subfolder/file names to process (optional)
    - out_png: Output PNG filename (optional)
    - wl_min: Minimum wavelength in nm (default 1330.4)
    - wl_max: Maximum wavelength in nm (default 1330.95)
    """
    parent = Path(parent_folder)
    if not parent.exists():
        raise FileNotFoundError(parent_folder)

    # Get list of CSV files based on selection
    if selected_files:
        print(f"Processing selected files/folders: {selected_files}")
        csv_files = []
        for name in selected_files:
            # Check if it's a direct file path
            file_path = parent / name
            if file_path.is_file() and file_path.suffix == '.csv':
                csv_files.append(file_path)
            elif file_path.is_dir():
                # Search for CSVs in this subfolder
                csv_files.extend(file_path.rglob("*.csv"))
            else:
                # Try treating it as a subfolder name
                csv_files.extend(parent.rglob(f"*{name}*/*.csv"))
    else:
        # Process all CSVs if no selection
        csv_files = list(parent.rglob("*.csv"))
    
    print(f"Found {len(csv_files)} CSV files")
    
    traces = []
    for csv_path in csv_files:
        print(f"Processing: {csv_path.relative_to(parent)}")
        wavelength, ch3 = extract_wavelength_and_ch3(csv_path)
        if wavelength is None or ch3 is None:
            print(f"  → Could not extract wavelength/ch3 data")
            continue
        
        print(f"  → Wavelength range: {wavelength.min():.2f} - {wavelength.max():.2f} nm")
        
        # Filter wavelength range
        mask = (wavelength >= wl_min) & (wavelength <= wl_max)
        wavelength_filtered = wavelength[mask]
        ch3_filtered = ch3[mask]
        
        print(f"  → Points in range {wl_min}-{wl_max} nm: {len(wavelength_filtered)}")
        
        if len(wavelength_filtered) == 0:
            continue
            
        # name by folder or file stem
        name = csv_path.parent.name if csv_path.parent != parent else csv_path.stem
        traces.append((name, wavelength_filtered, ch3_filtered, csv_path))

    if not traces:
        print(f"No valid CSV traces with Wavelength and channel 3 found in range {wl_min}-{wl_max} nm.")
        return

    # Get inferno colormap
    cmap = plt.get_cmap('inferno')
    colors = cmap(np.linspace(0.2, 0.9, len(traces)))  # Use visible range of inferno

    fig, ax = plt.subplots(figsize=(12, 7))
    for idx, (name, wavelength, ch3, csv_path) in enumerate(traces):
        # Only add label for first and last trace
        if idx == 0:
            label = f"First: {csv_path.stem}"  # stem removes .csv extension
        elif idx == len(traces) - 1:
            label = f"Last: {csv_path.stem}"
        else:
            label = None
        ax.plot(wavelength, ch3, linewidth=1.2, label=label, color=colors[idx])

    ax.set_xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax.set_ylabel("Channel 3 Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax.set_title(f"Channel 3 vs Wavelength ({wl_min}-{wl_max} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)

    # Show legend inside plot area (best location)
    ax.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
    fig.tight_layout()

    if out_png is None:
        # Save to parent directory of the selected folder
        out_png = str(parent.parent / f"Channel3_vs_Wavelength_{wl_min}_{wl_max}nm.png")
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    print(f"Saved plot to {out_png}")
    print(f"Plotted {len(traces)} traces")
    
    # Create second plot - show all traces with legends if <= 10 traces, otherwise just first & last
    fig2, ax2 = plt.subplots(figsize=(12, 7))
    
    if len(traces) <= 10:
        # Show all traces with full legends
        for idx, (name, wavelength, ch3, csv_path) in enumerate(traces):
            ax2.plot(wavelength, ch3, marker='o', linewidth=1.2, label=csv_path.stem, color=colors[idx])
        
        ax2.set_title(f"Channel 3 vs Wavelength - All Sweeps ({wl_min}-{wl_max} nm)", fontsize=PLOT_FONT_TITLE, fontweight='bold')
        out_png2 = str(parent.parent / f"Channel3_vs_Wavelength_AllSweeps_{wl_min}_{wl_max}nm.png")
        print(f"Saved all sweeps plot to {out_png2}")
    else:
        # Plot only first and last trace
        first_name, first_wavelength, first_ch3, first_csv_path = traces[0]
        ax2.plot(first_wavelength, first_ch3, marker='o', linewidth=1.2, label=f"First: {first_csv_path.stem}", color=colors[0])
        
        last_name, last_wavelength, last_ch3, last_csv_path = traces[-1]
        ax2.plot(last_wavelength, last_ch3, marker='o', linewidth=1.2, label=f"Last: {last_csv_path.stem}", color=colors[-1])
        
        ax2.set_title(f"Channel 3 vs Wavelength - First & Last Sweep ({wl_min}-{wl_max} nm)", fontsize=18, fontweight='bold')
        out_png2 = str(parent.parent / f"Channel3_vs_Wavelength_FirstLast_{wl_min}_{wl_max}nm.png")
        print(f"Saved first & last plot to {out_png2}")
    
    ax2.set_xlabel("Wavelength (nm)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax2.set_ylabel("Channel 3 Power (mW)", fontsize=PLOT_FONT_AXIS_LABEL, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='both', labelsize=PLOT_FONT_AXIS_TICKS)
    ax2.legend(fontsize=PLOT_FONT_LEGEND, loc='best')
    fig2.tight_layout()
    
    # Save second plot
    plt.savefig(out_png2, dpi=300, bbox_inches='tight')
    
    plt.show()

if __name__ == "__main__":
    # Create root window for dialogs
    root = tk.Tk()
    root.withdraw()
    
    # Ask for parent directory
    parent_dir = filedialog.askdirectory(title="Select Parent Directory for Benchtop Data Processing")
    
    if not parent_dir:
        print("No folder selected. Exiting.")
        root.destroy()
    else:
        # Open file selection GUI
        file_selection = multi_select.scrape_filenames(root, parent_dir)
        
        if file_selection:
            print(f"Selected folder: {parent_dir}")
            print(f"Selected files/folders: {file_selection}")
            # Plot wavelength vs channel 3 power for range 1330.3 - 1330.9 nm
            plot_all_ch3_vs_wavelength(parent_dir, selected_files=file_selection, wl_min=1330.28, wl_max=1330.92)
        else:
            print("No files/folders selected. Processing all CSV files...")
            plot_all_ch3_vs_wavelength(parent_dir, wl_min=1330.3, wl_max=1330.92)
        
        root.destroy()
    
