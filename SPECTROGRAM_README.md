# Spectrogram Plotting Tool

## Overview
`plot_spectrograms.py` is a versatile tool for analyzing and visualizing spectral data from benchtop CSV files, on-chip LIV measurements, and MAT files. It generates spectrograms (time vs wavelength heatmaps) and overlay plots.

## Features

### Benchtop CSV Workflow
- Recursively discovers CSV files with timestamps
- Extracts wavelength and Channel 3 power data
- Generates:
  1. **Spectrogram**: Time (minutes) vs Wavelength heatmap with inferno colormap
  2. **Overlay Plot 1**: All sweeps overlaid (gradient colored, first/last labeled)
  3. **Overlay Plot 2**: Detailed view with markers (all traces if ≤10, else first/last only)
  4. **MAT file** (optional): Saves aligned data for future analysis

### On-Chip Workflow (LIV + OSA)
- Uses OSA polyfit coefficients to convert current→wavelength
- Processes timestamped LIV .mat files recursively
- Converts LIV current axis to wavelength using 2nd order polynomial: `wavelength = a*I² + b*I + c`
- Generates:
  1. **Spectrogram**: Time (minutes) vs Wavelength heatmap
  2. **Overlay Plot 1**: All power vs wavelength traces (gradient colored)
  3. **Overlay Plot 2**: Detailed view with markers
  4. **MAT file** (optional): Saves aligned spectrogram data + polyfit coefficients

### MAT File Workflow
- Processes existing .mat sweep files
- Generates per-channel spectrograms
- Supports interactive viewing with pyqtgraph (optional)

## Usage

### Interactive Mode (GUI Prompts)
Simply run the script with no arguments:
```powershell
python plot_spectrograms.py
```

The script will prompt you for:
1. **Data type**: Benchtop CSVs, On-chip (LIV+OSA), or MAT files
2. **Input files/directories**:
   - Benchtop: Folder containing CSV files + wavelength range
   - On-chip: OSA .mat file + LIV folder
   - MAT: Folder containing .mat files
3. **Save options**: Whether to save .mat file with aligned data

### Command-Line Mode

#### Benchtop CSV Analysis
```powershell
# Basic usage with prompts for wavelength range
python plot_spectrograms.py --benchtop -i "C:\path\to\benchtop\data"

# Specify everything via CLI (no prompts)
python plot_spectrograms.py --benchtop -i "C:\path\to\benchtop\data" --wl-min 1330.28 --wl-max 1330.92 --save-mat -o "C:\output\folder"
```

#### On-Chip Analysis (LIV + OSA)
```powershell
# Interactive prompts for files
python plot_spectrograms.py --onchip

# Specify everything via CLI (no prompts)
python plot_spectrograms.py --onchip --osa-file "C:\path\to\OSA_file.mat" --liv-dir "C:\path\to\LIV\folder" --save-mat -o "C:\output"
```

#### MAT File Analysis
```powershell
# Process all .mat files in directory
python plot_spectrograms.py -i "C:\path\to\mat\files" -o "C:\output"

# Use specific file range and invert power values
python plot_spectrograms.py -i "C:\path\to\mat\files" --start 0 --stop 100 --step 2 --invert

# Interactive viewer (requires pyqtgraph and PySide6)
python plot_spectrograms.py -i "C:\path\to\mat\files" --interactive --peak-overlay
```

## Command-Line Arguments

### Common Arguments
- `-i, --input-dir`: Directory containing data files (will prompt if omitted)
- `-o, --output-dir`: Output directory (defaults to input directory)
- `--cmap`: Matplotlib colormap (default: inferno)

### Benchtop-Specific Arguments
- `--benchtop`: Enable benchtop CSV workflow
- `--wl-min`: Minimum wavelength in nm (will prompt if omitted)
- `--wl-max`: Maximum wavelength in nm (will prompt if omitted)
- `--save-mat`: Save .mat file with aligned spectrogram data

### On-Chip-Specific Arguments
- `--onchip`: Enable on-chip LIV+OSA workflow
- `--osa-file`: Path to OSA .mat file containing polyfit coefficients
- `--liv-dir`: Path to directory containing LIV .mat files
- `--save-mat`: Save .mat file with aligned spectrogram data + polyfit coeffs

### MAT File-Specific Arguments
- `--pattern`: Filename glob pattern (default: *.mat)
- `--invert`: Invert power values (useful for absorption dips)
- `--start`, `--stop`, `--step`: Slice the file list
- `--save-npz`: Save numpy compressed array
- `--interactive`: Open pyqtgraph viewer (requires pyqtgraph + PySide6)
- `--peak-overlay`: Add peak detection overlay to interactive viewer

## Output Files

### Benchtop Workflow
- `benchtop_spectrogram.png`: Main spectrogram (time vs wavelength)
- `benchtop_spectrogram.mat` (optional): Aligned data arrays
- `Channel3_vs_Wavelength_{wl_min}_{wl_max}nm.png`: Gradient overlay plot
- `Channel3_vs_Wavelength_AllSweeps_{wl_min}_{wl_max}nm.png` or `Channel3_vs_Wavelength_FirstLast_{wl_min}_{wl_max}nm.png`: Detailed overlay plot

### On-Chip Workflow
- `onchip_spectrogram.png`: Main spectrogram (time vs wavelength)
- `onchip_spectrogram.mat` (optional): Aligned data arrays + polyfit coefficients
- `OnChip_Power_vs_Wavelength_{wl_min}_{wl_max}nm.png`: Gradient overlay plot
- `OnChip_Power_vs_Wavelength_AllSweeps_{wl_min}_{wl_max}nm.png` or `OnChip_Power_vs_Wavelength_FirstLast_{wl_min}_{wl_max}nm.png`: Detailed overlay plot

### MAT File Workflow
- `spectrogram_channel_{N}.png`: Per-channel spectrogram
- `spectrograms.npz` (optional): Stacked numpy arrays

## Dependencies

### Required
- numpy
- scipy
- matplotlib

### Optional (for interactive mode)
- pyqtgraph
- PySide6

Install optional dependencies:
```powershell
python -m pip install pyqtgraph PySide6
```

## Timestamp Parsing
The benchtop workflow attempts to parse timestamps from filenames using common patterns:
- ISO-like: `2025-10-30_23-50-59` or `20251030_235059`
- Falls back to file modification time if parsing fails

## Tips
- Use `--wl-min` and `--wl-max` to focus on specific wavelength ranges (reduces noise)
- The inferno colormap highlights hot spots (high power) in yellow/white
- For large datasets (>10 CSV files), the detailed overlay plot shows only first/last for clarity
- Interactive mode allows zooming and exploring the spectrogram dynamically

## Troubleshooting

### "Could not be resolved" import warnings
- These warnings are about optional dependencies (pyqtgraph/PySide6)
- The script works fine without them for non-interactive use
- Install them if you want `--interactive` mode

### "No CSV files found"
- Check that your input directory contains CSV files (searches recursively)
- Verify the CSV format matches benchtop expectations (wavelength row + channel rows)

### On-chip: "Could not find polyfit coefficients"
- Make sure your OSA .mat file contains one of: `polyfit_peakWL_vs_I_deg2_coeffs`, `poly_coeffs`, `coeffs`
- Or ensure it has both `peak_wavelength` and `current_mA` arrays (script will compute polyfit)
- Check that the OSA file was generated by OSAclass or multi_osa

### On-chip: "No valid LIV files found"
- Verify LIV .mat files contain `current` and at least one of: `channel_1`, `channel_0`, `power`
- Check that LIV files were generated by LIVclass or multi_LIV
- Use verbose logging to see which files are being skipped

### Dialog windows not appearing
- Check your taskbar or use Alt+Tab
- The script prints reminders after 5 seconds
- Console fallback is available if GUI fails
